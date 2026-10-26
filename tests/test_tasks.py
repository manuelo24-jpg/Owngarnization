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


def test_time_validation():
    client = create_authenticated_client("timeuser@example.com", "timeuser")

    # Hora fin anterior a hora inicio -> debe fallar con 422
    bad_resp = client.post("/api/tasks", json={
        "title": "Reunión inválida",
        "kind": "daily",
        "date": "2026-11-01",
        "start_time": "15:00:00",
        "end_time": "14:00:00"
    })
    assert bad_resp.status_code == 422

    # Horario coherente -> 201
    good_resp = client.post("/api/tasks", json={
        "title": "Reunión válida",
        "kind": "daily",
        "date": "2026-11-01",
        "start_time": "10:00:00",
        "end_time": "11:30:00"
    })
    assert good_resp.status_code == 201
    assert good_resp.json()["start_time"] == "10:00:00"
    assert good_resp.json()["end_time"] == "11:30:00"

    # Sin horario -> 201
    no_time_resp = client.post("/api/tasks", json={
        "title": "Tarea sin hora",
        "kind": "daily",
        "date": "2026-11-01"
    })
    assert no_time_resp.status_code == 201
    assert no_time_resp.json()["start_time"] is None


def test_user_isolation():
    client_a = create_authenticated_client("user_a@example.com", "userA")
    client_b = create_authenticated_client("user_b@example.com", "userB")

    # Usuario A crea una tarea
    resp_a = client_a.post("/api/tasks", json={
        "title": "Tarea privada de A",
        "kind": "daily",
        "date": "2026-11-01"
    })
    assert resp_a.status_code == 201
    task_a_id = resp_a.json()["id"]

    # Usuario B intenta ver la ocurrencia de esa fecha
    occs_b = client_b.get("/api/occurrences?start=2026-11-01&end=2026-11-01").json()
    assert len(occs_b) == 0

    # Usuario B intenta acceder directamente por ID a la tarea de A -> 404
    detail_b = client_b.get(f"/api/tasks/{task_a_id}")
    assert detail_b.status_code == 404

    # Usuario B intenta editar la tarea de A -> 404
    edit_b = client_b.patch(f"/api/tasks/{task_a_id}", json={"title": "Hackeado"})
    assert edit_b.status_code == 404

    # Usuario B intenta borrar la tarea de A -> 404
    del_b = client_b.delete(f"/api/tasks/{task_a_id}")
    assert del_b.status_code == 404


def test_common_tasks_appear_every_day():
    client = create_authenticated_client("rutinas@example.com", "rutinas")

    # Crear una tarea común (rutina diaria)
    resp = client.post("/api/tasks", json={
        "title": "Beber 2L de agua",
        "kind": "common",
        "importance": "high"
    })
    assert resp.status_code == 201

    # Consultar rango de 5 días
    occs_resp = client.get("/api/occurrences?start=2026-11-01&end=2026-11-05")
    assert occs_resp.status_code == 200
    occs = occs_resp.json()

    assert len(occs) == 5
    fechas = [o["date"] for o in occs]
    assert fechas == [
        "2026-11-01",
        "2026-11-02",
        "2026-11-03",
        "2026-11-04",
        "2026-11-05"
    ]
    for o in occs:
        assert o["task"]["title"] == "Beber 2L de agua"
        assert o["status"] == "not_started"


def test_independent_status_per_day_for_common_task():
    client = create_authenticated_client("indep@example.com", "indep")

    client.post("/api/tasks", json={
        "title": "Hacer ejercicio",
        "kind": "common"
    })

    # Consultar 2 días consecutivos
    occs = client.get("/api/occurrences?start=2026-11-01&end=2026-11-02").json()
    assert len(occs) == 2
    occ_day1 = occs[0]
    occ_day2 = occs[1]

    # Marcar como 'done' el día 1
    patch_resp = client.patch(f"/api/occurrences/{occ_day1['id']}", json={"status": "done"})
    assert patch_resp.status_code == 200
    assert patch_resp.json()["status"] == "done"

    # Verificar que el día 2 sigue 'not_started'
    refreshed_occs = client.get("/api/occurrences?start=2026-11-01&end=2026-11-02").json()
    assert refreshed_occs[0]["status"] == "done"
    assert refreshed_occs[1]["status"] == "not_started"


def test_daily_task_only_on_its_date():
    client = create_authenticated_client("dailyuser@example.com", "dailyuser")

    client.post("/api/tasks", json={
        "title": "Dentista",
        "kind": "daily",
        "date": "2026-11-15"
    })

    # No debe aparecer entre el 1 y el 10
    early = client.get("/api/occurrences?start=2026-11-01&end=2026-11-10").json()
    assert len(early) == 0

    # Debe aparecer entre el 11 y el 20
    exact = client.get("/api/occurrences?start=2026-11-11&end=2026-11-20").json()
    assert len(exact) == 1
    assert exact[0]["date"] == "2026-11-15"
    assert exact[0]["task"]["title"] == "Dentista"


