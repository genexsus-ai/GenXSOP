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

    _supported_models = {
        "moving_average",
        "ewma",
        "exp_smoothing",
        "seasonal_naive",
        "arima",
        "prophet",
    }

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
                reason="Using user-selected model.",
                advisor_enabled=False,
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
            "Choose one model from ['moving_average','ewma','exp_smoothing','seasonal_naive','arima','prophet'] based on backtest metrics. "
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

    def compare_options(
        self,
        *,
        default_model: str,
        history_months: int,
        data_quality_flags: List[str],
        options: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Rank forecast model options and return recommendation narrative."""
        if not options:
            return {
                "recommended_model": default_model,
                "confidence": 0.5,
                "reason": "No options available to compare.",
                "advisor_enabled": False,
                "fallback_used": True,
                "warnings": ["no_options"],
            }

        ranked = sorted(options, key=lambda o: float(o.get("score", 999999.0)))
        deterministic_best = ranked[0]["model_type"]

        if not self._enabled:
            return {
                "recommended_model": deterministic_best,
                "confidence": 0.72,
                "reason": "LLM unavailable; selected lowest composite error score.",
                "advisor_enabled": False,
                "fallback_used": True,
                "warnings": ["llm_unavailable"],
                "ranked": ranked,
            }

        try:
            llm = self._compare_options_with_genxai(
                default_model=default_model,
                history_months=history_months,
                data_quality_flags=data_quality_flags,
                options=ranked,
            )
            picked = str(llm.get("recommended_model", deterministic_best))
            if picked not in {o["model_type"] for o in ranked}:
                picked = deterministic_best

            confidence = max(0.0, min(1.0, float(llm.get("confidence", 0.75))))
            return {
                "recommended_model": picked,
                "confidence": confidence,
                "reason": str(llm.get("reason", "Recommendation generated from multi-model comparison.")),
                "advisor_enabled": True,
                "fallback_used": False,
                "warnings": [],
                "ranked": ranked,
                "option_summaries": llm.get("option_summaries", {}),
                "conservative_model": llm.get("conservative_model"),
                "aggressive_model": llm.get("aggressive_model"),
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "recommended_model": deterministic_best,
                "confidence": 0.65,
                "reason": f"LLM comparison failed; used deterministic ranking. ({exc})",
                "advisor_enabled": True,
                "fallback_used": True,
                "warnings": ["advisor_runtime_error"],
                "ranked": ranked,
            }

    def _compare_options_with_genxai(
        self,
        *,
        default_model: str,
        history_months: int,
        data_quality_flags: List[str],
        options: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        from genxai import AgentConfig, AgentRuntime, AssistantAgent

        cfg = AgentConfig(
            role="Forecast Model Comparator",
            goal="Rank candidate forecasting options and explain tradeoffs for demand planners.",
            backstory="You are a senior S&OP advisor balancing service level, inventory risk, and forecast accuracy.",
            llm_provider="openai",
            llm_model=settings.GENXAI_LLM_MODEL,
            llm_temperature=settings.GENXAI_LLM_TEMPERATURE,
            max_execution_time=settings.GENXAI_MAX_EXECUTION_TIME_SECONDS,
            max_iterations=2,
            verbose=False,
        )
        agent = AssistantAgent(id="forecast-model-comparator", config=cfg)
        runtime = AgentRuntime(agent=agent, openai_api_key=settings.OPENAI_API_KEY)

        task = (
            "You are comparing forecast model options. Respond ONLY JSON with keys: "
            "recommended_model (string), confidence (0..1), reason (string), "
            "conservative_model (string), aggressive_model (string), option_summaries (object model_id->string). "
            f"Default model if uncertain: {default_model}. "
            f"History months: {history_months}. "
            f"Data quality flags: {data_quality_flags}. "
            f"Options: {json.dumps(options)}"
        )
        result = runtime.execute(task=task)
        return self._extract_json_payload(result)

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
