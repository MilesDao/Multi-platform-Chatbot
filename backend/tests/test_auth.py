def test_bootstrap_creates_the_first_admin(client):
    response = client.post(
        "/api/auth/bootstrap",
        json={"email": "boss@hateco.vn", "password": "hunter2hunter2"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["user"]["email"] == "boss@hateco.vn"
    assert body["user"]["role"] == "admin"
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_bootstrap_refuses_once_a_user_exists(client):
    client.post(
        "/api/auth/bootstrap",
        json={"email": "boss@hateco.vn", "password": "hunter2hunter2"},
    )

    response = client.post(
        "/api/auth/bootstrap",
        json={"email": "second@hateco.vn", "password": "hunter2hunter2"},
    )

    assert response.status_code == 409


def test_login_returns_a_token_for_valid_credentials(client):
    client.post(
        "/api/auth/bootstrap",
        json={"email": "boss@hateco.vn", "password": "hunter2hunter2"},
    )

    response = client.post(
        "/api/auth/login",
        json={"email": "boss@hateco.vn", "password": "hunter2hunter2"},
    )

    assert response.status_code == 200
    assert response.json()["access_token"]


def test_login_rejects_a_wrong_password(client):
    client.post(
        "/api/auth/bootstrap",
        json={"email": "boss@hateco.vn", "password": "hunter2hunter2"},
    )

    response = client.post(
        "/api/auth/login",
        json={"email": "boss@hateco.vn", "password": "not-the-password"},
    )

    assert response.status_code == 401


def test_me_returns_the_current_user(client, admin_token, auth):
    response = client.get("/api/auth/me", headers=auth(admin_token))

    assert response.status_code == 200
    assert response.json()["role"] == "admin"


def test_me_without_a_token_is_unauthorised(client):
    response = client.get("/api/auth/me")

    assert response.status_code == 401