def test_search_and_filters():
    client = create_authenticated_client("searchuser@example.com", "searchuser")

    client.post("/api/tasks", json={
        "title": "Preparar informe trimestral",
        "description": "Incluir balance de ventas",
        "kind": "daily",
        "importance": "high",
        "date": "2026-11-01"
    })
    client.post("/api/tasks", json={
        "title": "Comprar café",
        "description": "Tueste natural",
        "kind": "daily",
        "importance": "low",
        "date": "2026-11-01"
    })

    # Búsqueda por texto "informe"
    q_resp = client.get("/api/occurrences?start=2026-11-01&end=2026-11-01&q=informe").json()
    assert len(q_resp) == 1
    assert q_resp[0]["task"]["title"] == "Preparar informe trimestral"

    # Búsqueda por texto en descripción "ventas"
    q_desc = client.get("/api/occurrences?start=2026-11-01&end=2026-11-01&q=ventas").json()
    assert len(q_desc) == 1

    # Filtro por importancia "low"
    imp_resp = client.get("/api/occurrences?start=2026-11-01&end=2026-11-01&importance=low").json()
    assert len(imp_resp) == 1
    assert imp_resp[0]["task"]["title"] == "Comprar café"


def test_reorder_occurrences():
    client = create_authenticated_client("reorderuser@example.com", "reorderuser")

    t1 = client.post("/api/tasks", json={"title": "Tarea 1", "kind": "daily", "date": "2026-11-01"}).json()
    t2 = client.post("/api/tasks", json={"title": "Tarea 2", "kind": "daily", "date": "2026-11-01"}).json()

    occs = client.get("/api/occurrences?start=2026-11-01&end=2026-11-01").json()
    id1 = occs[0]["id"]
    id2 = occs[1]["id"]

    # Reordenar invirtiendo las posiciones
    reorder_resp = client.post("/api/occurrences/reorder", json={
        "date": "2026-11-01",
        "ordered_ids": [id2, id1]
    })
    assert reorder_resp.status_code == 200

    new_occs = client.get("/api/occurrences?start=2026-11-01&end=2026-11-01").json()
    assert new_occs[0]["id"] == id2
    assert new_occs[1]["id"] == id1


def test_move_occurrence_date():
    client = create_authenticated_client("moveuser@example.com", "moveuser")

    client.post("/api/tasks", json={
        "title": "Mover reunión",
        "kind": "daily",
        "date": "2026-11-01"
    })

    occs = client.get("/api/occurrences?start=2026-11-01&end=2026-11-01").json()
    occ_id = occs[0]["id"]

    # Mover al 2026-11-03
    patch_resp = client.patch(f"/api/occurrences/{occ_id}", json={"date": "2026-11-03"})
    assert patch_resp.status_code == 200
    assert patch_resp.json()["date"] == "2026-11-03"

    # Verificar que ya no está en el día 1
    day1_occs = client.get("/api/occurrences?start=2026-11-01&end=2026-11-01").json()
    assert len(day1_occs) == 0

    # Y que ahora está en el día 3
    day3_occs = client.get("/api/occurrences?start=2026-11-03&end=2026-11-03").json()
    assert len(day3_occs) == 1
    assert day3_occs[0]["date"] == "2026-11-03"


def test_daily_task_rollover_when_uncompleted():
    import datetime as dt
    client = create_authenticated_client("rollover@example.com", "rollover")

    today = dt.date.today()
    past_date = today - dt.timedelta(days=2)
    past_date_str = past_date.isoformat()
    today_str = today.isoformat()

    # 1. Tarea del pasado que NO se completó (not_started)
    t_pending = client.post("/api/tasks", json={
        "title": "Comprar pan ayer",
        "kind": "daily",
        "date": past_date_str
    }).json()

    # 2. Tarea del pasado que SÍ se completó (done)
    t_done = client.post("/api/tasks", json={
        "title": "Pagar factura",
        "kind": "daily",
        "date": past_date_str,
        "initial_status": "done"
    }).json()

    # 3. Consultar hoy
    today_occs = client.get(f"/api/occurrences?start={today_str}&end={today_str}").json()


    # La tarea pendiente debe haber hecho rollover a HOY
    today_titles = [o["task"]["title"] for o in today_occs]
    assert "Comprar pan ayer" in today_titles

    # La tarea completada debe permanecer en su fecha pasada
    assert "Pagar factura" not in today_titles

    # Comprobar que en la fecha pasada la completada sigue allí
    recheck_past = client.get(f"/api/occurrences?start={past_date_str}&end={past_date_str}").json()
    past_titles = [o["task"]["title"] for o in recheck_past]
    assert "Pagar factura" in past_titles


def test_common_task_with_specific_days_of_week():
    client = create_authenticated_client("daysuser@example.com", "daysuser")

    # Tarea común solo para Lunes (1), Miércoles (3) y Viernes (5)
    resp = client.post("/api/tasks", json={
        "title": "Ir al gimnasio",
        "kind": "common",
        "days_of_week": "1,3,5"
    })
    assert resp.status_code == 201

    # Rango de una semana completa: Lunes 2026-11-02 a Domingo 2026-11-08
    # 2026-11-02 es Lunes (1)
    # 2026-11-03 es Martes (2)
    # 2026-11-04 es Miércoles (3)
    # 2026-11-05 es Jueves (4)
    # 2026-11-06 es Viernes (5)
    # 2026-11-07 es Sábado (6)
    # 2026-11-08 es Domingo (7)
    occs = client.get("/api/occurrences?start=2026-11-02&end=2026-11-08").json()

    # Solo debe aparecer 3 veces (Lunes, Miércoles, Viernes)
    assert len(occs) == 3
    fechas = [o["date"] for o in occs]
    assert fechas == ["2026-11-02", "2026-11-04", "2026-11-06"]

