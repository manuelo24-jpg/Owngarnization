from typing import List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import (
    Project,
    ProjectMember,
    ProjectRole,
    ProjectColumn,
    ProjectTask,
    User
)
from app.schemas import (
    ProjectCreate,
    ProjectUpdate,
    ProjectRoleCreate,
    ProjectRoleUpdate,
    ProjectMemberInvite,
    ProjectMemberUpdate,
    ProjectColumnCreate,
    ProjectColumnUpdate,
)

PERMISSION_LEVELS = {
    "viewer": 1,
    "member": 2,
    "admin": 3,
    "owner": 4,
}


def get_member(db: Session, project_id: int, user_id: int) -> Optional[ProjectMember]:
    """Obtiene la membresía del usuario en el proyecto si existe."""
    return db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == user_id
    ).first()


def require_member(db: Session, project_id: int, user_id: int) -> Tuple[Project, ProjectMember]:
    """Valida que el proyecto exista y que el usuario sea miembro activo."""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.is_active == True
    ).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proyecto no encontrado"
        )
    member = get_member(db, project_id, user_id)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No eres miembro de este proyecto"
        )
    return project, member


def require_permission(db: Session, project_id: int, user_id: int, min_perm: str) -> Tuple[Project, ProjectMember]:
    """Valida que el usuario tenga al menos el nivel de permiso requerido."""
    project, member = require_member(db, project_id, user_id)
    user_level = PERMISSION_LEVELS.get(member.permission, 0)
    required_level = PERMISSION_LEVELS.get(min_perm, 99)
    if user_level < required_level:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Se requiere permiso de {min_perm} o superior"
        )
    return project, member


# --- PROYECTOS CRUD ---

def create_project(db: Session, user: User, data: ProjectCreate) -> Project:
    """
    Crea un nuevo proyecto con:
    1. Propietario inicial como miembro 'owner'.
    2. Rol por defecto 'General'.
    3. 4 Columnas por defecto: Pendiente, En curso, En revisión, Hecho (is_done=True).
    """
    project = Project(
        owner_id=user.id,
        name=data.name.strip(),
        description=data.description,
        color=data.color or "#C9B49A",
        icon=data.icon or "📁",
        is_archived=False,
        is_active=True
    )
    db.add(project)
    db.flush()

    # Rol por defecto 'General'
    default_role = ProjectRole(
        project_id=project.id,
        name="General",
        color="#C9B49A",
        position=0
    )
    db.add(default_role)
    db.flush()

    # Miembro creador con permiso 'owner' y rol 'General'
    owner_member = ProjectMember(
        project_id=project.id,
        user_id=user.id,
        permission="owner",
        role_id=default_role.id
    )
    db.add(owner_member)

    # Columnas por defecto
    default_columns = [
        ("Pendiente", 0, False),
        ("En curso", 1, False),
        ("En revisión", 2, False),
        ("Hecho", 3, True),
    ]
    for col_name, pos, is_done in default_columns:
        col = ProjectColumn(
            project_id=project.id,
            name=col_name,
            position=pos,
            is_done=is_done
        )
        db.add(col)

    db.commit()
    db.refresh(project)
    return project


