from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient

from tests.helpers import csrf_from, register_and_login


def test_health_public(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_private_pages_redirect_when_logged_out(client: TestClient):
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"].startswith("/login")


def test_register_login_logout_and_session_cleared(client: TestClient):
    register_and_login(client, "a@example.com")
    home = client.get("/")
    assert home.status_code == 200
    assert "日历" in home.text

    token = csrf_from(client)
    logout = client.post("/logout", data={"csrf_token": token}, follow_redirects=False)
    assert logout.status_code == 303
    # Cookie cleared
    blocked = client.get("/", follow_redirects=False)
    assert blocked.status_code == 303


def test_users_cannot_see_each_others_data(client: TestClient):
    register_and_login(client, "alice@example.com")
    today = date.today().isoformat()
    token = csrf_from(client)

    # Alice saves weight + meal
    save = client.post(
        f"/day/{today}",
        data={
            "csrf_token": token,
            "weight_kg": "60",
            "sleep_hours": "7",
            "fatigue_level": "3",
            "daily_note": "alice-note",
            "waist_cm": "",
        },
        follow_redirects=False,
    )
    assert save.status_code == 303

    token = csrf_from(client)
    meal = client.post(
        f"/day/{today}/meals",
        data={
            "csrf_token": token,
            "meal_type": "lunch",
            "meal_name": "",
            "description": "鸡胸肉米饭",
            "calories": "500",
            "protein_g": "40",
            "carbs_g": "50",
            "fat_g": "10",
            "notes": "",
        },
        follow_redirects=False,
    )
    assert meal.status_code == 303

    alice_day = client.get(f"/day/{today}")
    assert "alice-note" in alice_day.text
    assert "鸡胸肉米饭" in alice_day.text
    assert "500" in alice_day.text

    # Logout Alice, login Bob
    token = csrf_from(client)
    client.post("/logout", data={"csrf_token": token}, follow_redirects=False)
    register_and_login(client, "bob@example.com")

    bob_day = client.get(f"/day/{today}")
    assert bob_day.status_code == 200
    assert "alice-note" not in bob_day.text
    assert "鸡胸肉米饭" not in bob_day.text

    bob_home = client.get("/")
    assert "500 kcal" not in bob_home.text


def test_guessing_foreign_meal_id_returns_404(client: TestClient):
    register_and_login(client, "owner@example.com")
    today = date.today().isoformat()
    token = csrf_from(client)
    client.post(
        f"/day/{today}/meals",
        data={
            "csrf_token": token,
            "meal_type": "dinner",
            "meal_name": "",
            "description": "私密晚餐",
            "calories": "700",
            "protein_g": "30",
            "carbs_g": "70",
            "fat_g": "20",
            "notes": "",
        },
        follow_redirects=False,
    )

    # Find meal id from DB
    from app.database import SessionLocal
    from app.models import MealEntry

    db = SessionLocal()
    meal_id = db.query(MealEntry).filter(MealEntry.description == "私密晚餐").first().id
    db.close()

    token = csrf_from(client)
    client.post("/logout", data={"csrf_token": token}, follow_redirects=False)
    register_and_login(client, "intruder@example.com")

    media = client.get(f"/media/meals/{meal_id}")
    assert media.status_code == 404

    token = csrf_from(client)
    deleted = client.post(
        f"/day/{today}/meals/{meal_id}/delete",
        data={"csrf_token": token},
        follow_redirects=False,
    )
    assert deleted.status_code == 404


def test_two_users_can_record_same_day(client: TestClient):
    today = date.today().isoformat()

    register_and_login(client, "u1@example.com")
    token = csrf_from(client)
    client.post(
        f"/day/{today}",
        data={
            "csrf_token": token,
            "weight_kg": "70",
            "sleep_hours": "",
            "fatigue_level": "",
            "daily_note": "u1",
            "waist_cm": "",
        },
        follow_redirects=False,
    )
    token = csrf_from(client)
    client.post("/logout", data={"csrf_token": token}, follow_redirects=False)

    register_and_login(client, "u2@example.com")
    token = csrf_from(client)
    save = client.post(
        f"/day/{today}",
        data={
            "csrf_token": token,
            "weight_kg": "80",
            "sleep_hours": "",
            "fatigue_level": "",
            "daily_note": "u2",
            "waist_cm": "",
        },
        follow_redirects=False,
    )
    assert save.status_code == 303
    page = client.get(f"/day/{today}")
    assert "u2" in page.text
    assert "80" in page.text


def test_manual_nutrition_does_not_require_openai(client: TestClient, monkeypatch):
    called = {"vision": False}

    def fake_vision(*args, **kwargs):
        called["vision"] = True
        raise AssertionError("vision should not be called in manual mode")

    monkeypatch.setattr(
        "app.routers.day.estimate_food_from_image",
        fake_vision,
    )

    register_and_login(client, "manual@example.com")
    today = date.today().isoformat()
    token = csrf_from(client)
    response = client.post(
        f"/day/{today}/meals",
        data={
            "csrf_token": token,
            "meal_type": "snack",
            "meal_name": "",
            "description": "随便吃点",
            "calories": "200",
            "protein_g": "10",
            "carbs_g": "20",
            "fat_g": "8",
            "notes": "",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert called["vision"] is False


def test_next_param_rejects_external_redirect(client: TestClient):
    register_and_login(client, "next@example.com")
    token = csrf_from(client)
    client.post("/logout", data={"csrf_token": token}, follow_redirects=False)
    token = csrf_from(client)
    response = client.post(
        "/login",
        data={
            "email": "next@example.com",
            "password": "password123",
            "csrf_token": token,
            "next": "https://evil.example/phish",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/"


def test_forgot_password_uniform_message(client: TestClient):
    token = csrf_from(client)
    response = client.post(
        "/forgot-password",
        data={"email": "nobody@example.com", "csrf_token": token},
    )
    assert response.status_code == 200
    assert "如果该邮箱已注册" in response.text
