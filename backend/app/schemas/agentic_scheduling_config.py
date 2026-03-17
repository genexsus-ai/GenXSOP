from datetime import datetime
from typing import Dict, Literal, Optional

from pydantic import BaseModel, Field


ConfigType = Literal["objectives", "policies"]


class AgenticSchedulingConfigUpsertRequest(BaseModel):
    scope: str = "global"
    name: str = "default"
    config: Dict = Field(default_factory=dict)


class AgenticSchedulingConfigResponse(BaseModel):
    id: int
    config_type: ConfigType
    scope: str
    name: str
    config: Dict = Field(default_factory=dict)
    version: int
    is_active: bool
    updated_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
