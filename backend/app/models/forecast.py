from sqlalchemy import Column, Integer, String, Numeric, DateTime, Date, ForeignKey, Text, func
from app.database import Base


class Forecast(Base):
    __tablename__ = "forecasts"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    model_type = Column(String(50), nullable=False)
    period = Column(Date, nullable=False, index=True)
    predicted_qty = Column(Numeric(12, 2), nullable=False)
    lower_bound = Column(Numeric(12, 2), nullable=True)
    upper_bound = Column(Numeric(12, 2), nullable=True)
    confidence = Column(Numeric(5, 2), nullable=True)
    mape = Column(Numeric(8, 4), nullable=True)
    rmse = Column(Numeric(12, 4), nullable=True)
    features_used = Column(Text, nullable=True)
    model_version = Column(String(50), nullable=True)
    training_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())
