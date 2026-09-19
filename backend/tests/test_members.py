def test_owner_can_add_a_member(client, admin_token, auth, page_id, member_user):
    response = client.put(
        f"/api/pages/{page_id}/members",
        headers=auth(admin_token),
        json={"user_id": member_user["id"], "role": "editor"},
    )

    assert response.status_code == 200
    assert response.json()["role"] == "editor"
    assert response.json()["email"] == member_user["email"]


def test_adding_the_same_member_twice_updates_the_role(
    client, admin_token, auth, page_id, member_user
):
    client.put(
        f"/api/pages/{page_id}/members",
        headers=auth(admin_token),
        json={"user_id": member_user["id"], "role": "viewer"},
    )

    response = client.put(
        f"/api/pages/{page_id}/members",
        headers=auth(admin_token),
        json={"user_id": member_user["id"], "role": "owner"},
    )
    listing = client.get(f"/api/pages/{page_id}/members", headers=auth(admin_token))

    assert response.status_code == 200
    assert response.json()["role"] == "owner"
    assert len([m for m in listing.json() if m["user_id"] == member_user["id"]]) == 1


def test_invalid_role_is_rejected(client, admin_token, auth, page_id, member_user):
    response = client.put(
        f"/api/pages/{page_id}/members",
        headers=auth(admin_token),
        json={"user_id": member_user["id"], "role": "superuser"},
    )

    assert response.status_code == 422


def test_member_can_list_but_not_change_members(
    client, admin_token, member_token, auth, page_id, member_user
):
    client.put(
        f"/api/pages/{page_id}/members",
        headers=auth(admin_token),
        json={"user_id": member_user["id"], "role": "viewer"},
    )

    listing = client.get(f"/api/pages/{page_id}/members", headers=auth(member_token))
    attempt = client.put(
        f"/api/pages/{page_id}/members",
        headers=auth(member_token),
        json={"user_id": member_user["id"], "role": "owner"},
    )

    assert listing.status_code == 200
    assert attempt.status_code == 403


def test_owner_can_remove_a_member(client, admin_token, auth, page_id, member_user):
    client.put(
        f"/api/pages/{page_id}/members",
        headers=auth(admin_token),
        json={"user_id": member_user["id"], "role": "editor"},
    )

    response = client.delete(
        f"/api/pages/{page_id}/members/{member_user['id']}", headers=auth(admin_token)
    )
    listing = client.get(f"/api/pages/{page_id}/members", headers=auth(admin_token))

    assert response.status_code == 204
    assert member_user["id"] not in [m["user_id"] for m in listing.json()]


def test_adding_an_unknown_user_returns_404(client, admin_token, auth, page_id):
    response = client.put(
        f"/api/pages/{page_id}/members",
        headers=auth(admin_token),
        json={"user_id": 99999, "role": "editor"},
    )

    assert response.status_code == 404
