from fastapi.testclient import TestClient


def csrf_from(client: TestClient) -> str:
    response = client.get("/login")
    assert response.status_code == 200
    token = client.cookies.get("cutnbulk_csrf")
    assert token
    return token


def register_and_login(client: TestClient, email: str, password: str = "password123") -> None:
    token = csrf_from(client)
    response = client.post(
        "/register",
        data={
            "email": email,
            "password": password,
            "confirm_password": password,
            "csrf_token": token,
            "next": "/",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303, response.text
    assert client.cookies.get("cutnbulk_session")
