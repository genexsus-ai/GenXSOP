"""
GenXAI Forecast Advisor Service

Provides an optional LLM-powered recommendation layer for model selection.
The service is strictly advisory and always falls back to deterministic logic.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Dict, List, Optional

from app.config import settings


@dataclass
class ForecastAdvisorDecision:
    recommended_model: str
    confidence: float
    reason: str
    advisor_enabled: bool
    fallback_used: bool
    warnings: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "recommended_model": self.recommended_model,
            "confidence": self.confidence,
            "reason": self.reason,
            "advisor_enabled": self.advisor_enabled,
            "fallback_used": self.fallback_used,
            "warnings": self.warnings,
        }


class ForecastAdvisorService:
    """LLM advisor wrapper with strict deterministic fallback."""

    _supported_models = {"moving_average", "exp_smoothing", "prophet"}

    def __init__(self) -> None:
        self._enabled = bool(settings.OPENAI_API_KEY)

    def recommend_model(
        self,
        *,
        requested_model: Optional[str],
        default_model: str,
        candidate_metrics: List[Dict[str, Any]],
        history_months: int,
        data_quality_flags: List[str],
    ) -> ForecastAdvisorDecision:
        if requested_model:
            return ForecastAdvisorDecision(
                recommended_model=requested_model,
                confidence=1.0,
                reason="Model explicitly requested by user.",
                advisor_enabled=self._enabled,
                fallback_used=False,
                warnings=[],
            )

        if not self._enabled:
            return ForecastAdvisorDecision(
                recommended_model=default_model,
                confidence=0.65,
                reason="OPENAI_API_KEY not configured; using deterministic selector.",
                advisor_enabled=False,
                fallback_used=True,
                warnings=["llm_unavailable"],
            )

        try:
            return self._recommend_with_genxai(
                default_model=default_model,
                candidate_metrics=candidate_metrics,
                history_months=history_months,
                data_quality_flags=data_quality_flags,
            )
        except Exception as exc:  # noqa: BLE001
            return ForecastAdvisorDecision(
                recommended_model=default_model,
                confidence=0.6,
                reason=f"Advisor fallback used due to runtime error: {exc}",
                advisor_enabled=True,
                fallback_used=True,
                warnings=["advisor_runtime_error"],
            )

    def _recommend_with_genxai(
        self,
        *,
        default_model: str,
        candidate_metrics: List[Dict[str, Any]],
        history_months: int,
        data_quality_flags: List[str],
    ) -> ForecastAdvisorDecision:
        from genxai import AgentConfig, AgentRuntime, AssistantAgent

        cfg = AgentConfig(
            role="Forecast Model Advisor",
            goal="Select the most reliable forecasting model using provided metrics.",
            backstory="You are an S&OP forecasting advisor. Prefer low error and stable models.",
            llm_provider="openai",
            llm_model=settings.GENXAI_LLM_MODEL,
            llm_temperature=settings.GENXAI_LLM_TEMPERATURE,
            max_execution_time=settings.GENXAI_MAX_EXECUTION_TIME_SECONDS,
            max_iterations=2,
            verbose=False,
        )
        agent = AssistantAgent(id="forecast-advisor", config=cfg)
        runtime = AgentRuntime(agent=agent, openai_api_key=settings.OPENAI_API_KEY)

        task = (
            "Choose one model from ['moving_average','exp_smoothing','prophet'] based on backtest metrics. "
            "Respond ONLY valid JSON with keys: recommended_model (string), confidence (0..1), reason (string). "
            f"Default model if uncertain: {default_model}.\n"
            f"History months: {history_months}.\n"
            f"Data quality flags: {data_quality_flags}.\n"
            f"Candidate metrics: {json.dumps(candidate_metrics)}"
        )

        result = runtime.execute(task=task)
        payload = self._extract_json_payload(result)

        model = str(payload.get("recommended_model", default_model))
        if model not in self._supported_models:
            model = default_model

        confidence = float(payload.get("confidence", 0.7))
        confidence = max(0.0, min(1.0, confidence))

        reason = str(payload.get("reason", "Model selected by GenXAI advisor."))

        return ForecastAdvisorDecision(
            recommended_model=model,
            confidence=confidence,
            reason=reason,
            advisor_enabled=True,
            fallback_used=False,
            warnings=[],
        )

    @staticmethod
    def _extract_json_payload(result: Dict[str, Any]) -> Dict[str, Any]:
        if isinstance(result, dict):
            for key in ("output", "response", "result", "text", "content"):
                value = result.get(key)
                if isinstance(value, dict):
                    return value
                if isinstance(value, str):
                    value = value.strip()
                    if value.startswith("{") and value.endswith("}"):
                        return json.loads(value)
            if "recommended_model" in result:
                return result
        raise ValueError("Unable to parse advisor JSON response")
