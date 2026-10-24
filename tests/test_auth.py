from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)



def test_register_success():
    payload = {
        "email": "test@example.com",
        "username": "tester",
        "password": "securepassword123"
    }
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["username"] == "tester"
    assert "password_hash" not in data


def test_register_duplicate_email():
    payload = {
        "email": "duplicate@example.com",
        "username": "user1",
        "password": "password123"
    }
    res1 = client.post("/auth/register", json=payload)
    assert res1.status_code == 201

    res2 = client.post("/auth/register", json=payload)
    assert res2.status_code == 400
    assert "ya está registrado" in res2.json()["detail"]


def test_login_and_logout_flow():
    # 1. Registrar usuario
    reg_payload = {
        "email": "loginuser@example.com",
        "username": "loginuser",
        "password": "mypassword123"
    }
    client.post("/auth/register", json=reg_payload)

    # 2. Login con contraseña errónea
    bad_login = client.post("/auth/login", json={
        "email": "loginuser@example.com",
        "password": "wrongpassword"
    })
    assert bad_login.status_code == 401

    # 3. Login con contraseña correcta
    good_login = client.post("/auth/login", json={
        "email": "loginuser@example.com",
        "password": "mypassword123"
    })
    assert good_login.status_code == 200
    assert good_login.json()["user"]["email"] == "loginuser@example.com"

    # 4. Probar ruta protegida /auth/me con cookies del cliente
    me_resp = client.get("/auth/me")
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "loginuser@example.com"

    # 5. Logout
    logout_resp = client.post("/auth/logout")
    assert logout_resp.status_code == 200

    # 6. /auth/me tras logout debe retornar 401
    me_after_logout = client.get("/auth/me")
    assert me_after_logout.status_code == 401


def test_unauthenticated_access_denied():
    # Cliente nuevo sin cookies
    fresh_client = TestClient(app)
    response = fresh_client.get("/auth/me")
    assert response.status_code == 401


def test_page_redirects_for_anonymous_and_authenticated():
    anon_client = TestClient(app)
    
    # Usuario anónimo visitando / es redirigido a /login
    resp = anon_client.get("/", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"] == "/login"

    # Usuario anónimo puede ver la página /login
    login_page_resp = anon_client.get("/login")
    assert login_page_resp.status_code == 200
    assert "Iniciar sesión" in login_page_resp.text

    # Registrar usuario y comprobar acceso a /
    reg_payload = {
        "email": "pageuser@example.com",
        "username": "pageuser",
        "password": "password123"
    }
    anon_client.post("/auth/register", json=reg_payload)

    # Ahora con sesión iniciada, / debe responder 200
    home_resp = anon_client.get("/")
    assert home_resp.status_code == 200
    assert "pageuser" in home_resp.text

    # Y al visitar /login o /register con sesión activa, redirige a /
    redir_login = anon_client.get("/login", follow_redirects=False)
    assert redir_login.status_code == 302
    assert redir_login.headers["location"] == "/"

