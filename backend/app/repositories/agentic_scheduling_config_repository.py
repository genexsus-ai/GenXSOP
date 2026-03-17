import json
from typing import Optional

from sqlalchemy.orm import Session

from app.models.agentic_scheduling_config import AgenticSchedulingConfig
from app.repositories.base import BaseRepository


class AgenticSchedulingConfigRepository(BaseRepository[AgenticSchedulingConfig]):
    def __init__(self, db: Session):
        super().__init__(AgenticSchedulingConfig, db)

    def get_by_type_scope_name(self, config_type: str, scope: str = "global", name: str = "default") -> Optional[AgenticSchedulingConfig]:
        return (
            self.db.query(AgenticSchedulingConfig)
            .filter(
                AgenticSchedulingConfig.config_type == config_type,
                AgenticSchedulingConfig.scope == scope,
                AgenticSchedulingConfig.name == name,
                AgenticSchedulingConfig.is_active == True,
            )
            .first()
        )

    def upsert(
        self,
        *,
        config_type: str,
        config: dict,
        scope: str = "global",
        name: str = "default",
        updated_by: Optional[int] = None,
    ) -> AgenticSchedulingConfig:
        existing = self.get_by_type_scope_name(config_type=config_type, scope=scope, name=name)
        payload = json.dumps(config)
        if existing:
            return self.update(
                existing,
                {
                    "config_json": payload,
                    "version": existing.version + 1,
                    "updated_by": updated_by,
                    "is_active": True,
                },
            )

        return self.create(
            AgenticSchedulingConfig(
                config_type=config_type,
                scope=scope,
                name=name,
                config_json=payload,
                version=1,
                updated_by=updated_by,
                is_active=True,
            )
        )
