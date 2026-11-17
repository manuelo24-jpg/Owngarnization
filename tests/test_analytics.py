import datetime as dt
from fastapi.testclient import TestClient
from app.main import app


def create_authenticated_client(email: str, username: str) -> TestClient:
    c = TestClient(app)
    c.post("/auth/register", json={
        "email": email,
        "username": username,
        "password": "Password123!"
    })
    return c


def test_daily_summary_empty_and_calculations():
    client = create_authenticated_client("daily_test@example.com", "dailyuser")
    test_date = "2026-11-15"

    # 1. Sin tareas en la fecha
    resp_empty = client.get(f"/api/reports/daily?date={test_date}")
    assert resp_empty.status_code == 200
    data_empty = resp_empty.json()
    assert data_empty["total_tasks"] == 0
    assert data_empty["completed_tasks"] == 0
    assert data_empty["completion_rate"] == 0
    assert "No hay tareas programadas" in data_empty["motivational_message"]

    # 2. Crear 2 tareas del día (1 urgente con horas, 1 normal sin horas)
    t1 = client.post("/api/tasks", json={
        "title": "Informe urgente",
        "kind": "daily",
        "importance": "urgent",
        "date": test_date,
        "start_time": "09:00:00",
        "end_time": "10:30:00",
        "initial_status": "not_started"
    }).json()

    t2 = client.post("/api/tasks", json={
        "title": "Revisar correo",
        "kind": "daily",
        "importance": "low",
        "date": test_date,
        "initial_status": "not_started"
    }).json()

    # Comprobar resumen con tareas sin empezar
    resp_before = client.get(f"/api/reports/daily?date={test_date}")
    assert resp_before.status_code == 200
    data_before = resp_before.json()
    assert data_before["total_tasks"] == 2
    assert data_before["completed_tasks"] == 0
    assert data_before["completion_rate"] == 0
    assert data_before["estimated_minutes_total"] == 90  # 1h 30m
    assert data_before["estimated_minutes_completed"] == 0
    assert data_before["by_importance"]["urgent"]["total"] == 1
    assert data_before["by_importance"]["low"]["total"] == 1

    # Obtener ocurrencia de t1 y marcarla como 'done'
    occs = client.get(f"/api/occurrences?start={test_date}&end={test_date}").json()
    occ_t1 = next(o for o in occs if o["task_id"] == t1["id"])

    patch_resp = client.patch(f"/api/occurrences/{occ_t1['id']}", json={"status": "done"})
    assert patch_resp.status_code == 200

    # Comprobar resumen tras completar 1 de 2
    resp_half = client.get(f"/api/reports/daily?date={test_date}")
    data_half = resp_half.json()
    assert data_half["total_tasks"] == 2
    assert data_half["completed_tasks"] == 1
    assert data_half["completion_rate"] == 50
    assert data_half["estimated_minutes_completed"] == 90
    assert data_half["by_importance"]["urgent"]["completed"] == 1
    assert data_half["by_importance"]["low"]["completed"] == 0
    assert "mitad" in data_half["motivational_message"].lower()

    # Marcar t2 como done -> 100%
    occ_t2 = next(o for o in occs if o["task_id"] == t2["id"])
    client.patch(f"/api/occurrences/{occ_t2['id']}", json={"status": "done"})

    resp_full = client.get(f"/api/reports/daily?date={test_date}")
    data_full = resp_full.json()
    assert data_full["completion_rate"] == 100
    assert "impecable" in data_full["motivational_message"].lower()


def test_carry_over_uncompleted_daily_tasks():
    client = create_authenticated_client("carry_test@example.com", "carryuser")
    today = dt.date.today()
    source_date = str(today)
    target_date = str(today + dt.timedelta(days=1))

    # Crear 1 tarea que quedará sin hacer y 1 tarea que sí se completa
    t_uncompleted = client.post("/api/tasks", json={
        "title": "Tarea pendiente de hoy",
        "kind": "daily",
        "date": source_date,
        "initial_status": "not_started"
    }).json()

    t_completed = client.post("/api/tasks", json={
        "title": "Tarea terminada hoy",
        "kind": "daily",
        "date": source_date,
        "initial_status": "not_started"
    }).json()

    occs = client.get(f"/api/occurrences?start={source_date}&end={source_date}").json()
    occ_done = next(o for o in occs if o["task_id"] == t_completed["id"])
    client.patch(f"/api/occurrences/{occ_done['id']}", json={"status": "done"})

    # Ejecutar carry-over de source_date a target_date
    carry_resp = client.post(f"/api/reports/daily/carry-over?date={source_date}&target_date={target_date}")
    assert carry_resp.status_code == 200
    carry_data = carry_resp.json()
    assert carry_data["moved_count"] == 1
    assert carry_data["source_date"] == source_date
    assert carry_data["target_date"] == target_date

    # Verificar que en source_date ahora solo queda la completada
    occs_source = client.get(f"/api/occurrences?start={source_date}&end={source_date}").json()
    assert len(occs_source) == 1
    assert occs_source[0]["task_id"] == t_completed["id"]

    # Verificar que en target_date está la tarea que quedó pendiente
    occs_target = client.get(f"/api/occurrences?start={target_date}&end={target_date}").json()
    assert len(occs_target) == 1
    assert occs_target[0]["task_id"] == t_uncompleted["id"]