def list_user_projects(db: Session, user_id: int, include_archived: bool = False) -> List[dict]:
    """Lista todos los proyectos en los que el usuario participa."""
    query = (
        db.query(Project, ProjectMember)
        .join(ProjectMember, Project.id == ProjectMember.project_id)
        .filter(ProjectMember.user_id == user_id, Project.is_active == True)
    )
    if not include_archived:
        query = query.filter(Project.is_archived == False)

    rows = query.order_by(Project.updated_at.desc()).all()
    results = []
    for proj, member in rows:
        total_tasks = db.query(func.count(ProjectTask.id)).filter(
            ProjectTask.project_id == proj.id,
            ProjectTask.is_active == True
        ).scalar() or 0
        done_tasks = db.query(func.count(ProjectTask.id)).join(
            ProjectColumn, ProjectTask.column_id == ProjectColumn.id
        ).filter(
            ProjectTask.project_id == proj.id,
            ProjectTask.is_active == True,
            ProjectColumn.is_done == True
        ).scalar() or 0

        members_count = db.query(func.count(ProjectMember.id)).filter(
            ProjectMember.project_id == proj.id
        ).scalar() or 0

        progress = int((done_tasks / total_tasks * 100)) if total_tasks > 0 else 0

        # Miembros resumen (máx 5)
        top_members = db.query(ProjectMember).filter(
            ProjectMember.project_id == proj.id
        ).limit(5).all()
        members_data = []
        for m in top_members:
            members_data.append({
                "id": m.id,
                "user_id": m.user.id,
                "username": m.user.username,
                "email": m.user.email,
                "permission": m.permission,
                "role_name": m.role.name if m.role else None,
                "role_color": m.role.color if m.role else None,
            })

        results.append({
            "id": proj.id,
            "name": proj.name,
            "description": proj.description,
            "color": proj.color,
            "icon": proj.icon,
            "is_archived": proj.is_archived,
            "owner_id": proj.owner_id,
            "my_permission": member.permission,
            "my_role": member.role.name if member.role else None,
            "total_tasks": total_tasks,
            "done_tasks": done_tasks,
            "progress_percent": progress,
            "members_count": members_count,
            "members": members_data,
            "created_at": proj.created_at,
            "updated_at": proj.updated_at,
        })
    return results


def get_project_detail(db: Session, project_id: int, user_id: int) -> dict:
    """Devuelve la información completa del proyecto para su tablero."""
    proj, my_member = require_member(db, project_id, user_id)

    total_tasks = db.query(func.count(ProjectTask.id)).filter(
        ProjectTask.project_id == proj.id,
        ProjectTask.is_active == True
    ).scalar() or 0
    done_tasks = db.query(func.count(ProjectTask.id)).join(
        ProjectColumn, ProjectTask.column_id == ProjectColumn.id
    ).filter(
        ProjectTask.project_id == proj.id,
        ProjectTask.is_active == True,
        ProjectColumn.is_done == True
    ).scalar() or 0
    progress = int((done_tasks / total_tasks * 100)) if total_tasks > 0 else 0

    # Columnas con tareas
    columns = db.query(ProjectColumn).filter(
        ProjectColumn.project_id == proj.id
    ).order_by(ProjectColumn.position.asc()).all()

    cols_data = []
    for col in columns:
        tasks = db.query(ProjectTask).filter(
            ProjectTask.column_id == col.id,
            ProjectTask.is_active == True
        ).order_by(ProjectTask.position.asc()).all()

        tasks_data = []
        for t in tasks:
            assignee_data = []
            assignee_ids = []
            for u in t.assignees:
                assignee_ids.append(u.id)
                # buscar su rol en este proyecto
                u_mem = get_member(db, proj.id, u.id)
                assignee_data.append({
                    "id": u_mem.id if u_mem else 0,
                    "user_id": u.id,
                    "username": u.username,
                    "email": u.email,
                    "permission": u_mem.permission if u_mem else "member",
                    "role_name": u_mem.role.name if (u_mem and u_mem.role) else None,
                    "role_color": u_mem.role.color if (u_mem and u_mem.role) else None,
                })

            tasks_data.append({
                "id": t.id,
                "project_id": t.project_id,
                "column_id": t.column_id,
                "title": t.title,
                "description": t.description,
                "priority": t.priority,
                "position": t.position,
                "date": t.date,
                "start_time": t.start_time,
                "end_time": t.end_time,
                "due_date": t.due_date,
                "estimated_minutes": t.estimated_minutes,
                "role_id": t.role_id,
                "role_name": t.role.name if t.role else None,
                "role_color": t.role.color if t.role else None,
                "completed_at": t.completed_at,
                "created_by": t.created_by,
                "assignee_ids": assignee_ids,
                "assignees": assignee_data,
                "overlap_warnings": [],
                "created_at": t.created_at,
                "updated_at": t.updated_at,
            })

        cols_data.append({
            "id": col.id,
            "project_id": col.project_id,
            "name": col.name,
            "position": col.position,
            "is_done": col.is_done,
            "tasks": tasks_data,
        })

    # Roles
    roles = db.query(ProjectRole).filter(
        ProjectRole.project_id == proj.id
    ).order_by(ProjectRole.position.asc()).all()
    roles_data = [
        {"id": r.id, "project_id": r.project_id, "name": r.name, "color": r.color, "position": r.position}
        for r in roles
    ]

    # Miembros completos
    all_members = db.query(ProjectMember).filter(
        ProjectMember.project_id == proj.id
    ).all()
    members_data = []
    for m in all_members:
        members_data.append({
            "id": m.id,
            "project_id": m.project_id,
            "user_id": m.user.id,
            "username": m.user.username,
            "email": m.user.email,
            "permission": m.permission,
            "role_id": m.role_id,
            "role_name": m.role.name if m.role else None,
            "role_color": m.role.color if m.role else None,
            "weekly_hours": m.weekly_hours,
            "joined_at": m.joined_at,
        })

    return {
        "id": proj.id,
        "name": proj.name,
        "description": proj.description,
        "color": proj.color,
        "icon": proj.icon,
        "is_archived": proj.is_archived,
        "owner_id": proj.owner_id,
        "my_permission": my_member.permission,
        "my_role": my_member.role.name if my_member.role else None,
        "total_tasks": total_tasks,
        "done_tasks": done_tasks,
        "progress_percent": progress,
        "members_count": len(all_members),
        "members": members_data[:5],
        "all_members": members_data,
        "columns": cols_data,
        "roles": roles_data,
        "created_at": proj.created_at,
        "updated_at": proj.updated_at,
    }


