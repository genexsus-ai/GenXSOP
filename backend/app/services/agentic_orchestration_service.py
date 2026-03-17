from __future__ import annotations

from dataclasses import dataclass
from typing import List
from copy import deepcopy

from app.schemas.agentic_scheduling import (
    AgenticOrchestrationAlternative,
    AgenticOrchestrationResponse,
    AgenticScheduleAction,
    AgenticScheduleEventRequest,
)


@dataclass
class _ObjectiveWeights:
    tardiness: float = 0.45
    changeover: float = 0.25
    utilization: float = 0.30


class AgenticOrchestrationService:
    """
    Phase-2 MVP orchestration layer.

    Flow:
    1) Constraint pass (feasibility gate)
    2) Optimization ranking (objective scoring)
    3) Simulation impact estimation (KPI deltas)
    """

    def orchestrate(
        self,
        body: AgenticScheduleEventRequest,
        candidate_actions: List[AgenticScheduleAction],
    ) -> AgenticOrchestrationResponse:
        feasible = self._constraint_pass(candidate_actions)
        if not feasible:
            return AgenticOrchestrationResponse(
                workflow_state="FAILED",
                recommendation_summary="No feasible actions after constraint validation.",
                selected_action=None,
                alternatives=[],
                objective_weights=self._weights_as_dict(_ObjectiveWeights()),
            )

        weights = _ObjectiveWeights()
        expanded = self._expand_alternatives(feasible)
        alternatives = [self._score_and_simulate(body=body, action=a, weights=weights) for a in expanded]
        alternatives = sorted(alternatives, key=lambda x: x.score, reverse=True)
        selected = alternatives[0] if alternatives else None

        summary = (
            f"Orchestration evaluated {len(alternatives)} feasible alternative(s). "
            f"Selected action '{selected.action.action_type}' with score {selected.score:.3f}."
            if selected
            else "No candidate selected."
        )

        return AgenticOrchestrationResponse(
            workflow_state="SIMULATED",
            recommendation_summary=summary,
            selected_action=selected.action if selected else None,
            alternatives=alternatives,
            objective_weights=self._weights_as_dict(weights),
        )

    def _constraint_pass(
        self,
        candidate_actions: List[AgenticScheduleAction],
    ) -> List[AgenticScheduleAction]:
        feasible: List[AgenticScheduleAction] = []
        for action in candidate_actions:
            if action.to_sequence < 1:
                continue
            if action.from_sequence == action.to_sequence and action.action_type not in {"manual_review", "hold"}:
                continue
            feasible.append(action)
        return feasible

    def _expand_alternatives(
        self,
        candidate_actions: List[AgenticScheduleAction],
    ) -> List[AgenticScheduleAction]:
        alternatives: List[AgenticScheduleAction] = []
        seen = set()

        for action in candidate_actions:
            base = deepcopy(action)
            key = (base.action_type, base.schedule_id, base.from_sequence, base.to_sequence)
            if key not in seen:
                seen.add(key)
                alternatives.append(base)

            if action.action_type in {"resequence", "expedite"}:
                conservative = deepcopy(action)
                conservative.to_sequence = max(1, action.to_sequence - 1)
                conservative.reason = f"{action.reason} (conservative variant)"
                c_key = (
                    conservative.action_type,
                    conservative.schedule_id,
                    conservative.from_sequence,
                    conservative.to_sequence,
                )
                if c_key not in seen:
                    seen.add(c_key)
                    alternatives.append(conservative)

                aggressive = deepcopy(action)
                aggressive.to_sequence = max(1, action.to_sequence + 1)
                aggressive.reason = f"{action.reason} (aggressive variant)"
                a_key = (
                    aggressive.action_type,
                    aggressive.schedule_id,
                    aggressive.from_sequence,
                    aggressive.to_sequence,
                )
                if a_key not in seen:
                    seen.add(a_key)
                    alternatives.append(aggressive)

        return alternatives

    def _score_and_simulate(
        self,
        body: AgenticScheduleEventRequest,
        action: AgenticScheduleAction,
        weights: _ObjectiveWeights,
    ) -> AgenticOrchestrationAlternative:
        move_distance = abs(action.from_sequence - action.to_sequence)
        severity_factor = {
            "low": 0.90,
            "medium": 1.00,
            "high": 1.10,
            "critical": 1.20,
        }.get(body.severity, 1.0)

        tardiness_gain = min(1.0, (move_distance / 5.0) * severity_factor)
        changeover_penalty = min(1.0, 0.15 + (move_distance * 0.08))
        utilization_gain = min(1.0, 0.35 + (0.1 * severity_factor))

        score = (
            weights.tardiness * tardiness_gain
            - weights.changeover * changeover_penalty
            + weights.utilization * utilization_gain
        )

        otif_delta_pct = round((tardiness_gain * 3.2) - (changeover_penalty * 0.8), 2)
        utilization_delta_pct = round((utilization_gain * 2.0), 2)
        changeover_delta_pct = round(-(changeover_penalty * 2.5), 2)
        risk_indicators: List[str] = []
        if move_distance >= 4:
            risk_indicators.append("setup_churn_risk")
        if body.severity in {"high", "critical"}:
            risk_indicators.append("service_level_risk")
        if action.action_type == "hold":
            risk_indicators.append("throughput_risk")

        return AgenticOrchestrationAlternative(
            action=action,
            score=round(score, 4),
            simulated_kpis={
                "otif_delta_pct": otif_delta_pct,
                "utilization_delta_pct": utilization_delta_pct,
                "changeover_delta_pct": changeover_delta_pct,
                "schedule_adherence_delta_pct": round((tardiness_gain * 2.6), 2),
                "wip_delta_pct": round(-(move_distance * 0.4), 2),
            },
            risk_indicators=risk_indicators,
        )

    @staticmethod
    def _weights_as_dict(weights: _ObjectiveWeights) -> dict:
        return {
            "tardiness": weights.tardiness,
            "changeover": weights.changeover,
            "utilization": weights.utilization,
        }