def test_weekly_summary_and_streak():
    client = create_authenticated_client("weekly_test@example.com", "weeklyuser")
    # Lunes 2026-11-16 a Domingo 2026-11-22
    ref_date = "2026-11-18"  # Miércoles

    # Crear tareas en varios días de la semana
    t_mon = client.post("/api/tasks", json={
        "title": "Tarea Lunes",
        "kind": "daily",
        "date": "2026-11-16",
        "initial_status": "done"
    }).json()

    t_tue = client.post("/api/tasks", json={
        "title": "Tarea Martes",
        "kind": "daily",
        "date": "2026-11-17",
        "initial_status": "done"
    }).json()

    t_wed = client.post("/api/tasks", json={
        "title": "Tarea Miércoles",
        "kind": "daily",
        "date": "2026-11-18",
        "initial_status": "not_started"
    }).json()

    # Pedir informe semanal
    resp = client.get(f"/api/reports/weekly?week={ref_date}")
    assert resp.status_code == 200
    data = resp.json()

    assert data["week_start"] == "2026-11-16"
    assert data["week_end"] == "2026-11-22"
    assert len(data["days"]) == 7
    assert data["total_tasks"] >= 3
    assert data["completed_tasks"] == 2
    # Lunes y Martes tienen 100% de completado
    mon_summary = next(d for d in data["days"] if d["date"] == "2026-11-16")
    assert mon_summary["day_name"] == "Lun"
    assert mon_summary["completed_tasks"] == 1


def test_completed_history_and_isolation():
    client_a = create_authenticated_client("hist_a@example.com", "hista")
    client_b = create_authenticated_client("hist_b@example.com", "histb")

    # Usuario A crea 3 tareas: 2 completadas y 1 pendiente
    t1 = client_a.post("/api/tasks", json={
        "title": "Aprender FastAPI",
        "description": "Estudiar routers y dependencias",
        "kind": "daily",
        "date": "2026-11-01",
        "initial_status": "done"
    }).json()

    t2 = client_a.post("/api/tasks", json={
        "title": "Hacer ejercicio matutino",
        "description": "Rutina de cardio y pesas",
        "kind": "daily",
        "date": "2026-11-02",
        "initial_status": "done"
    }).json()

    t3 = client_a.post("/api/tasks", json={
        "title": "Comprar provisiones",
        "kind": "daily",
        "date": "2026-11-03",
        "initial_status": "not_started"
    }).json()

    # Usuario B crea 1 tarea completada (privada)
    client_b.post("/api/tasks", json={
        "title": "Tarea secreta de B",
        "kind": "daily",
        "date": "2026-11-01",
        "initial_status": "done"
    })

    # 1. Historial de A: deben salir exactamente las 2 completadas de A
    hist_resp = client_a.get("/api/history")
    assert hist_resp.status_code == 200
    hist_data = hist_resp.json()
    assert hist_data["total"] == 2
    titles = [item["title"] for item in hist_data["items"]]
    assert "Aprender FastAPI" in titles
    assert "Hacer ejercicio matutino" in titles
    assert "Comprar provisiones" not in titles
    assert "Tarea secreta de B" not in titles

    # 2. Búsqueda por texto en historial de A
    search_resp = client_a.get("/api/history?q=cardio")
    assert search_resp.status_code == 200
    search_data = search_resp.json()
    assert search_data["total"] == 1
    assert search_data["items"][0]["title"] == "Hacer ejercicio matutino"

    # 3. Paginación en historial
    paged_resp = client_a.get("/api/history?limit=1&offset=0")
    assert paged_resp.status_code == 200
    paged_data = paged_resp.json()
    assert paged_data["total"] == 2
    assert len(paged_data["items"]) == 1
    assert paged_data["limit"] == 1
    assert paged_data["offset"] == 0

    # 4. Historial de B: solo 1 tarea, sin ver datos de A
    hist_b = client_b.get("/api/history").json()
    assert hist_b["total"] == 1
    assert hist_b["items"][0]["title"] == "Tarea secreta de B"


def test_analytics_html_integration():
    client = create_authenticated_client("html_test@example.com", "htmluser")

    # Página web principal /
    web_resp = client.get("/")
    assert web_resp.status_code == 200
    assert "btn-analytics" in web_resp.text
    assert "analytics-modal" in web_resp.text
    assert "analytics.js" in web_resp.text

    # Página móvil /m
    m_resp = client.get("/m")
    assert m_resp.status_code == 200
    assert "btn-analytics" in m_resp.text
    assert "analytics-modal" in m_resp.text
    assert "analytics.js" in m_resp.text

