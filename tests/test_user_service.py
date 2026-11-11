"""Automated tests for the mandatory scenarios (in-memory SQLite, no MySQL needed).

Tokens are created here exactly like the Auth Service does (HS256, sub = user id),
using the shared secret.
"""
import os

os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-pytest-only-1234567890"
os.environ["DATABASE_URL"] = "sqlite://"

from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.database.connection import Base, get_db
from app.main import app
from app.models.address_model import UserAddress
from app.models.user_model import UserProfile

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)


@event.listens_for(engine, "connect")
def _fk_on(dbapi_conn, _):
    dbapi_conn.execute("PRAGMA foreign_keys=ON")


TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def token(user_id, minutes=30, secret=None, role="user"):
    now = datetime.now(timezone.utc)
    return jwt.encode({"sub": str(user_id), "role": role, "iat": now, "exp": now + timedelta(minutes=minutes)},
                      secret or settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def H(user_id):
    return {"Authorization": f"Bearer {token(user_id)}"}


PROFILE = {"full_name": "Dinesh Kumar", "phone_number": "9876543210",
           "date_of_birth": "2000-05-20", "gender": "Male", "profile_image": "https://img.example/a.png"}


def address(**over):
    base = {"address_type": "Home", "full_name": "Dinesh Kumar", "phone_number": "9876543210",
            "address_line_1": "12 Main Street", "address_line_2": "Near Park", "city": "Chennai",
            "state": "Tamil Nadu", "country": "India", "postal_code": "600001", "is_default": False}
    base.update(over)
    return base


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def make_profile(uid=1, **over):
    return client.post("/api/users/profile", headers=H(uid), json={**PROFILE, **over})


def add_addr(uid=1, **over):
    return client.post("/api/users/addresses", headers=H(uid), json=address(**over))


# ---------------- authentication ----------------
def test_01_no_token_401():
    for method, url in [("get", "/api/users/profile"), ("get", "/api/users/addresses")]:
        r = getattr(client, method)(url)
        assert r.status_code == 401 and "Bearer token missing" in r.json()["detail"]


def test_02_invalid_token_401():
    r = client.get("/api/users/profile", headers={"Authorization": "Bearer abc.def.ghi"})
    assert r.status_code == 401 and r.json()["detail"] == "Invalid token"
    wrong = {"Authorization": f"Bearer {token(1, secret='another-secret-key-xxxxxxxxxxxxxxxxxx')}"}
    assert client.get("/api/users/profile", headers=wrong).status_code == 401


def test_02b_expired_token_401():
    r = client.get("/api/users/profile", headers={"Authorization": f"Bearer {token(1, minutes=-5)}"})
    assert r.status_code == 401 and "expired" in r.json()["detail"].lower()


# ---------------- profile ----------------
def test_03_create_profile():
    r = make_profile(7)
    assert r.status_code == 201
    body = r.json()
    assert body["auth_user_id"] == 7 and body["is_active"] is True and body["phone_number"] == "9876543210"
    assert "password" not in body and "password_hash" not in body


def test_04_duplicate_profile_409():
    make_profile(1)
    assert make_profile(1).status_code == 409


def test_05_get_profile():
    make_profile(1)
    r = client.get("/api/users/profile", headers=H(1))
    assert r.status_code == 200 and r.json()["full_name"] == "Dinesh Kumar"


def test_05b_get_profile_before_create_404():
    assert client.get("/api/users/profile", headers=H(1)).status_code == 404


def test_06_put_updates_profile():
    make_profile(1)
    r = client.put("/api/users/profile", headers=H(1), json={**PROFILE, "full_name": "Dinesh K", "gender": "other"})
    assert r.status_code == 200 and r.json()["full_name"] == "Dinesh K" and r.json()["gender"] == "Other"


def test_07_patch_updates_only_sent_fields():
    make_profile(1)
    r = client.patch("/api/users/profile", headers=H(1), json={"phone_number": "+91 98765-43211"})
    assert r.status_code == 200
    assert r.json()["phone_number"] == "+919876543211" and r.json()["full_name"] == "Dinesh Kumar"
    assert client.patch("/api/users/profile", headers=H(1), json={}).status_code == 422


def test_profile_validation_422():
    assert make_profile(1, phone_number="12345").status_code == 422
    assert make_profile(1, phone_number="abcdefghij").status_code == 422
    assert make_profile(1, date_of_birth="2999-01-01").status_code == 422
    assert make_profile(1, gender="robot").status_code == 422
    assert make_profile(1, full_name="A").status_code == 422
    bad = {k: v for k, v in PROFILE.items() if k != "phone_number"}
    assert client.post("/api/users/profile", headers=H(1), json=bad).status_code == 422


def test_body_cannot_set_auth_user_id():
    r = client.post("/api/users/profile", headers=H(1), json={**PROFILE, "auth_user_id": 99})
    assert r.status_code == 422
    assert client.get("/api/users/profile", headers=H(99)).status_code == 404


def test_delete_profile_removes_addresses():
    make_profile(1)
    add_addr(1)
    r = client.delete("/api/users/profile", headers=H(1))
    assert r.status_code == 200
    db = TestingSession()
    assert db.query(UserProfile).count() == 0 and db.query(UserAddress).count() == 0
    db.close()
    assert client.get("/api/users/profile", headers=H(1)).status_code == 404


# ---------------- addresses ----------------
def test_08_add_multiple_addresses_and_first_is_default():
    make_profile(1)
    a1 = add_addr(1, address_type="Home")
    a2 = add_addr(1, address_type="Office", address_line_1="99 Office Road")
    a3 = add_addr(1, address_type="other")
    assert a1.status_code == a2.status_code == a3.status_code == 201
    assert a1.json()["is_default"] is True       # first one is default automatically
    assert a2.json()["is_default"] is False
    assert a3.json()["address_type"] == "Other"


def test_09_list_addresses():
    make_profile(1)
    add_addr(1)
    add_addr(1, address_type="Office")
    r = client.get("/api/users/addresses", headers=H(1))
    assert r.status_code == 200 and len(r.json()) == 2 and r.json()[0]["is_default"] is True


def test_10_update_address():
    make_profile(1)
    aid = add_addr(1).json()["id"]
    r = client.put(f"/api/users/addresses/{aid}", headers=H(1), json=address(city="Madurai", postal_code="625001"))
    assert r.status_code == 200 and r.json()["city"] == "Madurai"
    assert client.get(f"/api/users/addresses/{aid}", headers=H(1)).json()["postal_code"] == "625001"


def test_11_12_set_default_keeps_exactly_one_default():
    make_profile(1)
    a1 = add_addr(1).json()["id"]
    a2 = add_addr(1, address_type="Office").json()["id"]
    r = client.patch(f"/api/users/addresses/{a2}/default", headers=H(1))
    assert r.status_code == 200 and r.json()["is_default"] is True
    rows = client.get("/api/users/addresses", headers=H(1)).json()
    assert [a["id"] for a in rows if a["is_default"]] == [a2]
    # creating a new address with is_default=true moves the default again
    a3 = add_addr(1, address_type="Other", is_default=True).json()["id"]
    rows = client.get("/api/users/addresses", headers=H(1)).json()
    assert [a["id"] for a in rows if a["is_default"]] == [a3]
    # database level check
    db = TestingSession()
    assert db.query(UserAddress).filter(UserAddress.user_id == 1, UserAddress.is_default.is_(True)).count() == 1
    db.close()
    assert a1 != a2


def test_13_delete_address_and_default_is_reassigned():
    make_profile(1)
    a1 = add_addr(1).json()["id"]
    a2 = add_addr(1, address_type="Office").json()["id"]
    assert client.delete(f"/api/users/addresses/{a1}", headers=H(1)).status_code == 200
    assert client.get(f"/api/users/addresses/{a1}", headers=H(1)).status_code == 404
    left = client.get("/api/users/addresses", headers=H(1)).json()
    assert len(left) == 1 and left[0]["id"] == a2 and left[0]["is_default"] is True


def test_address_validation_422():
    make_profile(1)
    assert add_addr(1, address_type="Hotel").status_code == 422
    assert add_addr(1, postal_code="!!").status_code == 422
    assert add_addr(1, phone_number="123").status_code == 422
    assert add_addr(1, city="").status_code == 422
    bad = {k: v for k, v in address().items() if k != "address_line_1"}
    assert client.post("/api/users/addresses", headers=H(1), json=bad).status_code == 422


def test_address_not_found_404():
    make_profile(1)
    assert client.get("/api/users/addresses/9999", headers=H(1)).status_code == 404
    assert client.delete("/api/users/addresses/9999", headers=H(1)).status_code == 404
    assert client.patch("/api/users/addresses/9999/default", headers=H(1)).status_code == 404


def test_addresses_need_a_profile_first():
    assert add_addr(1).status_code == 404


# ---------------- authorization between users ----------------
def test_14_cannot_access_another_users_profile():
    make_profile(1)
    # user 2 has no profile: gets 404, never user 1's data
    assert client.get("/api/users/profile", headers=H(2)).status_code == 404
    make_profile(2, full_name="Second User", phone_number="9123456780")
    mine = client.get("/api/users/profile", headers=H(2)).json()
    assert mine["auth_user_id"] == 2 and mine["full_name"] == "Second User"
    assert client.get("/api/users/profile", headers=H(1)).json()["full_name"] == "Dinesh Kumar"
    # updating as user 2 never touches user 1
    client.patch("/api/users/profile", headers=H(2), json={"full_name": "Changed Name"})
    assert client.get("/api/users/profile", headers=H(1)).json()["full_name"] == "Dinesh Kumar"


def test_15_cannot_access_another_users_address():
    make_profile(1)
    make_profile(2, full_name="Second User")
    aid = add_addr(1).json()["id"]
    assert client.get(f"/api/users/addresses/{aid}", headers=H(2)).status_code == 403
    assert client.put(f"/api/users/addresses/{aid}", headers=H(2), json=address()).status_code == 403
    assert client.delete(f"/api/users/addresses/{aid}", headers=H(2)).status_code == 403
    assert client.patch(f"/api/users/addresses/{aid}/default", headers=H(2)).status_code == 403
    # the address is untouched and user 2 sees none of user 1's addresses
    assert client.get(f"/api/users/addresses/{aid}", headers=H(1)).status_code == 200
    assert client.get("/api/users/addresses", headers=H(2)).json() == []


# ---------------- account management ----------------
def test_account_overview():
    make_profile(1)
    add_addr(1)
    r = client.get("/api/users/account", headers=H(1))
    assert r.status_code == 200 and r.json()["address_count"] == 1 and r.json()["profile"]["is_active"] is True


def test_deactivate_blocks_profile_apis_but_not_account_view():
    make_profile(1)
    add_addr(1)
    r = client.patch("/api/users/profile/deactivate", headers=H(1))
    assert r.status_code == 200 and r.json()["is_active"] is False
    assert client.patch("/api/users/profile/deactivate", headers=H(1)).status_code == 409
    assert client.get("/api/users/profile", headers=H(1)).status_code == 403
    assert client.get("/api/users/addresses", headers=H(1)).status_code == 403
    assert add_addr(1).status_code == 403
    assert client.get("/api/users/account", headers=H(1)).json()["profile"]["is_active"] is False
    assert client.patch("/api/users/profile/reactivate", headers=H(1)).json()["is_active"] is True
    assert client.get("/api/users/profile", headers=H(1)).status_code == 200


def test_health_check():
    assert client.get("/").json()["status"] == "running"
