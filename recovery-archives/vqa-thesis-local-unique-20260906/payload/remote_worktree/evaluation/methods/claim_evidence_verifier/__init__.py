"""Lightweight counterfactual claim-evidence verifier for AdsQA."""

from .features import FEATURE_SCHEMA_VERSION, build_feature_vector, feature_names

__all__ = ["FEATURE_SCHEMA_VERSION", "build_feature_vector", "feature_names"]
