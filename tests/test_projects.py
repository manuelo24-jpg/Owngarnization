from datetime import date, time
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def _register_and_login(c: TestClient, email: str, username: str, password: str = "pass1234"):
    c.post("/auth/register", json={"email": email, "username": username, "password": password})
    c.post("/auth/login", json={"email": email, "password": password})


def test_project_creation_defaults():
    c = TestClient(app)
    _register_and_login(c, "owner@example.com", "owneruser")

    # Crear proyecto
    payload = {
        "name": "Mi Primer Proyecto",
        "description": "Descripción de prueba",
        "color": "#C9B49A",
        "icon": "🚀"
    }
    resp = c.post("/api/projects", json=payload)
    assert resp.status_code == 201
    data = resp.json()

    assert data["name"] == "Mi Primer Proyecto"
    assert data["my_permission"] == "owner"
    assert data["my_role"] == "General"
    assert data["total_tasks"] == 0
    assert data["done_tasks"] == 0
    assert data["progress_percent"] == 0

    # Obtener detalle
    detail_resp = c.get(f"/api/projects/{data['id']}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()

    # Verificar 4 columnas por defecto
    col_names = [col["name"] for col in detail["columns"]]
    assert col_names == ["Pendiente", "En curso", "En revisión", "Hecho"]
    assert detail["columns"][3]["is_done"] is True

    # Verificar rol por defecto
    assert len(detail["roles"]) == 1
    assert detail["roles"][0]["name"] == "General"

    # Verificar miembro owner
    assert len(detail["all_members"]) == 1
    assert detail["all_members"][0]["permission"] == "owner"


def test_user_and_project_isolation():
    c1 = TestClient(app)
    c2 = TestClient(app)

    _register_and_login(c1, "user1@example.com", "user1")
    _register_and_login(c2, "user2@example.com", "user2")

    # user1 crea un proyecto
    res = c1.post("/api/projects", json={"name": "Privado User 1"})
    assert res.status_code == 201
    proj_id = res.json()["id"]

    # user2 NO debe ver el proyecto en su lista
    res_list = c2.get("/api/projects")
    assert res_list.status_code == 200
    assert all(p["id"] != proj_id for p in res_list.json())

    # user2 NO puede acceder al detalle (403 o 404)
    res_detail = c2.get(f"/api/projects/{proj_id}")
    assert res_detail.status_code in (403, 404)

    # user2 NO puede modificar el proyecto
    res_update = c2.patch(f"/api/projects/{proj_id}", json={"name": "Hackeado"})
    assert res_update.status_code in (403, 404)


def test_spaces_summary_and_preferences():
    c = TestClient(app)
    _register_and_login(c, "spaceuser@example.com", "spaceuser")

    # 1. Crear tarea personal para hoy
    c.post("/api/tasks", json={
        "title": "Rutina personal",
        "kind": "common",
        "importance": "high"
    })

    # 2. Crear proyecto
    proj = c.post("/api/projects", json={"name": "Proyecto Espacios"}).json()
    proj_id = proj["id"]

    # 3. Consultar /api/spaces/summary
    summary_res = c.get("/api/spaces/summary")
    assert summary_res.status_code == 200
    summary = summary_res.json()
    assert summary["personal"]["today_total"] >= 1
    assert summary["projects"]["active_projects"] == 1
    assert summary["projects"]["assigned_tasks"] == 0

    # 4. Actualizar preferencia de espacio
    patch_res = c.patch("/api/me/space", json={
        "last_space": "projects",
        "last_project_id": proj_id
    })
    assert patch_res.status_code == 200
    assert patch_res.json()["last_space"] == "projects"
    assert patch_res.json()["last_project_id"] == proj_id


def test_task_lifecycle_move_and_done():
    c = TestClient(app)
    _register_and_login(c, "taskflow@example.com", "taskflow")

    proj = c.post("/api/projects", json={"name": "Kanban Test"}).json()
    proj_id = proj["id"]
    detail = c.get(f"/api/projects/{proj_id}").json()

    col_todo = detail["columns"][0]["id"]
    col_done = detail["columns"][3]["id"]

    # Crear tarea en Pendiente
    t_res = c.post(f"/api/projects/{proj_id}/tasks", json={
        "column_id": col_todo,
        "title": "Implementar módulo",
        "priority": "high"
    })
    assert t_res.status_code == 201
    task = t_res.json()
    assert task["completed_at"] is None

    # Mover tarea a 'Hecho'
    move_res = c.post(f"/api/projects/{proj_id}/tasks/move", json={
        "task_id": task["id"],
        "column_id": col_done,
        "position": 0
    })
    assert move_res.status_code == 200
    moved_task = move_res.json()
    assert moved_task["column_id"] == col_done
    assert moved_task["completed_at"] is not None

    # Verificar que el progreso del proyecto ahora sea 100%
    updated_proj = c.get(f"/api/projects/{proj_id}").json()
    assert updated_proj["progress_percent"] == 100

    # Mover de vuelta a Pendiente: completed_at vuelve a None
    move_back = c.post(f"/api/projects/{proj_id}/tasks/move", json={
        "task_id": task["id"],
        "column_id": col_todo,
        "position": 0
    })
    assert move_back.status_code == 200
    assert move_back.json()["completed_at"] is None


def test_task_member_assignment_restriction():
    c1 = TestClient(app)
    c2 = TestClient(app)

    _register_and_login(c1, "owner_assign@example.com", "owner_assign")
    _register_and_login(c2, "outsider@example.com", "outsider")
    outsider_id = c2.get("/auth/me").json()["id"]

    proj = c1.post("/api/projects", json={"name": "Assign Test"}).json()
    proj_id = proj["id"]
    col_id = c1.get(f"/api/projects/{proj_id}").json()["columns"][0]["id"]

    # Intentar asignar tarea a un usuario que NO es miembro del proyecto
    bad_assign = c1.post(f"/api/projects/{proj_id}/tasks", json={
        "column_id": col_id,
        "title": "Tarea ajena",
        "assignee_ids": [outsider_id]
    })
    assert bad_assign.status_code == 400
    assert "miembros" in bad_assign.json()["detail"].lower()


def test_column_and_role_management():
    c = TestClient(app)
    _register_and_login(c, "manager@example.com", "manager")

    proj = c.post("/api/projects", json={"name": "Cols and Roles"}).json()
    proj_id = proj["id"]

    # Crear rol nuevo
    role_res = c.post(f"/api/projects/{proj_id}/roles", json={
        "name": "Frontend",
        "color": "#E3CFB4"
    })
    assert role_res.status_code == 201
    role_id = role_res.json()["id"]

    # Crear columna nueva
    col_res = c.post(f"/api/projects/{proj_id}/columns", json={
        "name": "QA / Pruebas",
        "position": 4,
        "is_done": False
    })
    assert col_res.status_code == 201
    new_col_id = col_res.json()["id"]

    # Reordenar columnas
    cols = c.get(f"/api/projects/{proj_id}").json()["columns"]
    reordered_ids = [new_col_id] + [col["id"] for col in cols if col["id"] != new_col_id]
    reorder_res = c.post(f"/api/projects/{proj_id}/columns/reorder", json={
        "column_ids": reordered_ids
    })
    assert reorder_res.status_code == 200
    assert reorder_res.json()[0]["id"] == new_col_id

    # Eliminar columna
    del_col = c.delete(f"/api/projects/{proj_id}/columns/{new_col_id}")
    assert del_col.status_code == 204

    # Eliminar rol
    del_role = c.delete(f"/api/projects/{proj_id}/roles/{role_id}")
    assert del_role.status_code == 204


def test_personal_and_project_data_separation():
    c = TestClient(app)
    _register_and_login(c, "separate@example.com", "separate")

    # 1. Crear tarea personal
    c.post("/api/tasks", json={
        "title": "Comprar leche (personal)",
        "kind": "daily",
        "date": "2028-11-01"
    })

    # 2. Crear proyecto con tarea
    proj = c.post("/api/projects", json={"name": "Separation Proj"}).json()
    proj_id = proj["id"]
    col_id = c.get(f"/api/projects/{proj_id}").json()["columns"][0]["id"]

    c.post(f"/api/projects/{proj_id}/tasks", json={
        "column_id": col_id,
        "title": "Desplegar backend (proyecto)"
    })

    # 3. Comprobar que en /api/occurrences no aparece la tarea del proyecto
    occs = c.get("/api/occurrences?start=2028-11-01&end=2028-11-01").json()
    titles = [o["task"]["title"] for o in occs]
    assert "Comprar leche (personal)" in titles
    assert "Desplegar backend (proyecto)" not in titles

    # 4. Comprobar que en el proyecto no aparece la tarea personal
    proj_detail = c.get(f"/api/projects/{proj_id}").json()
    proj_task_titles = [t["title"] for col in proj_detail["columns"] for t in col["tasks"]]
    assert "Desplegar backend (proyecto)" in proj_task_titles
    assert "Comprar leche (personal)" not in proj_task_titles



def test_project_html_pages_flow():
    c_anon = TestClient(app)

    # 1. Anónimo redirige a /login
    for path in ["/spaces", "/projects", "/projects/1", "/m/spaces", "/m/projects", "/m/projects/1"]:
        r = c_anon.get(path, follow_redirects=False)
        assert r.status_code == 302
        assert r.headers["location"] == "/login"

    c_auth = TestClient(app)
    _register_and_login(c_auth, "pages_user@example.com", "pages_user")

    # 2. Usuario autenticado ve /spaces
    spaces_resp = c_auth.get("/spaces")
    assert spaces_resp.status_code == 200
    assert "Organización personal" in spaces_resp.text
    assert "Proyectos" in spaces_resp.text

    # 3. Usuario autenticado ve /projects
    proj_resp = c_auth.get("/projects")
    assert proj_resp.status_code == 200
    assert "Tus proyectos" in proj_resp.text
    assert "projects-guide-modal" in proj_resp.text

    # 4. Crear proyecto y acceder a su pantalla interior /projects/{id}
    new_proj = c_auth.post("/api/projects", json={"name": "Pantalla Proyecto"}).json()
    p_id = new_proj["id"]

    interior_resp = c_auth.get(f"/projects/{p_id}")
    assert interior_resp.status_code == 200
    assert "Pantalla Proyecto" in interior_resp.text
    assert "Tablero" in interior_resp.text
    assert "Horario" in interior_resp.text
    assert "Personas" in interior_resp.text
    assert "Manual de Proyectos y Equipos" in interior_resp.text

    # 5. Usuario ajeno recibe 404 al intentar entrar a ese proyecto
    c_stranger = TestClient(app)
    _register_and_login(c_stranger, "stranger@example.com", "stranger")
    stranger_resp = c_stranger.get(f"/projects/{p_id}")
    assert stranger_resp.status_code == 404

    # 6. Versión móvil dedicada /m/projects y /m/projects/{id} con navegación inferior y FAB
    m_proj_resp = c_auth.get("/m/projects")
    assert m_proj_resp.status_code == 200
    assert "Tus proyectos" in m_proj_resp.text

    m_interior_resp = c_auth.get(f"/m/projects/{p_id}")
    assert m_interior_resp.status_code == 200
    assert "project-mobile-bottom-nav" in m_interior_resp.text
    assert "btn-project-mobile-fab" in m_interior_resp.text
    assert "mobile-tab-board" in m_interior_resp.text