def update_project(db: Session, project_id: int, user_id: int, data: ProjectUpdate) -> Project:
    """Edita información del proyecto (requiere admin o owner)."""
    project, _ = require_permission(db, project_id, user_id, "admin")
    if data.name is not None:
        project.name = data.name.strip()
    if data.description is not None:
        project.description = data.description
    if data.color is not None:
        project.color = data.color
    if data.icon is not None:
        project.icon = data.icon
    if data.is_archived is not None:
        project.is_archived = data.is_archived

    db.commit()
    db.refresh(project)
    return project


def delete_project(db: Session, project_id: int, user_id: int) -> None:
    """Borrado lógico de proyecto (exclusivo para owner)."""
    project, _ = require_permission(db, project_id, user_id, "owner")
    project.is_active = False
    db.commit()


# --- MIEMBROS CRUD ---

def invite_member(db: Session, project_id: int, current_user_id: int, data: ProjectMemberInvite) -> ProjectMember:
    """Invita a un usuario registrado al proyecto (requiere admin u owner)."""
    require_permission(db, project_id, current_user_id, "admin")

    target_user = db.query(User).filter(User.email == data.email.lower().strip()).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe ningún usuario registrado con ese correo"
        )

    existing = get_member(db, project_id, target_user.id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario ya es miembro de este proyecto"
        )

    if data.role_id:
        role = db.query(ProjectRole).filter(
            ProjectRole.id == data.role_id,
            ProjectRole.project_id == project_id
        ).first()
        if not role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El rol especificado no pertenece a este proyecto"
            )

    new_member = ProjectMember(
        project_id=project_id,
        user_id=target_user.id,
        permission=data.permission,
        role_id=data.role_id,
        weekly_hours=data.weekly_hours
    )
    db.add(new_member)
    db.commit()
    db.refresh(new_member)
    return new_member


