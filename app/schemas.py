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


# --- ESPACIOS Y PROYECTOS ---

SpaceType = Literal["personal", "projects"]
ProjectPermission = Literal["owner", "admin", "member", "viewer"]
ProjectTaskPriority = Literal["low", "medium", "high", "urgent"]


class UserSpaceUpdate(BaseModel):
    last_space: Optional[SpaceType] = None
    last_project_id: Optional[int] = None


class SpaceSummaryPersonal(BaseModel):
    today_total: int
    today_done: int


class SpaceSummaryProjects(BaseModel):
    active_projects: int
    assigned_tasks: int


class SpacesSummaryResponse(BaseModel):
    personal: SpaceSummaryPersonal
    projects: SpaceSummaryProjects


# --- ROLES DE PROYECTO ---

class ProjectRoleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    color: Optional[str] = Field(default="#C9B49A", max_length=20)
    position: Optional[int] = 0


class ProjectRoleUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=50)
    color: Optional[str] = Field(default=None, max_length=20)
    position: Optional[int] = None


class ProjectRoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    name: str
    color: str
    position: int


# --- MIEMBROS DE PROYECTO ---

class ProjectMemberInvite(BaseModel):
    email: EmailStr
    permission: ProjectPermission = "member"
    role_id: Optional[int] = None
    weekly_hours: Optional[int] = Field(default=None, ge=0, le=168)


class ProjectMemberUpdate(BaseModel):
    permission: Optional[ProjectPermission] = None
    role_id: Optional[int] = None
    weekly_hours: Optional[int] = Field(default=None, ge=0, le=168)


class ProjectMemberSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    username: str
    email: str
    permission: str
    role_name: Optional[str] = None
    role_color: Optional[str] = None


class ProjectMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    user_id: int
    username: str
    email: str
    permission: str
    role_id: Optional[int] = None
    role_name: Optional[str] = None
    role_color: Optional[str] = None
    weekly_hours: Optional[int] = None
    joined_at: dt.datetime


# --- COLUMNAS DE PROYECTO ---

class ProjectColumnCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    position: Optional[int] = None
    is_done: Optional[bool] = False


class ProjectColumnUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=50)
    position: Optional[int] = None
    is_done: Optional[bool] = None


class ProjectColumnReorder(BaseModel):
    column_ids: List[int]


# --- TAREAS DE PROYECTO ---

class ScheduleOverlapWarning(BaseModel):
    task_id: int
    user_id: int
    username: str
    conflicting_task_id: int
    conflicting_title: str
    date: dt.date
    start_time: dt.time
    end_time: dt.time


class ProjectTaskCreate(BaseModel):
    column_id: int
    title: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    priority: ProjectTaskPriority = "medium"
    date: Optional[dt.date] = None
    start_time: Optional[dt.time] = None
    end_time: Optional[dt.time] = None
    due_date: Optional[dt.date] = None
    estimated_minutes: Optional[int] = Field(default=None, ge=0)
    role_id: Optional[int] = None
    assignee_ids: List[int] = []

    @model_validator(mode="after")
    def validate_times(self):
        if self.start_time and self.end_time and self.end_time <= self.start_time:
            raise ValueError("La hora de fin debe ser posterior a la hora de inicio")
        return self


class ProjectTaskUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    priority: Optional[ProjectTaskPriority] = None
    column_id: Optional[int] = None
    position: Optional[int] = None
    date: Optional[dt.date] = None
    start_time: Optional[dt.time] = None
    end_time: Optional[dt.time] = None
    due_date: Optional[dt.date] = None
    estimated_minutes: Optional[int] = Field(default=None, ge=0)
    role_id: Optional[int] = None
    assignee_ids: Optional[List[int]] = None

    @model_validator(mode="after")
    def validate_times(self):
        if self.start_time and self.end_time and self.end_time <= self.start_time:
            raise ValueError("La hora de fin debe ser posterior a la hora de inicio")
        return self


class ProjectTaskMove(BaseModel):
    task_id: int
    column_id: int
    position: int


class ProjectTaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    column_id: int
    title: str
    description: Optional[str] = None
    priority: ProjectTaskPriority
    position: int
    date: Optional[dt.date] = None
    start_time: Optional[dt.time] = None
    end_time: Optional[dt.time] = None
    due_date: Optional[dt.date] = None
    estimated_minutes: Optional[int] = None
    role_id: Optional[int] = None
    role_name: Optional[str] = None
    role_color: Optional[str] = None
    completed_at: Optional[dt.datetime] = None
    created_by: Optional[int] = None
    assignee_ids: List[int] = []
    assignees: List[ProjectMemberSummary] = []
    overlap_warnings: List[ScheduleOverlapWarning] = []
    created_at: dt.datetime
    updated_at: dt.datetime


class ProjectColumnResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    name: str
    position: int
    is_done: bool
    tasks: List[ProjectTaskResponse] = []


# --- PROYECTO PRINCIPAL ---

class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = None
    color: Optional[str] = Field(default="#C9B49A", max_length=20)
    icon: Optional[str] = Field(default="📁", max_length=20)


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = None
    color: Optional[str] = Field(default=None, max_length=20)
    icon: Optional[str] = Field(default=None, max_length=20)
    is_archived: Optional[bool] = None


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    is_archived: bool
    owner_id: int
    my_permission: str
    my_role: Optional[str] = None
    total_tasks: int = 0
    done_tasks: int = 0
    progress_percent: int = 0
    members_count: int = 0
    members: List[ProjectMemberSummary] = []
    created_at: dt.datetime
    updated_at: dt.datetime


class ProjectDetailResponse(ProjectResponse):
    columns: List[ProjectColumnResponse] = []
    roles: List[ProjectRoleResponse] = []
    all_members: List[ProjectMemberResponse] = []


# --- HORARIO Y CARGA HORARIA ---

class ProjectScheduleTaskResponse(BaseModel):
    task: ProjectTaskResponse
    overlaps: List[ScheduleOverlapWarning] = []


class ProjectScheduleResponse(BaseModel):
    start: dt.date
    end: dt.date
    tasks: List[ProjectScheduleTaskResponse]
    by_person: dict[int, List[ProjectScheduleTaskResponse]]


class ProjectWorkloadMember(BaseModel):
    user_id: int
    username: str
    weekly_hours: Optional[int] = None
    planned_hours: float
    task_count: int


class ProjectWorkloadResponse(BaseModel):
    week_start: dt.date
    week_end: dt.date
    members: List[ProjectWorkloadMember]
