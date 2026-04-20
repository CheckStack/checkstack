from datetime import datetime

from pydantic import BaseModel, Field


class TagRef(BaseModel):
    id: int
    name: str
    color: str | None = None

    model_config = {"from_attributes": True}


class MonitorCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    url: str = Field(min_length=1)
    interval_seconds: int = Field(default=60, ge=10, le=3600)
    timeout_seconds: int = Field(default=10, ge=1, le=120)
    failure_threshold: int = Field(default=3, ge=1, le=20)
    alerts_enabled: bool = True
    tag_ids: list[int] = Field(default_factory=list)


class MonitorUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    url: str | None = None
    interval_seconds: int | None = Field(default=None, ge=10, le=3600)
    timeout_seconds: int | None = Field(default=None, ge=1, le=120)
    failure_threshold: int | None = Field(default=None, ge=1, le=20)
    alerts_enabled: bool | None = None
    tag_ids: list[int] | None = None


class MonitorRead(BaseModel):
    id: int
    name: str
    url: str
    interval_seconds: int
    timeout_seconds: int
    failure_threshold: int
    consecutive_failures: int
    alerts_enabled: bool
    last_status: str | None
    last_checked_at: datetime | None
    tls_cert_expires_at: datetime | None = None
    tls_cert_subject: str | None = None
    tls_cert_checked_at: datetime | None = None
    tls_cert_probe_error: str | None = None
    tags: list[TagRef] = Field(default_factory=list)
    alerts_will_fire: bool = True
    created_at: datetime

    model_config = {"from_attributes": True}


class MonitorCreateResponse(MonitorRead):
    pass


class CheckResultRead(BaseModel):
    id: int
    ok: bool
    status_code: int | None
    latency_ms: float | None
    error_message: str | None
    checked_at: datetime

    model_config = {"from_attributes": True}


class MonitorMetricPoint(BaseModel):
    timestamp: datetime
    status: str
    response_time_ms: float


class SlaResponse(BaseModel):
    monitor_id: int
    window: str
    uptime_percent: float
    total_checks: int
    successful_checks: int


class IncidentRead(BaseModel):
    id: int
    monitor_id: int
    title: str
    summary: str
    status: str
    detected_by: str
    started_at: datetime
    resolved_at: datetime | None
    duration_seconds: int | None = None

    model_config = {"from_attributes": True}


class IncidentDetailRead(IncidentRead):
    start_time: datetime
    end_time: datetime | None
    monitor_name: str
    monitor_url: str


class MonitorInIncident(BaseModel):
    id: int
    name: str
    url: str
    alerts_enabled: bool

