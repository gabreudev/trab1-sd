import pytest


class TestSignup:
    def test_signup_success(self, client):
        resp = client.post(
            "/api/auth/signup",
            json={"email": "new@test.com", "password": "pass123"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["email"] == "new@test.com"
        assert data["user_id"] != ""

    def test_signup_duplicate_user(self, client):
        client.post(
            "/api/auth/signup",
            json={"email": "dup@test.com", "password": "pass123"},
        )
        resp = client.post(
            "/api/auth/signup",
            json={"email": "dup@test.com", "password": "pass123"},
        )
        assert resp.status_code == 400

    def test_signup_missing_email(self, client):
        resp = client.post(
            "/api/auth/signup",
            json={"password": "pass123"},
        )
        assert resp.status_code == 422  # validation error

    def test_signup_missing_password(self, client):
        resp = client.post(
            "/api/auth/signup",
            json={"email": "no@test.com"},
        )
        assert resp.status_code == 422


class TestLogin:
    def test_login_success(self, client):
        client.post(
            "/api/auth/signup",
            json={"email": "login@test.com", "password": "pass123"},
        )
        resp = client.post(
            "/api/auth/login",
            json={"email": "login@test.com", "password": "pass123"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["email"] == "login@test.com"

    def test_login_wrong_password(self, client):
        client.post(
            "/api/auth/signup",
            json={"email": "wrong@test.com", "password": "pass123"},
        )
        resp = client.post(
            "/api/auth/login",
            json={"email": "wrong@test.com", "password": "wrongpassword"},
        )
        assert resp.status_code == 400

    def test_login_nonexistent_user(self, client):
        resp = client.post(
            "/api/auth/login",
            json={"email": "ghost@test.com", "password": "pass123"},
        )
        assert resp.status_code == 400


class TestLogout:
    def test_logout_success(self, client, auth_headers):
        resp = client.post("/api/auth/logout", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_logout_without_token(self, client):
        resp = client.post("/api/auth/logout")
        assert resp.status_code == 401

    def test_logout_invalid_token(self, client):
        resp = client.post(
            "/api/auth/logout",
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert resp.status_code == 401


class TestMe:
    def test_me_success(self, client, auth_headers):
        resp = client.get("/api/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "user@test.com"
        assert "id" in data

    def test_me_without_token(self, client):
        resp = client.get("/api/auth/me")
        assert resp.status_code == 401

    def test_me_invalid_token(self, client):
        resp = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert resp.status_code == 401
