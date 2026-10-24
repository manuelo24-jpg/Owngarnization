import datetime as dt
from typing import Literal, Optional, List
from pydantic import BaseModel, EmailStr, Field, ConfigDict, model_validator


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
    created_at: dt.datetime


# --- TAREAS ---

class TaskBase(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    kind: TaskKind = "daily"
    importance: TaskImportance = "medium"
    date: Optional[dt.date] = None
    start_time: Optional[dt.time] = None
    end_time: Optional[dt.time] = None

    @model_validator(mode="after")
    def validate_task_coherence(self):
        # Si es common, date debe ser None
        if self.kind == "common" and self.date is not None:
            self.date = None

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