def update_member(db: Session, project_id: int, current_user_id: int, target_user_id: int, data: ProjectMemberUpdate) -> ProjectMember:
    """Modifica permisos, rol o capacidad de un miembro."""
    _, current_member = require_permission(db, project_id, current_user_id, "admin")
    target_member = get_member(db, project_id, target_user_id)
    if not target_member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Miembro no encontrado")

    # Si current_user es admin (no owner), no puede modificar a un owner ni a otro admin
    if current_member.permission == "admin" and target_member.permission in ("owner", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Los administradores no pueden modificar a los propietarios ni a otros administradores"
        )

    # Restricción: no se puede degradar al único owner
    if data.permission and data.permission != "owner" and target_member.permission == "owner":
        owners_count = db.query(func.count(ProjectMember.id)).filter(
            ProjectMember.project_id == project_id,
            ProjectMember.permission == "owner"
        ).scalar()
        if owners_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El proyecto debe tener al menos un propietario (owner)"
            )

    if data.permission is not None:
        target_member.permission = data.permission
    if data.role_id is not None:
        if data.role_id > 0:
            role = db.query(ProjectRole).filter(
                ProjectRole.id == data.role_id,
                ProjectRole.project_id == project_id
            ).first()
            if not role:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Rol inválido")
            target_member.role_id = data.role_id
        else:
            target_member.role_id = None
    if data.weekly_hours is not None:
        target_member.weekly_hours = data.weekly_hours

    db.commit()
    db.refresh(target_member)
    return target_member


def remove_member(db: Session, project_id: int, current_user_id: int, target_user_id: int) -> None:
    """Elimina o abandona el proyecto asegurando que quede al menos 1 owner."""
    _, current_member = require_member(db, project_id, current_user_id)
    target_member = get_member(db, project_id, target_user_id)
    if not target_member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Miembro no encontrado")

    is_self = (current_user_id == target_user_id)
    if not is_self:
        # Si no se elimina a sí mismo, debe ser admin u owner
        if current_member.permission not in ("owner", "admin"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permisos para expulsar miembros")
        if current_member.permission == "admin" and target_member.permission in ("owner", "admin"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No puedes expulsar a un propietario ni a un administrador")

    # Si el que se va o es expulsado es owner, verificar que no sea el único
    if target_member.permission == "owner":
        owners_count = db.query(func.count(ProjectMember.id)).filter(
            ProjectMember.project_id == project_id,
            ProjectMember.permission == "owner"
        ).scalar()
        if owners_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No puedes salir o eliminar al único propietario del proyecto"
            )

    db.delete(target_member)
    db.commit()


# --- ROLES CRUD ---

def create_role(db: Session, project_id: int, user_id: int, data: ProjectRoleCreate) -> ProjectRole:
    """Crea un rol de equipo para el proyecto."""
    require_permission(db, project_id, user_id, "admin")
    clean_name = data.name.strip()
    existing = db.query(ProjectRole).filter(
        ProjectRole.project_id == project_id,
        func.lower(ProjectRole.name) == clean_name.lower()
    ).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ya existe un rol con ese nombre")

    role = ProjectRole(
        project_id=project_id,
        name=clean_name,
        color=data.color or "#C9B49A",
        position=data.position or 0
    )
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


def update_role(db: Session, project_id: int, role_id: int, user_id: int, data: ProjectRoleUpdate) -> ProjectRole:
    """Actualiza nombre o color de un rol."""
    require_permission(db, project_id, user_id, "admin")
    role = db.query(ProjectRole).filter(
        ProjectRole.id == role_id,
        ProjectRole.project_id == project_id
    ).first()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rol no encontrado")

    if data.name is not None:
        clean_name = data.name.strip()
        dup = db.query(ProjectRole).filter(
            ProjectRole.project_id == project_id,
            ProjectRole.id != role_id,
            func.lower(ProjectRole.name) == clean_name.lower()
        ).first()
        if dup:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ya existe otro rol con ese nombre")
        role.name = clean_name
    if data.color is not None:
        role.color = data.color
    if data.position is not None:
        role.position = data.position

    db.commit()
    db.refresh(role)
    return role


def delete_role(db: Session, project_id: int, role_id: int, user_id: int) -> None:
    """Elimina un rol, desvinculándolo de miembros y tareas sin eliminarlos."""
    require_permission(db, project_id, user_id, "admin")
    role = db.query(ProjectRole).filter(
        ProjectRole.id == role_id,
        ProjectRole.project_id == project_id
    ).first()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rol no encontrado")

    # Desvincular miembros
    db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id,
        ProjectMember.role_id == role_id
    ).update({"role_id": None})

    # Desvincular tareas
    db.query(ProjectTask).filter(
        ProjectTask.project_id == project_id,
        ProjectTask.role_id == role_id
    ).update({"role_id": None})

    db.delete(role)
    db.commit()


