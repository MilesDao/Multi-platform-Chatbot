NEW_PAGE = {
    "fb_page_id": "222222222222222",
    "name": "Hateco Tuyen Sinh",
    "access_token": "EAAG-secret-token",
}


def _add_membership(page_id: int, user_id: int, role: str) -> None:
    from app.db import SessionLocal
    from app.models import PageMembership

    session = SessionLocal()
    session.add(PageMembership(page_id=page_id, user_id=user_id, role=role))
    session.commit()
    session.close()


def test_admin_can_create_a_page(client, admin_token, auth):
    response = client.post("/api/pages", headers=auth(admin_token), json=NEW_PAGE)

    assert response.status_code == 201
    body = response.json()
    assert body["fb_page_id"] == "222222222222222"
    assert body["has_access_token"] is True


def test_create_page_keeps_the_closing_message(client, admin_token, auth):
    response = client.post(
        "/api/pages",
        headers=auth(admin_token),
        json={**NEW_PAGE, "closing_message": "Goi 0123 456 789 de duoc tu van them nhe!"},
    )

    assert response.status_code == 201
    assert response.json()["closing_message"] == "Goi 0123 456 789 de duoc tu van them nhe!"


def test_page_response_never_leaks_the_access_token(client, admin_token, auth):
    response = client.post("/api/pages", headers=auth(admin_token), json=NEW_PAGE)

    assert "EAAG-secret-token" not in response.text
    assert "access_token" not in response.json()


def test_duplicate_facebook_page_id_is_rejected(client, admin_token, auth):
    client.post("/api/pages", headers=auth(admin_token), json=NEW_PAGE)

    response = client.post("/api/pages", headers=auth(admin_token), json=NEW_PAGE)

    assert response.status_code == 409


def test_admin_sees_every_page(client, admin_token, auth, page_id):
    response = client.get("/api/pages", headers=auth(admin_token))

    assert response.status_code == 200
    assert [p["id"] for p in response.json()] == [page_id]


def test_member_without_membership_sees_no_pages(client, member_token, auth, page_id):
    response = client.get("/api/pages", headers=auth(member_token))

    assert response.status_code == 200
    assert response.json() == []


def test_member_without_membership_cannot_open_a_page(
    client, member_token, auth, page_id
):
    response = client.get(f"/api/pages/{page_id}", headers=auth(member_token))

    assert response.status_code == 403


def test_member_with_viewer_membership_can_read_but_not_edit(
    client, admin_token, member_token, auth, page_id, member_user
):
    _add_membership(page_id, member_user["id"], "viewer")

    read = client.get(f"/api/pages/{page_id}", headers=auth(member_token))
    write = client.patch(
        f"/api/pages/{page_id}", headers=auth(member_token), json={"name": "Renamed"}
    )

    assert read.status_code == 200
    assert read.json()["my_role"] == "viewer"
    assert write.status_code == 403


def test_editor_can_edit_instructions(
    client, member_token, auth, page_id, member_user
):
    _add_membership(page_id, member_user["id"], "editor")

    response = client.patch(
        f"/api/pages/{page_id}",
        headers=auth(member_token),
        json={"system_prompt": "Be brief.", "closing_message": "Goi hotline nhe!"},
    )

    assert response.status_code == 200
    assert response.json()["system_prompt"] == "Be brief."
    assert response.json()["closing_message"] == "Goi hotline nhe!"


def test_editor_cannot_change_owner_only_settings(
    client, member_token, auth, page_id, member_user
):
    _add_membership(page_id, member_user["id"], "editor")

    for body in (
        {"name": "Renamed"},
        {"access_token": "EAAG-stolen"},
        {"is_active": False},
    ):
        response = client.patch(
            f"/api/pages/{page_id}", headers=auth(member_token), json=body
        )
        assert response.status_code == 403, body


def test_editor_cannot_delete_a_page(client, member_token, auth, page_id, member_user):
    _add_membership(page_id, member_user["id"], "editor")

    response = client.delete(f"/api/pages/{page_id}", headers=auth(member_token))

    assert response.status_code == 403


def test_owner_can_rename_a_page(client, admin_token, auth, page_id):
    response = client.patch(
        f"/api/pages/{page_id}", headers=auth(admin_token), json={"name": "Renamed"}
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Renamed"


def test_updating_the_access_token_keeps_it_hidden(client, admin_token, auth, page_id):
    response = client.patch(
        f"/api/pages/{page_id}",
        headers=auth(admin_token),
        json={"access_token": "EAAG-rotated-token"},
    )

    assert response.status_code == 200
    assert "EAAG-rotated-token" not in response.text
    assert response.json()["has_access_token"] is True


def test_admin_can_delete_a_page(client, admin_token, auth, page_id):
    response = client.delete(f"/api/pages/{page_id}", headers=auth(admin_token))

    assert response.status_code == 204
    assert client.get("/api/pages", headers=auth(admin_token)).json() == []
