import pytest


class TestCreateTask:
    def test_create_task_minimal(self, client, auth_headers):
        resp = client.post(
            "/api/tasks",
            json={"title": "Minha tarefa"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Minha tarefa"
        assert data["description"] == ""
        assert data["priority"] == "media"
        assert data["status"] == "pendente"
        assert data["due_date"] is None
        assert "id" in data
        assert "created_at" in data

    def test_create_task_full(self, client, auth_headers):
        resp = client.post(
            "/api/tasks",
            json={
                "title": "Estudar pytest",
                "description": "Aprender a escrever testes",
                "due_date": "2026-12-31",
                "priority": "alta",
                "status": "em_andamento",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Estudar pytest"
        assert data["description"] == "Aprender a escrever testes"
        assert data["due_date"] == "2026-12-31"
        assert data["priority"] == "alta"
        assert data["status"] == "em_andamento"

    def test_create_task_without_auth(self, client):
        resp = client.post(
            "/api/tasks",
            json={"title": "Sem auth"},
        )
        assert resp.status_code == 401

    def test_create_task_empty_title(self, client, auth_headers):
        resp = client.post(
            "/api/tasks",
            json={"title": ""},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_create_task_blank_title(self, client, auth_headers):
        resp = client.post(
            "/api/tasks",
            json={"title": "   "},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_create_multiple_tasks(self, client, auth_headers):
        for i in range(3):
            resp = client.post(
                "/api/tasks",
                json={"title": f"Tarefa {i}"},
                headers=auth_headers,
            )
            assert resp.status_code == 201

        resp = client.get("/api/tasks", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 3


class TestListTasks:
    def test_list_empty(self, client, auth_headers):
        resp = client.get("/api/tasks", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_with_tasks(self, client, auth_headers):
        client.post(
            "/api/tasks",
            json={"title": "Task A"},
            headers=auth_headers,
        )
        client.post(
            "/api/tasks",
            json={"title": "Task B"},
            headers=auth_headers,
        )
        resp = client.get("/api/tasks", headers=auth_headers)
        assert resp.status_code == 200
        tasks = resp.json()
        assert len(tasks) == 2
        titles = {t["title"] for t in tasks}
        assert "Task A" in titles
        assert "Task B" in titles

    def test_list_without_auth(self, client):
        resp = client.get("/api/tasks")
        assert resp.status_code == 401


class TestUpdateTask:
    def test_update_title(self, client, auth_headers):
        # Create
        resp = client.post(
            "/api/tasks",
            json={"title": "Original"},
            headers=auth_headers,
        )
        task_id = resp.json()["id"]

        # Update
        resp = client.put(
            f"/api/tasks/{task_id}",
            json={"title": "Atualizado"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "Atualizado"

    def test_update_priority(self, client, auth_headers):
        resp = client.post(
            "/api/tasks",
            json={"title": "Prioridade"},
            headers=auth_headers,
        )
        task_id = resp.json()["id"]
        assert resp.json()["priority"] == "media"

        resp = client.put(
            f"/api/tasks/{task_id}",
            json={"priority": "alta"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["priority"] == "alta"

    def test_update_status(self, client, auth_headers):
        resp = client.post(
            "/api/tasks",
            json={"title": "Status"},
            headers=auth_headers,
        )
        task_id = resp.json()["id"]

        resp = client.put(
            f"/api/tasks/{task_id}",
            json={"status": "concluida"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "concluida"

    def test_update_multiple_fields(self, client, auth_headers):
        resp = client.post(
            "/api/tasks",
            json={"title": "Original", "description": "Desc"},
            headers=auth_headers,
        )
        task_id = resp.json()["id"]

        resp = client.put(
            f"/api/tasks/{task_id}",
            json={
                "title": "Novo título",
                "description": "Nova descrição",
                "priority": "baixa",
                "due_date": "2026-06-15",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Novo título"
        assert data["description"] == "Nova descrição"
        assert data["priority"] == "baixa"
        assert data["due_date"] == "2026-06-15"

    def test_update_can_clear_due_date(self, client, auth_headers):
        created = client.post(
            "/api/tasks",
            json={"title": "Com prazo", "due_date": "2026-09-01"},
            headers=auth_headers,
        )
        task_id = created.json()["id"]

        resp = client.put(
            f"/api/tasks/{task_id}",
            json={"due_date": None},
            headers=auth_headers,
        )

        assert resp.status_code == 200
        assert resp.json()["due_date"] is None

    def test_update_nonexistent_task(self, client, auth_headers):
        resp = client.put(
            "/api/tasks/00000000-0000-0000-0000-000000000000",
            json={"title": "Ghost"},
            headers=auth_headers,
        )
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Tarefa não encontrada"

    def test_update_without_auth(self, client):
        resp = client.put(
            "/api/tasks/some-id",
            json={"title": "No auth"},
        )
        assert resp.status_code == 401

    def test_update_empty_body(self, client, auth_headers):
        resp = client.post(
            "/api/tasks",
            json={"title": "Test"},
            headers=auth_headers,
        )
        task_id = resp.json()["id"]

        resp = client.put(
            f"/api/tasks/{task_id}",
            json={},
            headers=auth_headers,
        )
        assert resp.status_code == 400


class TestDeleteTask:
    def test_delete_task(self, client, auth_headers):
        resp = client.post(
            "/api/tasks",
            json={"title": "Para deletar"},
            headers=auth_headers,
        )
        task_id = resp.json()["id"]

        resp = client.delete(f"/api/tasks/{task_id}", headers=auth_headers)
        assert resp.status_code == 204

        # Confirm deleted
        resp = client.get("/api/tasks", headers=auth_headers)
        assert len(resp.json()) == 0

    def test_delete_nonexistent_task(self, client, auth_headers):
        resp = client.delete(
            "/api/tasks/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_delete_without_auth(self, client):
        resp = client.delete("/api/tasks/some-id")
        assert resp.status_code == 401


class TestTaskIsolation:
    """Cada usuário só vê suas próprias tarefas."""

    def test_users_cannot_see_each_others_tasks(self, client):
        # User A
        resp_a = client.post(
            "/api/auth/signup",
            json={"email": "usera@test.com", "password": "pass123"},
        )
        token_a = resp_a.json()["access_token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}

        # User B
        resp_b = client.post(
            "/api/auth/signup",
            json={"email": "userb@test.com", "password": "pass123"},
        )
        token_b = resp_b.json()["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # User A creates a task
        client.post(
            "/api/tasks",
            json={"title": "Tarefa do A"},
            headers=headers_a,
        )

        # User B creates a task
        client.post(
            "/api/tasks",
            json={"title": "Tarefa do B"},
            headers=headers_b,
        )

        # User A only sees their task
        resp = client.get("/api/tasks", headers=headers_a)
        assert len(resp.json()) == 1
        assert resp.json()[0]["title"] == "Tarefa do A"

        # User B only sees their task
        resp = client.get("/api/tasks", headers=headers_b)
        assert len(resp.json()) == 1
        assert resp.json()[0]["title"] == "Tarefa do B"

    def test_user_cannot_update_or_delete_another_users_task(self, client):
        resp_a = client.post(
            "/api/auth/signup",
            json={"email": "owner@test.com", "password": "pass123"},
        )
        headers_a = {"Authorization": f"Bearer {resp_a.json()['access_token']}"}

        resp_b = client.post(
            "/api/auth/signup",
            json={"email": "intruder@test.com", "password": "pass123"},
        )
        headers_b = {"Authorization": f"Bearer {resp_b.json()['access_token']}"}

        created = client.post(
            "/api/tasks",
            json={"title": "Tarefa privada"},
            headers=headers_a,
        )
        task_id = created.json()["id"]

        update = client.put(
            f"/api/tasks/{task_id}",
            json={"title": "Invadida"},
            headers=headers_b,
        )
        assert update.status_code == 404

        delete = client.delete(f"/api/tasks/{task_id}", headers=headers_b)
        assert delete.status_code == 404

        owner_tasks = client.get("/api/tasks", headers=headers_a).json()
        assert len(owner_tasks) == 1
        assert owner_tasks[0]["title"] == "Tarefa privada"
