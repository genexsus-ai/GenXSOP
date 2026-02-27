from sqlalchemy import Column, Integer, String, Numeric, DateTime, Date, func
from app.database import Base


class KPIMetric(Base):
    __tablename__ = "kpi_metrics"

    id = Column(Integer, primary_key=True, index=True)
    metric_name = Column(String(100), nullable=False, index=True)
    metric_category = Column(String(50), nullable=False)
    period = Column(Date, nullable=False, index=True)
    value = Column(Numeric(12, 4), nullable=False)
    target = Column(Numeric(12, 4), nullable=True)
    previous_value = Column(Numeric(12, 4), nullable=True)
    variance = Column(Numeric(12, 4), nullable=True)
    variance_pct = Column(Numeric(8, 4), nullable=True)
    trend = Column(String(20), nullable=True)
    unit = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=func.now())
