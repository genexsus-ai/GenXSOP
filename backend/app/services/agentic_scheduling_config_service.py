import json
from typing import Any, Dict

from sqlalchemy.orm import Session

from app.repositories.agentic_scheduling_config_repository import AgenticSchedulingConfigRepository
from app.schemas.agentic_scheduling_config import (
    AgenticSchedulingConfigResponse,
    AgenticSchedulingConfigUpsertRequest,
)


DEFAULT_OBJECTIVES: Dict[str, Any] = {
    "tardiness": 0.45,
    "changeover": 0.25,
    "utilization": 0.30,
}

DEFAULT_POLICIES: Dict[str, Any] = {
    "auto_publish": False,
    "maker_checker_required": True,
    "maker_checker_threshold_pct": 20,
    "max_resequence_distance": 5,
}


class AgenticSchedulingConfigService:
    def __init__(self, db: Session):
        self._repo = AgenticSchedulingConfigRepository(db)

    def get_objectives(self, scope: str = "global", name: str = "default") -> AgenticSchedulingConfigResponse:
        row = self._repo.get_by_type_scope_name("objectives", scope=scope, name=name)
        if not row:
            row = self._repo.upsert(config_type="objectives", config=DEFAULT_OBJECTIVES, scope=scope, name=name)
        return self._to_response(row)

    def upsert_objectives(
        self,
        payload: AgenticSchedulingConfigUpsertRequest,
        user_id: int,
    ) -> AgenticSchedulingConfigResponse:
        row = self._repo.upsert(
            config_type="objectives",
            config=payload.config,
            scope=payload.scope,
            name=payload.name,
            updated_by=user_id,
        )
        return self._to_response(row)

    def get_policies(self, scope: str = "global", name: str = "default") -> AgenticSchedulingConfigResponse:
        row = self._repo.get_by_type_scope_name("policies", scope=scope, name=name)
        if not row:
            row = self._repo.upsert(config_type="policies", config=DEFAULT_POLICIES, scope=scope, name=name)
        return self._to_response(row)

    def upsert_policies(
        self,
        payload: AgenticSchedulingConfigUpsertRequest,
        user_id: int,
    ) -> AgenticSchedulingConfigResponse:
        row = self._repo.upsert(
            config_type="policies",
            config=payload.config,
            scope=payload.scope,
            name=payload.name,
            updated_by=user_id,
        )
        return self._to_response(row)

    def _to_response(self, row) -> AgenticSchedulingConfigResponse:
        parsed = {}
        if row.config_json:
            try:
                parsed = json.loads(row.config_json)
            except Exception:
                parsed = {"raw": row.config_json}

        return AgenticSchedulingConfigResponse(
            id=row.id,
            config_type=row.config_type,
            scope=row.scope,
            name=row.name,
            config=parsed,
            version=row.version,
            is_active=row.is_active,
            updated_by=row.updated_by,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
