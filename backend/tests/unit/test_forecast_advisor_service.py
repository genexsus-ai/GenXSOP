from app.config import settings
from app.services.forecast_advisor_service import ForecastAdvisorService


def test_recommend_model_uses_requested_model_directly(monkeypatch):
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "")
    service = ForecastAdvisorService()

    result = service.recommend_model(
        requested_model="prophet",
        default_model="moving_average",
        candidate_metrics=[],
        history_months=8,
        data_quality_flags=[],
    )

    assert result.recommended_model == "prophet"
    assert result.fallback_used is False
    assert "explicitly requested" in result.reason.lower()


def test_recommend_model_falls_back_when_llm_not_configured(monkeypatch):
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "")
    service = ForecastAdvisorService()

    result = service.recommend_model(
        requested_model=None,
        default_model="exp_smoothing",
        candidate_metrics=[{"model_type": "exp_smoothing", "mape": 10.0}],
        history_months=16,
        data_quality_flags=["short_history"],
    )

    assert result.recommended_model == "exp_smoothing"
    assert result.advisor_enabled is False
    assert result.fallback_used is True
    assert "llm_unavailable" in result.warnings
