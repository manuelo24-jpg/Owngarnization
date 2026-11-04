from datetime import date
from fastapi.testclient import TestClient
from app.main import app

def _register_and_login(c: TestClient, email: str, username: str, password: str = "pass1234"):
    c.post("/auth/register", json={"email": email, "username": username, "password": password})
    c.post("/auth/login", json={"email": email, "password": password})
    return c.get("/auth/me").json()


def test_permission_matrix_and_role_access():
    c_owner = TestClient(app)
    c_admin = TestClient(app)
    c_member = TestClient(app)
    c_viewer = TestClient(app)

    u_owner = _register_and_login(c_owner, "perm_owner@example.com", "perm_owner")
    u_admin = _register_and_login(c_admin, "perm_admin@example.com", "perm_admin")
    u_member = _register_and_login(c_member, "perm_member@example.com", "perm_member")
    u_viewer = _register_and_login(c_viewer, "perm_viewer@example.com", "perm_viewer")

    # 1. Owner crea el proyecto
    proj = c_owner.post("/api/projects", json={"name": "Matriz Permisos"}).json()
    proj_id = proj["id"]
    col_id = c_owner.get(f"/api/projects/{proj_id}").json()["columns"][0]["id"]

    # 2. Owner invita a admin, member y viewer
    c_owner.post(f"/api/projects/{proj_id}/members", json={"email": u_admin["email"], "permission": "admin"})
    c_owner.post(f"/api/projects/{proj_id}/members", json={"email": u_member["email"], "permission": "member"})
    c_owner.post(f"/api/projects/{proj_id}/members", json={"email": u_viewer["email"], "permission": "viewer"})

    # 3. Viewer intenta crear tarea -> Debe fallar (403)
    viewer_task_res = c_viewer.post(f"/api/projects/{proj_id}/tasks", json={
        "column_id": col_id,
        "title": "Tarea intento viewer"
    })
    assert viewer_task_res.status_code == 403

    # 4. Member crea tarea -> Debe funcionar (201)
    member_task_res = c_member.post(f"/api/projects/{proj_id}/tasks", json={
        "column_id": col_id,
        "title": "Tarea de member"
    })
    assert member_task_res.status_code == 201
    task_id = member_task_res.json()["id"]

    # 5. Member intenta crear una columna o invitar a alguien -> Debe fallar (403)
    member_col_res = c_member.post(f"/api/projects/{proj_id}/columns", json={"name": "Col ilegal"})
    assert member_col_res.status_code == 403

    # 6. Admin crea rol -> Debe funcionar (201)
    admin_role_res = c_admin.post(f"/api/projects/{proj_id}/roles", json={"name": "Backend"})
    assert admin_role_res.status_code == 201

    # 7. Admin intenta borrar el proyecto -> Debe fallar (403, solo owner puede)
    admin_del_proj = c_admin.delete(f"/api/projects/{proj_id}")
    assert admin_del_proj.status_code == 403

    # 8. Admin intenta degradar o expulsar al owner -> Debe fallar (403)
    admin_kick_owner = c_admin.delete(f"/api/projects/{proj_id}/members/{u_owner['id']}")
    assert admin_kick_owner.status_code == 403


def test_at_least_one_owner_constraint():
    c = TestClient(app)
    u_owner = _register_and_login(c, "sole_owner@example.com", "sole_owner")

    proj = c.post("/api/projects", json={"name": "Solo Owner Proj"}).json()
    proj_id = proj["id"]

    # 1. Intentar degradar al único owner a member -> 400
    demote_res = c.patch(f"/api/projects/{proj_id}/members/{u_owner['id']}", json={
        "permission": "member"
    })
    assert demote_res.status_code == 400
    assert "al menos un propietario" in demote_res.json()["detail"].lower()

    # 2. Intentar que el único owner abandone el proyecto -> 400
    leave_res = c.delete(f"/api/projects/{proj_id}/members/{u_owner['id']}")
    assert leave_res.status_code == 400
    assert "único propietario" in leave_res.json()["detail"].lower()


def test_schedule_overlap_warning_and_workload():
    c_owner = TestClient(app)
    c_worker = TestClient(app)

    u_owner = _register_and_login(c_owner, "sched_owner@example.com", "sched_owner")
    u_worker = _register_and_login(c_worker, "sched_worker@example.com", "sched_worker")

    proj = c_owner.post("/api/projects", json={"name": "Schedule Proj"}).json()
    proj_id = proj["id"]
    col_id = c_owner.get(f"/api/projects/{proj_id}").json()["columns"][0]["id"]

    # Invitar a worker con 35 horas semanales
    c_owner.post(f"/api/projects/{proj_id}/members", json={
        "email": u_worker["email"],
        "permission": "member",
        "weekly_hours": 35
    })

    # Tarea 1: 10:00 a 12:00
    t1_res = c_owner.post(f"/api/projects/{proj_id}/tasks", json={
        "column_id": col_id,
        "title": "Reunión de arquitectura",
        "date": "2028-11-06",
        "start_time": "10:00:00",
        "end_time": "12:00:00",
        "assignee_ids": [u_worker["id"]]
    })
    assert t1_res.status_code == 201
    assert len(t1_res.json()["overlap_warnings"]) == 0

    # Tarea 2: 11:30 a 13:00 (solapa con Tarea 1 para worker)
    t2_res = c_owner.post(f"/api/projects/{proj_id}/tasks", json={
        "column_id": col_id,
        "title": "Code Review urgente",
        "date": "2028-11-06",
        "start_time": "11:30:00",
        "end_time": "13:00:00",
        "assignee_ids": [u_worker["id"]]
    })
    assert t2_res.status_code == 201
    t2_data = t2_res.json()
    assert len(t2_data["overlap_warnings"]) == 1
    assert t2_data["overlap_warnings"][0]["user_id"] == u_worker["id"]
    assert "Reunión de arquitectura" in t2_data["overlap_warnings"][0]["conflicting_title"]

    # Consultar /api/projects/{id}/schedule
    sched_res = c_owner.get(f"/api/projects/{proj_id}/schedule?start=2028-11-06&end=2028-11-06&by=person")
    assert sched_res.status_code == 200
    sched_data = sched_res.json()
    assert len(sched_data["tasks"]) == 2
    assert str(u_worker["id"]) in sched_data["by_person"]

    # Consultar /api/projects/{id}/workload
    workload_res = c_owner.get(f"/api/projects/{proj_id}/workload?week=2028-11-06")
    assert workload_res.status_code == 200
    workload_data = workload_res.json()
    worker_stat = next(m for m in workload_data["members"] if m["user_id"] == u_worker["id"])
    assert worker_stat["weekly_hours"] == 35
    # 2.0 h (t1) + 1.5 h (t2) = 3.5 h
    assert worker_stat["planned_hours"] == 3.5
    assert worker_stat["task_count"] == 2

