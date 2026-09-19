def test_admin_can_create_a_user(client, admin_token, auth):
    response = client.post(
        "/api/users",
        headers=auth(admin_token),
        json={"email": "new@hateco.vn", "password": "another-pass-1", "role": "member"},
    )

    assert response.status_code == 201
    assert response.json()["email"] == "new@hateco.vn"
    assert response.json()["role"] == "member"


def test_created_user_can_log_in(client, admin_token, auth):
    client.post(
        "/api/users",
        headers=auth(admin_token),
        json={"email": "new@hateco.vn", "password": "another-pass-1", "role": "member"},
    )

    response = client.post(
        "/api/auth/login",
        json={"email": "new@hateco.vn", "password": "another-pass-1"},
    )

    assert response.status_code == 200


def test_duplicate_email_is_rejected(client, admin_token, auth):
    client.post(
        "/api/users",
        headers=auth(admin_token),
        json={"email": "new@hateco.vn", "password": "another-pass-1", "role": "member"},
    )

    response = client.post(
        "/api/users",
        headers=auth(admin_token),
        json={"email": "new@hateco.vn", "password": "another-pass-2", "role": "member"},
    )

    assert response.status_code == 409


def test_member_cannot_list_users(client, member_token, auth):
    response = client.get("/api/users", headers=auth(member_token))

    assert response.status_code == 403


def test_admin_can_deactivate_a_user(client, admin_token, auth, member_user):
    response = client.delete(f"/api/users/{member_user['id']}", headers=auth(admin_token))

    assert response.status_code == 200
    assert response.json()["is_active"] is False


def test_deactivated_user_cannot_log_in(client, admin_token, auth, member_user):
    client.delete(f"/api/users/{member_user['id']}", headers=auth(admin_token))

    response = client.post(
        "/api/auth/login",
        json={"email": member_user["email"], "password": "member-password-123"},
    )

    assert response.status_code == 403


def test_admin_cannot_deactivate_themselves(client, admin_token, auth):
    me = client.get("/api/auth/me", headers=auth(admin_token)).json()

    response = client.delete(f"/api/users/{me['id']}", headers=auth(admin_token))

    assert response.status_code == 400
