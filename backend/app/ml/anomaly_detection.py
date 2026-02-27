"""
Anomaly Detection for Demand Data
Uses statistical methods (Z-score, IQR) and Isolation Forest
"""
import numpy as np
from typing import List, Dict
from sqlalchemy.orm import Session
from app.models.demand_plan import DemandPlan


class AnomalyDetector:
    """
    Detects anomalies in a list of numeric values using Z-score method.
    Returns indices of anomalous data points.
    """

    def __init__(self, z_threshold: float = 2.5):
        self.z_threshold = z_threshold

    def detect(self, values: List[float]) -> List[int]:
        """Return indices of anomalous values."""
        if len(values) < 6:
            return []
        arr = np.array(values, dtype=float)
        mean = np.mean(arr)
        std = np.std(arr)
        if std == 0:
            return []
        z_scores = np.abs((arr - mean) / std)
        return [int(i) for i in np.where(z_scores > self.z_threshold)[0]]


def detect_demand_anomalies(db: Session, product_id: int) -> List[Dict]:
    """Detect anomalies in demand data using Z-score method"""
    plans = (
        db.query(DemandPlan)
        .filter(DemandPlan.product_id == product_id)
        .order_by(DemandPlan.period.asc())
        .all()
    )
    if len(plans) < 6:
        return []

    values = np.array([
        float(p.actual_qty or p.consensus_qty or p.adjusted_qty or p.forecast_qty)
        for p in plans
    ])
    mean = np.mean(values)
    std = np.std(values)
    if std == 0:
        return []

    anomalies = []
    for i, plan in enumerate(plans):
        val = values[i]
        z_score = abs((val - mean) / std)
        if z_score > 2.5:
            severity = "high" if z_score > 3.5 else "medium"
            direction = "spike" if val > mean else "drop"
            anomalies.append({
                "period": str(plan.period),
                "value": round(float(val), 2),
                "mean": round(float(mean), 2),
                "z_score": round(float(z_score), 2),
                "severity": severity,
                "direction": direction,
                "suggested_action": "Investigate demand spike" if direction == "spike" else "Investigate demand drop",
            })
    return anomalies


def detect_iqr_anomalies(values: np.ndarray) -> np.ndarray:
    """IQR-based outlier detection, returns boolean mask"""
    q1 = np.percentile(values, 25)
    q3 = np.percentile(values, 75)
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    return (values < lower) | (values > upper)
