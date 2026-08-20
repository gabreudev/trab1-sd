import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Mock Supabase client — evita dependência do Supabase real nos testes
# ---------------------------------------------------------------------------
class MockUser:
    def __init__(self, user_id="test-user-id", email="test@example.com"):
        self.id = user_id
        self.email = email


class MockSession:
    _counter = 0

    def __init__(self):
        MockSession._counter += 1
        self.access_token = f"mock-token-{MockSession._counter}-{id(self)}"
        self.refresh_token = f"mock-refresh-{MockSession._counter}"


class MockAuthResponse:
    def __init__(self, user=None, session=None):
        self.user = user
        self.session = session


class MockSupabaseAuth:
    _counter = 0

    def __init__(self):
        self.users_db = {}  # email -> {password, user}
        self.tokens_db = {}  # token -> MockUser

    def _next_id(self):
        MockSupabaseAuth._counter += 1
        return f"uid-{MockSupabaseAuth._counter}"

    def sign_up(self, credentials):
        email = credentials["email"]
        password = credentials["password"]
        if email in self.users_db:
            raise Exception("User already registered")
        user = MockUser(user_id=self._next_id(), email=email)
        self.users_db[email] = {"password": password, "user": user}
        session = MockSession()
        self.tokens_db[session.access_token] = user
        return MockAuthResponse(user=user, session=session)

    def sign_in_with_password(self, credentials):
        email = credentials["email"]
        password = credentials["password"]
        if email not in self.users_db:
            raise Exception("Invalid login credentials")
        if self.users_db[email]["password"] != password:
            raise Exception("Invalid login credentials")
        user = self.users_db[email]["user"]
        session = MockSession()
        self.tokens_db[session.access_token] = user
        return MockAuthResponse(user=user, session=session)

    def get_user(self, token):
        if token == "invalid-token":
            return None
        user = self.tokens_db.get(token)
        if user:
            return MockAuthResponse(user=user, session=None)
        return MockAuthResponse(user=MockUser(), session=None)


class MockAdminAuth:
    def __init__(self, auth: MockSupabaseAuth):
        self._auth = auth

    def create_user(self, data):
        email = data["email"]
        password = data["password"]
        if email in self._auth.users_db:
            raise Exception("User already registered")
        user = MockUser(user_id=f"uid-{len(self._auth.users_db)+1}", email=email)
        self._auth.users_db[email] = {"password": password, "user": user}

    def sign_out(self, user_id):
        pass


class MockQueryBuilder:
    def __init__(self, table_data: list):
        self._data = table_data
        self._filters = []
        self._order_by = None
        self._order_desc = False
        self._single = False

    def select(self, *args):
        return self

    def eq(self, field, value):
        self._filters.append(("eq", field, value))
        return self

    def order(self, field, desc=False):
        self._order_by = field
        self._order_desc = desc
        return self

    def single(self):
        self._single = True
        return self

    def execute(self):
        result = list(self._data)
        for op, field, value in self._filters:
            result = [r for r in result if r.get(field) == value]
        if self._single:
            result = result[0] if result else None
        return MagicMock(data=result)

    def insert(self, record):
        import uuid
        from datetime import datetime, timezone
        record["id"] = str(uuid.uuid4())
        record.setdefault("created_at", datetime.now(timezone.utc).isoformat())
        record.setdefault("updated_at", datetime.now(timezone.utc).isoformat())
        self._data.append(record)
        self._insert_record = record
        return self

    def update(self, updates):
        self._updates = updates
        return self

    def delete(self):
        self._delete = True
        return self


class MockSupabaseTable:
    def __init__(self, name: str, store: dict):
        self._name = name
        self._store = store
        if name not in store:
            store[name] = []

    def select(self, *args):
        return MockQueryBuilder(self._store[self._name])

    def insert(self, record):
        q = MockQueryBuilder(self._store[self._name])
        return q.insert(record)

    def update(self, updates):
        q = MockQueryBuilder(self._store[self._name])
        # Apply update to matching records
        for op, field, value in q._filters:
            pass
        return MockUpdateBuilder(self._store[self._name], updates, q._filters)

    def delete(self):
        return MockDeleteBuilder(self._store[self._name])


class MockUpdateBuilder:
    def __init__(self, data, updates, filters):
        self._data = data
        self._updates = updates
        self._filters = list(filters)

    def eq(self, field, value):
        self._filters.append(("eq", field, value))
        return self

    def execute(self):
        updated = None
        for record in self._data:
            match = True
            for op, f, v in self._filters:
                if record.get(f) != v:
                    match = False
                    break
            if match:
                record.update(self._updates)
                updated = record
                break
        return MagicMock(data=[updated] if updated else [])


class MockDeleteBuilder:
    def __init__(self, data):
        self._data = data
        self._filters = []

    def eq(self, field, value):
        self._filters.append((field, value))
        return self

    def execute(self):
        to_remove = []
        for record in self._data:
            match = True
            for f, v in self._filters:
                if record.get(f) != v:
                    match = False
                    break
            if match:
                to_remove.append(record)
        for r in to_remove:
            self._data.remove(r)
        return MagicMock(data=to_remove)


class MockSupabaseClient:
    def __init__(self):
        self._store = {}  # table_name -> [records]
        self.auth = MockSupabaseAuth()
        self.auth.admin = MockAdminAuth(self.auth)

    def table(self, name):
        return MockSupabaseTable(name, self._store)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def mock_supabase():
    """Retorna um MockSupabaseClient que pode ser injetado no main.py."""
    return MockSupabaseClient()


@pytest.fixture
def client(mock_supabase):
    """Client HTTP do FastAPI com Supabase mockado."""
    with patch("main.supabase", mock_supabase):
        from main import app
        with TestClient(app) as c:
            yield c


@pytest.fixture
def registered_user(client, mock_supabase):
    """Cria um usuário e retorna os dados de auth."""
    email = "user@test.com"
    password = "secret123"
    resp = client.post("/api/auth/signup", json={"email": email, "password": password})
    assert resp.status_code == 200
    data = resp.json()
    return {
        "email": email,
        "password": password,
        "access_token": data["access_token"],
        "user_id": data["user_id"],
    }


@pytest.fixture
def auth_headers(registered_user):
    """Headers de autenticação para requisições autenticadas."""
    return {"Authorization": f"Bearer {registered_user['access_token']}"}
