"""
Forecasting Model Factory — GoF Factory Pattern

Principles applied:
- Factory Pattern (GoF): Centralizes object creation for forecasting strategies.
- Open/Closed Principle (OCP): Register new strategies without modifying the factory.
- Single Responsibility Principle (SRP): Factory only creates strategy objects.
- Dependency Inversion Principle (DIP): Callers depend on the factory abstraction.
"""
from typing import Dict, Type, List
from app.ml.strategies import (
    BaseForecastStrategy,
    MovingAverageStrategy,
    ExponentialSmoothingStrategy,
    ProphetStrategy,
    ForecastContext,
)


class ForecastModelFactory:
    """
    Factory that creates and manages forecasting strategy instances.

    Usage:
        strategy = ForecastModelFactory.create("prophet")
        context = ForecastModelFactory.create_context("exp_smoothing")
    """

    # Registry maps model_id → strategy class (OCP: add new entries, don't modify)
    _registry: Dict[str, Type[BaseForecastStrategy]] = {
        "moving_average": MovingAverageStrategy,
        "exp_smoothing": ExponentialSmoothingStrategy,
        "prophet": ProphetStrategy,
    }

    @classmethod
    def register(cls, model_id: str, strategy_class: Type[BaseForecastStrategy]) -> None:
        """
        Register a new forecasting strategy at runtime.
        Enables plugin-style extensibility without modifying this file.
        """
        cls._registry[model_id] = strategy_class

    @classmethod
    def create(cls, model_id: str) -> BaseForecastStrategy:
        """
        Instantiate a forecasting strategy by model_id.

        Raises:
            ValueError: If model_id is not registered.
        """
        strategy_class = cls._registry.get(model_id)
        if strategy_class is None:
            available = list(cls._registry.keys())
            raise ValueError(
                f"Unknown forecast model '{model_id}'. "
                f"Available models: {available}"
            )
        return strategy_class()

    @classmethod
    def create_context(cls, model_id: str) -> ForecastContext:
        """
        Create a ForecastContext pre-loaded with the requested strategy.
        """
        strategy = cls.create(model_id)
        return ForecastContext(strategy)

    @classmethod
    def list_models(cls) -> List[Dict]:
        """
        Return metadata for all registered models (for API /forecasting/models endpoint).
        """
        return [
            {
                "id": model_id,
                "name": cls._registry[model_id]().display_name,
                "min_data_months": cls._registry[model_id]().min_data_months,
            }
            for model_id in cls._registry
        ]

    @classmethod
    def get_best_strategy(cls, data_months: int) -> BaseForecastStrategy:
        """
        Auto-select the best strategy based on available data length.
        Implements the auto-selection logic from the design document.
        """
        if data_months >= 24:
            return cls.create("prophet")
        elif data_months >= 12:
            return cls.create("exp_smoothing")
        else:
            return cls.create("moving_average")
