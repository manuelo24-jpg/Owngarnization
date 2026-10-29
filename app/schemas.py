import datetime as dt
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from typing import Literal, Optional, List
from pydantic import BaseModel, EmailStr, Field, ConfigDict, model_validator

VALID_REMINDER_OFFSETS = (0, 5, 10, 15, 30, 60)


# Tipos válidos
TaskKind = Literal["common", "daily"]
TaskImportance = Literal["low", "medium", "high", "urgent"]
TaskStatus = Literal["not_started", "in_progress", "done"]


# --- USUARIO ---

class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(min_length=2, max_length=100)
    password: str = Field(min_length=6, max_length=128)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    username: str
    timezone: str = "Europe/Madrid"
    reminders_enabled: bool = True
    reminder_offset_min: int = 10
    created_at: dt.datetime


class UserPreferencesUpdate(BaseModel):
    timezone: Optional[str] = Field(default=None, min_length=1, max_length=64)
    reminders_enabled: Optional[bool] = None
    reminder_offset_min: Optional[int] = None

    @model_validator(mode="after")
    def validate_preferences(self):
        if self.timezone is not None:
            try:
                ZoneInfo(self.timezone)
            except (ZoneInfoNotFoundError, KeyError, ValueError):
                raise ValueError("Zona horaria IANA no válida")
        if self.reminder_offset_min is not None and self.reminder_offset_min not in VALID_REMINDER_OFFSETS:
            raise ValueError(f"La antelación debe ser una de: {VALID_REMINDER_OFFSETS}")
        return self


class UserPreferencesResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    timezone: str
    reminders_enabled: bool
    reminder_offset_min: int


class PushSubscriptionKeys(BaseModel):
    p256dh: str = Field(min_length=1, max_length=255)
    auth: str = Field(min_length=1, max_length=255)


class PushSubscriptionCreate(BaseModel):
    endpoint: str = Field(min_length=10, max_length=2048)
    keys: PushSubscriptionKeys


class PushSubscriptionDelete(BaseModel):
    endpoint: str = Field(min_length=10, max_length=2048)


# --- TAREAS ---

class TaskBase(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    kind: TaskKind = "daily"
    importance: TaskImportance = "medium"
    date: Optional[dt.date] = None
    start_time: Optional[dt.time] = None
    end_time: Optional[dt.time] = None
    days_of_week: Optional[str] = None  # Coma-separado: ej. "1,2,3,4,5" (1=Lunes .. 7=Domingo)

    @model_validator(mode="after")
    def validate_task_coherence(self):
        # Si es common, date debe ser None
        if self.kind == "common" and self.date is not None:
            self.date = None

        # Si es daily, days_of_week debe ser None
        if self.kind == "daily" and self.days_of_week is not None:
            self.days_of_week = None

        # Validación horaria: end_time > start_time
        if self.start_time and self.end_time and self.end_time <= self.start_time:
            raise ValueError("La hora de fin debe ser posterior a la hora de inicio")

        return self


class TaskCreate(TaskBase):
    initial_status: TaskStatus = "not_started"


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    kind: Optional[TaskKind] = None
    importance: Optional[TaskImportance] = None
    date: Optional[dt.date] = None
    start_time: Optional[dt.time] = None
    end_time: Optional[dt.time] = None
    days_of_week: Optional[str] = None
    is_active: Optional[bool] = None

    @model_validator(mode="after")
    def validate_times(self):
        if self.start_time and self.end_time and self.end_time <= self.start_time:
            raise ValueError("La hora de fin debe ser posterior a la hora de inicio")
        return self



class TaskResponse(TaskBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    is_active: bool
    created_at: dt.datetime
    updated_at: dt.datetime


# --- OCURRENCIAS DE TAREAS ---

class OccurrenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    date: dt.date
    status: TaskStatus
    position: int
    manual_order: bool = False
    start_time: Optional[dt.time] = None
    end_time: Optional[dt.time] = None
    task: TaskResponse


class OccurrenceUpdate(BaseModel):
    status: Optional[TaskStatus] = None
    date: Optional[dt.date] = None
    start_time: Optional[dt.time] = None
    end_time: Optional[dt.time] = None

    @model_validator(mode="after")
    def validate_times(self):
        if self.start_time and self.end_time and self.end_time <= self.start_time:
            raise ValueError("La hora de fin debe ser posterior a la hora de inicio")
        return self


class OccurrenceReorder(BaseModel):
    date: dt.date
    ordered_ids: List[int]  # Lista ordenada de ids de TaskOccurrence
