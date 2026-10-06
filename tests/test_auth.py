import pytest

from app.database import SessionLocal
from app.models.user import User
from app.security import hash_password


@pytest.fixture()
def secured(client, monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "0")
    with SessionLocal() as db:
        db.add(User(username="boss", password_hash=hash_password("secret123"), role="admin"))
        db.add(User(username="worker", password_hash=hash_password("secret123"), role="staff"))
        db.commit()
    return client


def login(c, user, pw="secret123"):
    return c.post("/auth/login", json={"username": user, "password": pw})


def hdr(c, user):
    r = login(c, user)
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_endpoints_require_login(secured):
    assert secured.get("/partners").status_code == 401
    assert secured.get("/reports/summary").status_code == 401
    assert secured.get("/health").status_code == 200  # monitoring uchun ochiq


def test_login_and_me(secured):
    assert login(secured, "boss", "xato-parol").status_code == 401
    assert login(secured, "yoq-user").status_code == 401
    h = hdr(secured, "boss")
    assert secured.get("/auth/me", headers=h).json()["role"] == "admin"
    assert secured.get("/partners", headers=h).status_code == 200
    assert secured.get("/partners", headers={"Authorization": "Bearer yaroqsiz"}).status_code == 401


def test_staff_cannot_delete_but_can_create(secured):
    admin, staff = hdr(secured, "boss"), hdr(secured, "worker")
    r = secured.post("/partners", json={"name": "Hamkor X"}, headers=staff)
    assert r.status_code == 201
    pid = r.json()["id"]
    assert secured.delete(f"/partners/{pid}", headers=staff).status_code == 403
    assert secured.delete(f"/partners/{pid}", headers=admin).status_code == 200


def test_user_management_admin_only(secured):
    admin, staff = hdr(secured, "boss"), hdr(secured, "worker")
    body = {"username": "yangi", "password": "parol12345", "role": "staff"}
    assert secured.post("/auth/users", json=body, headers=staff).status_code == 403
    assert secured.post("/auth/users", json=body, headers=admin).status_code == 201
    assert login(secured, "yangi", "parol12345").status_code == 200


def test_change_password(secured):
    h = hdr(secured, "worker")
    bad = secured.post("/auth/change-password", json={"old_password": "x", "new_password": "yangiparol1"}, headers=h)
    assert bad.status_code == 400
    ok = secured.post("/auth/change-password", json={"old_password": "secret123", "new_password": "yangiparol1"}, headers=h)
    assert ok.status_code == 200
    assert login(secured, "worker").status_code == 401
    assert login(secured, "worker", "yangiparol1").status_code == 200


def test_admin_can_delete_users_including_admins(secured):
    admin, staff = hdr(secured, "boss"), hdr(secured, "worker")
    body = {"username": "boshqa_admin", "password": "parol12345", "role": "admin"}
    other = secured.post("/auth/users", json=body, headers=admin).json()
    other_token = {"Authorization": f"Bearer {login(secured, 'boshqa_admin', 'parol12345').json()['access_token']}"}
    users = {u["username"]: u["id"] for u in secured.get("/auth/users", headers=admin).json()}

    # xodim o'chira olmaydi
    assert secured.delete(f"/auth/users/{other['id']}", headers=staff).status_code == 403
    # o'zini o'chirib bo'lmaydi
    assert secured.delete(f"/auth/users/{users['boss']}", headers=admin).status_code == 400
    # boshqa adminni o'chirish mumkin; eski tokeni va logini darrov ishlamaydi
    assert secured.delete(f"/auth/users/{other['id']}", headers=admin).status_code == 200
    assert secured.get("/auth/me", headers=other_token).status_code == 401
    assert login(secured, "boshqa_admin", "parol12345").status_code == 401
    # xodimni ham o'chirish mumkin, bo'lmagan foydalanuvchi 404
    assert secured.delete(f"/auth/users/{users['worker']}", headers=admin).status_code == 200
    assert secured.delete(f"/auth/users/{users['worker']}", headers=admin).status_code == 404
    assert [u["username"] for u in secured.get("/auth/users", headers=admin).json()] == ["boss"]
