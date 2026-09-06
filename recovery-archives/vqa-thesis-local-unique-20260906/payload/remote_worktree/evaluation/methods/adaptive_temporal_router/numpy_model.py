"""Small deterministic NumPy model for the adaptive temporal router."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def _np():
    import numpy as np

    return np


def sigmoid(values):
    np = _np()
    clipped = np.clip(values, -40.0, 40.0)
    return 1.0 / (1.0 + np.exp(-clipped))


@dataclass
class Standardizer:
    mean: Any
    scale: Any

    @classmethod
    def fit(cls, values):
        np = _np()
        mean = np.asarray(values, dtype=np.float64).mean(axis=0)
        scale = np.asarray(values, dtype=np.float64).std(axis=0)
        scale[scale < 1e-6] = 1.0
        return cls(mean=mean, scale=scale)

    def transform(self, values):
        np = _np()
        return (np.asarray(values, dtype=np.float64) - self.mean) / self.scale

    def to_dict(self) -> dict[str, Any]:
        return {"mean": self.mean.tolist(), "scale": self.scale.tolist()}

    @classmethod
    def from_dict(cls, value: dict[str, Any]):
        np = _np()
        return cls(np.asarray(value["mean"], dtype=np.float64), np.asarray(value["scale"], dtype=np.float64))


class BinaryMLP:
    def __init__(self, input_dim: int, hidden_dim: int = 16, seed: int = 42):
        np = _np()
        rng = np.random.default_rng(seed)
        self.w1 = rng.normal(0.0, (2.0 / max(1, input_dim)) ** 0.5, (input_dim, hidden_dim))
        self.b1 = np.zeros(hidden_dim, dtype=np.float64)
        self.w2 = rng.normal(0.0, (2.0 / max(1, hidden_dim)) ** 0.5, (hidden_dim, 1))
        self.b2 = np.zeros(1, dtype=np.float64)

    def logits(self, values):
        np = _np()
        hidden = np.maximum(0.0, values @ self.w1 + self.b1)
        return (hidden @ self.w2 + self.b2).reshape(-1)

    def predict_proba(self, values, temperature: float = 1.0):
        return sigmoid(self.logits(values) / max(1e-4, float(temperature)))

    def fit(self, train_x, train_y, validation_x, validation_y, *, epochs=800, learning_rate=0.01, l2=1e-3, patience=80):
        np = _np()
        x = np.asarray(train_x, dtype=np.float64)
        y = np.asarray(train_y, dtype=np.float64).reshape(-1)
        val_x = np.asarray(validation_x, dtype=np.float64)
        val_y = np.asarray(validation_y, dtype=np.float64).reshape(-1)
        positives = max(1.0, float(y.sum()))
        negatives = max(1.0, float(len(y) - y.sum()))
        positive_weight = min(20.0, negatives / positives)
        sample_weight = np.where(y > 0.5, positive_weight, 1.0)
        parameters = [self.w1, self.b1, self.w2, self.b2]
        first = [np.zeros_like(value) for value in parameters]
        second = [np.zeros_like(value) for value in parameters]
        best_state = self.to_dict()
        best_loss = float("inf")
        best_epoch = 0
        wait = 0
        history = []
        for epoch in range(1, epochs + 1):
            hidden_pre = x @ self.w1 + self.b1
            hidden = np.maximum(0.0, hidden_pre)
            logits = (hidden @ self.w2 + self.b2).reshape(-1)
            probabilities = sigmoid(logits)
            normalizer = max(1.0, float(sample_weight.sum()))
            dlogits = (probabilities - y) * sample_weight / normalizer
            grad_w2 = hidden.T @ dlogits[:, None] + l2 * self.w2
            grad_b2 = np.asarray([dlogits.sum()])
            dhidden = dlogits[:, None] @ self.w2.T
            dhidden[hidden_pre <= 0.0] = 0.0
            grad_w1 = x.T @ dhidden + l2 * self.w1
            grad_b1 = dhidden.sum(axis=0)
            gradients = [grad_w1, grad_b1, grad_w2, grad_b2]
            for index, (parameter, gradient) in enumerate(zip(parameters, gradients)):
                first[index] = 0.9 * first[index] + 0.1 * gradient
                second[index] = 0.999 * second[index] + 0.001 * gradient * gradient
                first_hat = first[index] / (1.0 - 0.9 ** epoch)
                second_hat = second[index] / (1.0 - 0.999 ** epoch)
                parameter -= learning_rate * first_hat / (np.sqrt(second_hat) + 1e-8)
            val_probabilities = self.predict_proba(val_x)
            epsilon = 1e-8
            val_loss = float(-np.mean(
                val_y * np.log(val_probabilities + epsilon)
                + (1.0 - val_y) * np.log(1.0 - val_probabilities + epsilon)
            ))
            if epoch == 1 or epoch % 25 == 0:
                history.append({"epoch": epoch, "validation_bce": val_loss})
            if val_loss + 1e-6 < best_loss:
                best_loss, best_epoch, best_state, wait = val_loss, epoch, self.to_dict(), 0
            else:
                wait += 1
                if wait >= patience:
                    break
        restored = BinaryMLP.from_dict(best_state)
        self.w1, self.b1, self.w2, self.b2 = restored.w1, restored.b1, restored.w2, restored.b2
        return {
            "best_epoch": best_epoch, "best_validation_bce": best_loss,
            "epochs_ran": epoch, "positive_weight": positive_weight, "history": history,
        }

    def to_dict(self) -> dict[str, Any]:
        return {"w1": self.w1.tolist(), "b1": self.b1.tolist(), "w2": self.w2.tolist(), "b2": self.b2.tolist()}

    @classmethod
    def from_dict(cls, value: dict[str, Any]):
        np = _np()
        model = cls(len(value["w1"]), len(value["b1"]), seed=0)
        model.w1 = np.asarray(value["w1"], dtype=np.float64)
        model.b1 = np.asarray(value["b1"], dtype=np.float64)
        model.w2 = np.asarray(value["w2"], dtype=np.float64)
        model.b2 = np.asarray(value["b2"], dtype=np.float64)
        return model