# --- COLUMNAS CRUD ---

def create_column(db: Session, project_id: int, user_id: int, data: ProjectColumnCreate) -> ProjectColumn:
    """Crea una columna en el tablero."""
    require_permission(db, project_id, user_id, "admin")
    max_pos = db.query(func.max(ProjectColumn.position)).filter(
        ProjectColumn.project_id == project_id
    ).scalar() or 0

    col = ProjectColumn(
        project_id=project_id,
        name=data.name.strip(),
        position=data.position if data.position is not None else max_pos + 1,
        is_done=data.is_done or False
    )
    db.add(col)
    db.commit()
    db.refresh(col)
    return col


def update_column(db: Session, project_id: int, column_id: int, user_id: int, data: ProjectColumnUpdate) -> ProjectColumn:
    """Edita nombre, orden o estado is_done de la columna."""
    require_permission(db, project_id, user_id, "admin")
    col = db.query(ProjectColumn).filter(
        ProjectColumn.id == column_id,
        ProjectColumn.project_id == project_id
    ).first()
    if not col:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Columna no encontrada")

    if data.name is not None:
        col.name = data.name.strip()
    if data.position is not None:
        col.position = data.position
    if data.is_done is not None:
        col.is_done = data.is_done

    db.commit()
    db.refresh(col)
    return col


def delete_column(db: Session, project_id: int, column_id: int, user_id: int, target_column_id: Optional[int] = None) -> None:
    """Elimina una columna asegurando que quede al menos 1."""
    require_permission(db, project_id, user_id, "admin")
    total_cols = db.query(func.count(ProjectColumn.id)).filter(
        ProjectColumn.project_id == project_id
    ).scalar() or 0
    if total_cols <= 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El proyecto debe tener al menos una columna")

    col = db.query(ProjectColumn).filter(
        ProjectColumn.id == column_id,
        ProjectColumn.project_id == project_id
    ).first()
    if not col:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Columna no encontrada")

    # Mover tareas a target_column_id si hay tareas y target especificado
    if target_column_id and target_column_id != column_id:
        target_col = db.query(ProjectColumn).filter(
            ProjectColumn.id == target_column_id,
            ProjectColumn.project_id == project_id
        ).first()
        if target_col:
            db.query(ProjectTask).filter(
                ProjectTask.column_id == column_id
            ).update({"column_id": target_col.id})

    db.delete(col)
    db.commit()


def reorder_columns(db: Session, project_id: int, user_id: int, ordered_ids: List[int]) -> List[ProjectColumn]:
    """Reordena las columnas según la lista de IDs provista."""
    require_permission(db, project_id, user_id, "admin")
    cols = db.query(ProjectColumn).filter(
        ProjectColumn.project_id == project_id,
        ProjectColumn.id.in_(ordered_ids)
    ).all()
    col_map = {c.id: c for c in cols}

    for pos, col_id in enumerate(ordered_ids):
        if col_id in col_map:
            col_map[col_id].position = pos

    db.commit()
    return db.query(ProjectColumn).filter(
        ProjectColumn.project_id == project_id
    ).order_by(ProjectColumn.position.asc()).all()

