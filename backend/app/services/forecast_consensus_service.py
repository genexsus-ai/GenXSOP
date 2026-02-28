"""
Forecast Consensus Service — Service Layer (SRP / DIP)
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List

from sqlalchemy.orm import Session

from app.core.exceptions import (
    EntityNotFoundException,
    BusinessRuleViolationException,
    InvalidStateTransitionException,
    to_http_exception,
)
from app.models.demand_plan import DemandPlan
from app.models.forecast_consensus import ForecastConsensus
from app.repositories.demand_repository import DemandPlanRepository
from app.repositories.forecast_consensus_repository import ForecastConsensusRepository
from app.schemas.forecast_consensus import (
    ForecastConsensusCreate,
    ForecastConsensusUpdate,
    ForecastConsensusApproveRequest,
)


class ForecastConsensusService:
    def __init__(self, db: Session):
        self._db = db
        self._repo = ForecastConsensusRepository(db)
        self._demand_repo = DemandPlanRepository(db)

    @staticmethod
    def _d(value: Optional[Decimal], default: str = "0") -> Decimal:
        if value is None:
            return Decimal(default)
        return Decimal(str(value))

    def _compute_final(
        self,
        baseline_qty: Decimal,
        sales_override_qty: Decimal,
        marketing_uplift_qty: Decimal,
        finance_adjustment_qty: Decimal,
        constraint_cap_qty: Optional[Decimal],
    ) -> tuple[Decimal, Decimal]:
        pre = baseline_qty + sales_override_qty + marketing_uplift_qty + finance_adjustment_qty
        if pre < 0:
            pre = Decimal("0")

        final = pre
        if constraint_cap_qty is not None:
            final = min(pre, constraint_cap_qty)
        if final < 0:
            final = Decimal("0")

        return pre, final

    def list_consensus(
        self,
        product_id: Optional[int] = None,
        status: Optional[str] = None,
        period_from: Optional[date] = None,
        period_to: Optional[date] = None,
    ) -> List[ForecastConsensus]:
        return self._repo.list_filtered(
            product_id=product_id,
            status=status,
            period_from=period_from,
            period_to=period_to,
        )

    def get_consensus(self, consensus_id: int) -> ForecastConsensus:
        consensus = self._repo.get_by_id(consensus_id)
        if not consensus:
            raise to_http_exception(EntityNotFoundException("ForecastConsensus", consensus_id))
        return consensus

    def create_consensus(self, data: ForecastConsensusCreate, user_id: int) -> ForecastConsensus:
        baseline = self._d(data.baseline_qty)
        sales = self._d(data.sales_override_qty)
        marketing = self._d(data.marketing_uplift_qty)
        finance = self._d(data.finance_adjustment_qty)
        cap = self._d(data.constraint_cap_qty) if data.constraint_cap_qty is not None else None
        pre, final = self._compute_final(baseline, sales, marketing, finance, cap)

        latest = self._repo.get_latest(data.product_id, data.period)
        version = (latest.version + 1) if latest else 1

        row = ForecastConsensus(
            product_id=data.product_id,
            period=data.period,
            baseline_qty=baseline,
            sales_override_qty=sales,
            marketing_uplift_qty=marketing,
            finance_adjustment_qty=finance,
            constraint_cap_qty=cap,
            pre_consensus_qty=pre,
            final_consensus_qty=final,
            status=data.status,
            notes=data.notes,
            version=version,
            created_by=user_id,
        )
        return self._repo.create(row)

    def update_consensus(
        self,
        consensus_id: int,
        data: ForecastConsensusUpdate,
        user_id: int,
    ) -> ForecastConsensus:
        consensus = self.get_consensus(consensus_id)
        if consensus.status in ("approved", "frozen"):
            raise to_http_exception(
                BusinessRuleViolationException(
                    "Cannot modify approved/frozen consensus record."
                )
            )

        if data.status == "approved":
            raise to_http_exception(
                InvalidStateTransitionException("ForecastConsensus", consensus.status, "approved")
            )

        payload = data.model_dump(exclude_unset=True)

        baseline = self._d(payload.get("baseline_qty")) if "baseline_qty" in payload else self._d(consensus.baseline_qty)
        sales = self._d(payload.get("sales_override_qty")) if "sales_override_qty" in payload else self._d(consensus.sales_override_qty)
        marketing = (
            self._d(payload.get("marketing_uplift_qty"))
            if "marketing_uplift_qty" in payload
            else self._d(consensus.marketing_uplift_qty)
        )
        finance = (
            self._d(payload.get("finance_adjustment_qty"))
            if "finance_adjustment_qty" in payload
            else self._d(consensus.finance_adjustment_qty)
        )
        if "constraint_cap_qty" in payload:
            cap = self._d(payload.get("constraint_cap_qty")) if payload.get("constraint_cap_qty") is not None else None
        else:
            cap = self._d(consensus.constraint_cap_qty) if consensus.constraint_cap_qty is not None else None
        pre, final = self._compute_final(baseline, sales, marketing, finance, cap)

        updates = {
            "baseline_qty": baseline,
            "sales_override_qty": sales,
            "marketing_uplift_qty": marketing,
            "finance_adjustment_qty": finance,
            "constraint_cap_qty": cap,
            "pre_consensus_qty": pre,
            "final_consensus_qty": final,
            "version": consensus.version + 1,
        }
        if data.status is not None:
            updates["status"] = data.status
        if data.notes is not None:
            updates["notes"] = data.notes

        return self._repo.update(consensus, updates)

    def approve_consensus(
        self,
        consensus_id: int,
        body: ForecastConsensusApproveRequest,
        approver_id: int,
    ) -> ForecastConsensus:
        consensus = self.get_consensus(consensus_id)
        if consensus.status in ("approved", "frozen"):
            raise to_http_exception(
                InvalidStateTransitionException("ForecastConsensus", consensus.status, "approved")
            )

        notes = consensus.notes or ""
        if body.notes:
            notes = f"{notes}\n[Approved] {body.notes}".strip()

        result = self._repo.update(
            consensus,
            {
                "status": "approved",
                "approved_by": approver_id,
                "approved_at": datetime.utcnow(),
                "notes": notes,
            },
        )

        demand_plan = self._demand_repo.get_by_product_and_period(
            product_id=result.product_id,
            period=result.period,
        )
        if demand_plan:
            self._demand_repo.update(
                demand_plan,
                {
                    "consensus_qty": result.final_consensus_qty,
                    "version": demand_plan.version + 1,
                },
            )
        else:
            self._demand_repo.create(
                DemandPlan(
                    product_id=result.product_id,
                    period=result.period,
                    region="Global",
                    channel="All",
                    forecast_qty=result.baseline_qty,
                    consensus_qty=result.final_consensus_qty,
                    status="draft",
                    created_by=approver_id,
                    version=1,
                )
            )

        return result
