from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Date,
    Time,
    Boolean,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    Index,
    func
)
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), nullable=False)
    password_hash = Column(String(255), nullable=False)
    timezone = Column(String(64), default="Europe/Madrid", nullable=False)
    reminders_enabled = Column(Boolean, default=True, nullable=False)
    reminder_offset_min = Column(Integer, default=10, nullable=False)
    last_space = Column(String(20), default="personal", nullable=True)  # "personal" | "projects"
    last_project_id = Column(Integer, ForeignKey("projects.id", ondelete="SET NULL", use_alter=True, name="fk_users_last_project_id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now(), nullable=False)

    tasks = relationship("Task", back_populates="user", cascade="all, delete-orphan")
    push_subscriptions = relationship("PushSubscription", back_populates="user", cascade="all, delete-orphan")
    owned_projects = relationship("Project", back_populates="owner", foreign_keys="Project.owner_id", cascade="all, delete-orphan")
    project_memberships = relationship("ProjectMember", back_populates="user", cascade="all, delete-orphan")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    kind = Column(String(20), nullable=False, default="daily")  # "common" | "daily"
    importance = Column(String(20), nullable=False, default="medium")  # "low" | "medium" | "high" | "urgent"
    date = Column(Date, nullable=True, index=True)  # Solo para "daily", NULL para "common"
    start_time = Column(Time, nullable=True)
    end_time = Column(Time, nullable=True)
    days_of_week = Column(String(50), nullable=True)  # Ej: "1,2,3,4,5" (1=Lunes .. 7=Domingo), NULL para todos los días
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="tasks")
    occurrences = relationship("TaskOccurrence", back_populates="task", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_tasks_user_date", "user_id", "date"),
    )


class TaskOccurrence(Base):
    __tablename__ = "task_occurrences"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    status = Column(String(20), nullable=False, default="not_started")  # "not_started" | "in_progress" | "done"
    position = Column(Integer, default=0, nullable=False)
    manual_order = Column(Boolean, default=False, nullable=False)
    start_time = Column(Time, nullable=True)  # Override opcional para el día
    end_time = Column(Time, nullable=True)    # Override opcional para el día
    reminder_sent_at = Column(DateTime(timezone=True), nullable=True)

    task = relationship("Task", back_populates="occurrences")

    __table_args__ = (
        UniqueConstraint("task_id", "date", name="uq_task_occurrence_date"),
        Index("ix_occurrences_task_date", "task_id", "date"),
    )


class PushSubscription(Base):
    __tablename__ = "push_subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    endpoint = Column(Text, unique=True, nullable=False)
    p256dh = Column(String(255), nullable=False)
    auth = Column(String(255), nullable=False)
    user_agent = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now(), nullable=False)
    last_success_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="push_subscriptions")


# --- MODELOS DE PROYECTOS Y ESPACIOS ---

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    color = Column(String(20), nullable=True)
    icon = Column(String(20), nullable=True)
    is_archived = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), server_default=func.now(), nullable=False)

    owner = relationship("User", foreign_keys=[owner_id], back_populates="owned_projects")
    members = relationship("ProjectMember", back_populates="project", cascade="all, delete-orphan")
    roles = relationship("ProjectRole", back_populates="project", cascade="all, delete-orphan")
    columns = relationship("ProjectColumn", back_populates="project", cascade="all, delete-orphan", order_by="ProjectColumn.position")
    tasks = relationship("ProjectTask", back_populates="project", cascade="all, delete-orphan")


class ProjectRole(Base):
    __tablename__ = "project_roles"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(50), nullable=False)
    color = Column(String(20), default="#C9B49A", nullable=False)
    position = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now(), nullable=False)

    project = relationship("Project", back_populates="roles")
    members = relationship("ProjectMember", back_populates="role")
    tasks = relationship("ProjectTask", back_populates="role")

    __table_args__ = (
        UniqueConstraint("project_id", "name", name="uq_project_role_project_name"),
    )


class ProjectMember(Base):
    __tablename__ = "project_members"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    permission = Column(String(20), default="member", nullable=False)  # "owner" | "admin" | "member" | "viewer"
    role_id = Column(Integer, ForeignKey("project_roles.id", ondelete="SET NULL"), nullable=True, index=True)
    weekly_hours = Column(Integer, nullable=True)
    joined_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now(), nullable=False)

    project = relationship("Project", back_populates="members")
    user = relationship("User", back_populates="project_memberships")
    role = relationship("ProjectRole", back_populates="members")

    __table_args__ = (
        UniqueConstraint("project_id", "user_id", name="uq_project_member_project_user"),
    )


class ProjectColumn(Base):
    __tablename__ = "project_columns"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(50), nullable=False)
    position = Column(Integer, default=0, nullable=False)
    is_done = Column(Boolean, default=False, nullable=False)

    project = relationship("Project", back_populates="columns")
    tasks = relationship("ProjectTask", back_populates="column", cascade="all, delete-orphan", order_by="ProjectTask.position")

    __table_args__ = (
        Index("ix_project_columns_project_pos", "project_id", "position"),
    )


class ProjectTaskAssignee(Base):
    __tablename__ = "project_task_assignees"

    task_id = Column(Integer, ForeignKey("project_tasks.id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    assigned_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now(), nullable=False)

    user = relationship("User")
    task = relationship("ProjectTask", back_populates="task_assignees")


class ProjectTask(Base):
    __tablename__ = "project_tasks"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    column_id = Column(Integer, ForeignKey("project_columns.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    priority = Column(String(20), default="medium", nullable=False)  # "low" | "medium" | "high" | "urgent"
    position = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    date = Column(Date, nullable=True, index=True)
    start_time = Column(Time, nullable=True)
    end_time = Column(Time, nullable=True)
    due_date = Column(Date, nullable=True)
    estimated_minutes = Column(Integer, nullable=True)
    role_id = Column(Integer, ForeignKey("project_roles.id", ondelete="SET NULL"), nullable=True, index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    reminder_sent_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), server_default=func.now(), nullable=False)

    project = relationship("Project", back_populates="tasks")
    column = relationship("ProjectColumn", back_populates="tasks")
    creator = relationship("User", foreign_keys=[created_by])
    role = relationship("ProjectRole", back_populates="tasks")
    task_assignees = relationship("ProjectTaskAssignee", back_populates="task", cascade="all, delete-orphan")
    assignees = relationship("User", secondary="project_task_assignees", viewonly=True)

    __table_args__ = (
        Index("ix_project_tasks_pos", "project_id", "column_id", "position"),
        Index("ix_project_tasks_sched", "project_id", "date", "start_time"),
    )
