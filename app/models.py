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
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now(), nullable=False)

    tasks = relationship("Task", back_populates="user", cascade="all, delete-orphan")


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
    start_time = Column(Time, nullable=True)  # Override opcional para el día
    end_time = Column(Time, nullable=True)    # Override opcional para el día

    task = relationship("Task", back_populates="occurrences")

    __table_args__ = (
        UniqueConstraint("task_id", "date", name="uq_task_occurrence_date"),
        Index("ix_occurrences_task_date", "task_id", "date"),
    )
