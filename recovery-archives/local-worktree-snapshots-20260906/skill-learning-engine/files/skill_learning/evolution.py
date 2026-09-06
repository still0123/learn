from __future__ import annotations

import hashlib
from difflib import unified_diff
from pathlib import Path
from typing import Mapping

from .components import KnowledgeMaintainer, SkillProposer, TaskExecutor
from .gate import EvaluationGate
from .models import EvolutionSummary
from .runtime import StructuredRuntime
from .tasks import TaskAdapter
from .workspace import Workspace


class EvolutionEngine:
    def __init__(
        self,
        *,
        workspace: Workspace,
        runtime: StructuredRuntime,
        adapter: TaskAdapter,
        gate: EvaluationGate | None = None,
        prompts: Mapping[str, str] | None = None,
        candidate_count: int = 3,
    ) -> None:
        if candidate_count < 1:
            raise ValueError("candidate_count must be at least 1")
        prompt_set = prompts or {}
        self.workspace = workspace
        self.executor = TaskExecutor(
            runtime,
            adapter,
            system_prompt=prompt_set.get("executor.md"),
        )
        self.maintainer = KnowledgeMaintainer(
            runtime,
            system_prompt=prompt_set.get("maintainer.md"),
        )
        self.proposer = SkillProposer(
            runtime,
            system_prompt=prompt_set.get("proposer.md"),
        )
        self.adapter = adapter
        self.gate = gate or EvaluationGate()
        self.candidate_count = candidate_count

    def run(self, *, iterations: int, evaluate_test: bool = True) -> EvolutionSummary:
        if iterations < 1:
            raise ValueError("iterations must be at least 1")
        state = self.workspace.load_state()
        skill_name = state["skill_name"]
        initial_version = int(state["version"])
        iteration = int(state["iteration"])
        active_skill = self.workspace.read_skill(skill_name)

        if state["best_validation_score"] is None:
            baseline_eval = self.executor.evaluate(
                tasks=self.adapter.tasks("validation"),
                skill_name=skill_name,
                skill_version=state["version"],
                skill_text=active_skill,
                iteration=iteration,
                phase="validation-baseline",
                workdir=self.workspace.root,
            )
            self.workspace.record_evaluation(baseline_eval)
            state["best_validation_score"] = baseline_eval.mean_score
            state["best_validation_iteration"] = iteration
            state["best_validation_phase"] = baseline_eval.phase
            self.workspace.save_state(state)
            best_validation = baseline_eval
        else:
            best_iteration = state.get("best_validation_iteration")
            best_phase = state.get("best_validation_phase")
            if best_iteration is None or not best_phase:
                raise ValueError(
                    "workspace lacks V2 best-validation pointer; start a fresh experiment workspace"
                )
            best_validation = self.workspace.load_evaluation(
                iteration=int(best_iteration),
                phase=str(best_phase),
            )
        initial_validation = float(state["best_validation_score"])
        accepted = 0
        rejected = 0
        skipped = 0
        completed = 0

        for _ in range(iterations):
            if best_validation.mean_score >= 1.0:
                self.workspace.append_log(
                    f"\n## Iteration {state['iteration']}\n\n"
                    "Best validation score reached 1.0; evolution stopped early.\n"
                )
                break
            iteration = int(state["iteration"])
            version = int(state["version"])
            active_skill = self.workspace.read_skill(skill_name)
            train_eval = self.executor.evaluate(
                tasks=self.adapter.tasks("train"),
                skill_name=skill_name,
                skill_version=version,
                skill_text=active_skill,
                iteration=iteration,
                phase="train",
                workdir=self.workspace.root,
            )
            self.workspace.record_evaluation(train_eval)
            if all(trace.passed for trace in train_eval.traces):
                self.workspace.append_log(
                    f"\n## Iteration {iteration}\n\nAll training tasks passed; evolution stopped early.\n"
                )
                break

            patterns = self.maintainer.update(
                wiki_index=self.workspace.read_wiki_index(),
                traces=train_eval.traces,
                workdir=self.workspace.root,
            )
            self.workspace.update_patterns(iteration=iteration, patterns=patterns)

            proposer_view = self.workspace.prepare_proposer_view(
                iteration=iteration,
                skill_name=skill_name,
                traces=train_eval.traces,
            )
            baseline_score = float(state["best_validation_score"])
            candidates: list[dict] = []
            seen_skill_hashes: set[str] = set()
            target_patterns = sorted(patterns, key=lambda item: item.id)[:self.candidate_count]
            for position, target_pattern in enumerate(target_patterns, start=1):
                candidate_id = f"candidate-{position:02d}"
                proposal = None
                diff = ""
                candidate_sha256 = None
                candidate_path = None
                try:
                    proposal = self.proposer.propose(
                        skill_name=skill_name,
                        skill_text=active_skill,
                        target_pattern=target_pattern,
                        patterns=patterns,
                        traces=train_eval.traces,
                        impact_log=self.workspace.read_impact_log(),
                        workdir=proposer_view,
                    )
                    candidate_skill = self.workspace.render_candidate_skill(proposal)
                    candidate_sha256 = hashlib.sha256(candidate_skill.encode("utf-8")).hexdigest()
                    if candidate_sha256 in seen_skill_hashes:
                        skipped += 1
                        self.workspace.record_impact(
                            iteration=iteration,
                            candidate_id=candidate_id,
                            candidate_sha256=candidate_sha256,
                            skill_name=skill_name,
                            decision="duplicate",
                            baseline=baseline_score,
                            candidate=None,
                            summary=proposal.summary,
                            reason="candidate SKILL.md duplicates an earlier candidate in this iteration",
                            proposal=proposal,
                            version_before=version,
                            version_after=version,
                        )
                        continue
                    seen_skill_hashes.add(candidate_sha256)
                    candidate_dir = self.workspace.build_candidate(
                        iteration=iteration,
                        candidate_id=candidate_id,
                        proposal=proposal,
                    )
                    candidate_path = candidate_dir.relative_to(self.workspace.root).as_posix()
                    diff = "".join(unified_diff(
                        active_skill.splitlines(keepends=True),
                        candidate_skill.splitlines(keepends=True),
                        fromfile=f"skills/{skill_name}/SKILL.md",
                        tofile=f"{candidate_path}/SKILL.md",
                    ))
                    candidate_eval = self.executor.evaluate(
                        tasks=self.adapter.tasks("validation"),
                        skill_name=skill_name,
                        skill_version=version + 1,
                        skill_text=candidate_skill,
                        iteration=iteration,
                        phase=f"validation-{candidate_id}",
                        workdir=candidate_dir,
                    )
                    self.workspace.record_evaluation(candidate_eval)
                    candidates.append({
                        "candidate_id": candidate_id,
                        "candidate_dir": candidate_dir,
                        "candidate_path": candidate_path,
                        "candidate_sha256": candidate_sha256,
                        "proposal": proposal,
                        "diff": diff,
                        "evaluation": candidate_eval,
                        "gate": self.gate.decide(
                            baseline=best_validation,
                            candidate=candidate_eval,
                        ),
                    })
                except Exception as exc:
                    skipped += 1
                    self.workspace.record_impact(
                        iteration=iteration,
                        candidate_id=candidate_id,
                        candidate_sha256=candidate_sha256,
                        candidate_path=candidate_path,
                        skill_name=skill_name,
                        decision="failed",
                        baseline=baseline_score,
                        candidate=None,
                        summary=proposal.summary if proposal else "proposal not created",
                        reason=f"{type(exc).__name__}: {exc}",
                        proposal=proposal,
                        diff=diff,
                        version_before=version,
                        version_after=version,
                    )

            eligible = [item for item in candidates if item["gate"].accepted]
            winner = None
            if eligible:
                best_score = max(item["evaluation"].mean_score for item in eligible)
                best_candidates = [
                    item for item in eligible
                    if item["evaluation"].mean_score == best_score
                ]
                if len(best_candidates) == 1:
                    winner = best_candidates[0]

            for item in candidates:
                proposal = item["proposal"]
                candidate_eval = item["evaluation"]
                decision = item["gate"]
                if item is winner:
                    state["version"] = self.workspace.promote(
                        candidate_dir=item["candidate_dir"],
                        skill_name=skill_name,
                        current_version=version,
                    )
                    state["best_validation_score"] = candidate_eval.mean_score
                    state["best_validation_iteration"] = iteration
                    state["best_validation_phase"] = candidate_eval.phase
                    best_validation = candidate_eval
                    accepted += 1
                    decision_name = "accepted"
                    reason = decision.reason
                elif decision.accepted:
                    rejected += 1
                    decision_name = "rejected-not-best"
                    if winner is None:
                        reason = (
                            "candidate strictly improves validation but ties another best candidate; "
                            "no arbitrary promotion was made"
                        )
                    else:
                        reason = (
                            f"candidate is below selected {winner['candidate_id']} on validation "
                            f"({candidate_eval.mean_score:.4f} < "
                            f"{winner['evaluation'].mean_score:.4f})"
                        )
                else:
                    rejected += 1
                    decision_name = "rejected"
                    reason = decision.reason
                self.workspace.record_impact(
                    iteration=iteration,
                    candidate_id=item["candidate_id"],
                    candidate_sha256=item["candidate_sha256"],
                    candidate_path=item["candidate_path"],
                    skill_name=skill_name,
                    decision=decision_name,
                    baseline=baseline_score,
                    candidate=candidate_eval.mean_score,
                    summary=proposal.summary,
                    reason=reason,
                    proposal=proposal,
                    diff=item["diff"],
                    version_before=version,
                    version_after=int(state["version"]),
                    comparison=decision.to_dict(),
                )

            state["iteration"] = iteration + 1
            self.workspace.save_state(state)
            completed += 1

        final_test_score = None
        if evaluate_test:
            final_skill = self.workspace.read_skill(skill_name)
            final_test = self.executor.evaluate(
                tasks=self.adapter.tasks("test"),
                skill_name=skill_name,
                skill_version=int(state["version"]),
                skill_text=final_skill,
                iteration=int(state["iteration"]),
                phase="test-final",
                workdir=self.workspace.root,
            )
            self.workspace.record_evaluation(final_test)
            final_test_score = final_test.mean_score
        return EvolutionSummary(
            skill_name=skill_name,
            initial_version=initial_version,
            final_version=int(state["version"]),
            initial_validation_score=initial_validation,
            final_validation_score=best_validation.mean_score,
            final_test_score=final_test_score,
            accepted=accepted,
            rejected=rejected,
            skipped=skipped,
            completed_iterations=completed,
        )
