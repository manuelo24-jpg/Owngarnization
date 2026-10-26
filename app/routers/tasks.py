import datetime as dt
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.deps import get_db, get_current_user
from app.models import User
from app.schemas import (
    TaskCreate,
    TaskUpdate,
    TaskResponse,
    OccurrenceResponse,
    OccurrenceUpdate,
    OccurrenceReorder,
    TaskStatus,
    TaskImportance,
    TaskKind
)
from app.services import task_service, occurrence_service

router = APIRouter(prefix="/api", tags=["Tareas"])


@router.get("/occurrences", response_model=List[OccurrenceResponse])
def get_occurrences(
    start: dt.date = Query(..., description="Fecha inicial del rango (YYYY-MM-DD)"),
    end: dt.date = Query(..., description="Fecha final del rango (YYYY-MM-DD)"),
    q: Optional[str] = Query(None, description="Búsqueda por texto en título o descripción"),
    status_filter: Optional[TaskStatus] = Query(None, alias="status", description="Filtrar por estado"),
    importance_filter: Optional[TaskImportance] = Query(None, alias="importance", description="Filtrar por importancia"),
    kind_filter: Optional[TaskKind] = Query(None, alias="kind", description="Filtrar por tipo (common o daily)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Obtiene las ocurrencias de tareas en un rango de fechas con búsqueda y filtros.
    """
    if end < start:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La fecha de fin debe ser posterior o igual a la fecha de inicio"
        )

    if (end - start).days > 370:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El rango de fechas no puede superar un año"
        )

    return occurrence_service.get_occurrences_in_range(
        db=db,
        user_id=current_user.id,
        start=start,
        end=end,
        q=q,
        status=status_filter,
        importance=importance_filter,
        kind=kind_filter,
    )


@router.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    task_in: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Crea una nueva tarea (común o del día) y genera su ocurrencia inicial."""
    return task_service.create_task(db=db, user_id=current_user.id, task_in=task_in)


@router.get("/tasks/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Obtiene el detalle completo de una tarea del usuario."""
    task = task_service.get_task_by_id(db=db, user_id=current_user.id, task_id=task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tarea no encontrada"
        )
    return task


@router.patch("/tasks/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: int,
    task_in: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Actualiza los campos de una tarea existente."""
    task = task_service.update_task(
        db=db,
        user_id=current_user.id,
        task_id=task_id,
        task_in=task_in
    )
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tarea no encontrada"
        )
    return task


@router.delete("/tasks/{task_id}")
def delete_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Elimina/desactiva una tarea para el usuario."""
    success = task_service.delete_task(db=db, user_id=current_user.id, task_id=task_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tarea no encontrada"
        )
    return {"message": "Tarea eliminada correctamente"}


@router.patch("/occurrences/{occurrence_id}", response_model=OccurrenceResponse)
@router.patch("/api/occurrences/{occurrence_id}", response_model=OccurrenceResponse)
def update_occurrence(
    occurrence_id: int,
    occ_in: OccurrenceUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Actualiza el estado, horario o fecha de una ocurrencia específica."""
    occ, error_msg = occurrence_service.update_occurrence(
        db=db,
        user_id=current_user.id,
        occurrence_id=occurrence_id,
        occ_in=occ_in
    )
    if error_msg == "Ocurrencia no encontrada":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error_msg)
    elif error_msg:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)

    return occ


@router.post("/occurrences/reorder")
def reorder_occurrences(
    reorder_in: OccurrenceReorder,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Guarda el orden manual de los post-its tras drag & drop para una fecha concreta."""
    occurrence_service.reorder_occurrences(
        db=db,
        user_id=current_user.id,
        reorder_in=reorder_in
    )
    return {"message": "Orden actualizado correctamente"}
