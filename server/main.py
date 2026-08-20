from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from supabase import create_client, Client
from pydantic import BaseModel, field_validator
from enum import Enum
import os

load_dotenv()

app = FastAPI(title="Task Manager API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Supabase
# ---------------------------------------------------------------------------
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# A inicialização condicional permite importar a aplicação e executar os testes
# mesmo sem credenciais reais. Em execução normal, endpoints que dependem do
# Supabase retornam uma mensagem clara quando a configuração está ausente.
supabase: Client | None = (
    create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    if SUPABASE_URL and SUPABASE_SERVICE_KEY
    else None
)


def get_supabase() -> Client:
    if supabase is None:
        raise HTTPException(
            status_code=503,
            detail="Supabase não configurado. Preencha SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY.",
        )
    return supabase


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
def get_current_user(request: Request):
    client = get_supabase()
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token ausente")
    token = auth.split(" ")[1]
    try:
        resp = client.auth.get_user(token)
        if resp and resp.user:
            return resp.user
    except Exception:
        pass
    raise HTTPException(status_code=401, detail="Token inválido ou expirado")


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class PriorityEnum(str, Enum):
    baixa = "baixa"
    media = "media"
    alta = "alta"


class StatusEnum(str, Enum):
    pendente = "pendente"
    em_andamento = "em_andamento"
    concluida = "concluida"


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class AuthRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    user_id: str
    email: str | None = None


class TaskCreate(BaseModel):
    title: str
    description: str = ""
    due_date: str | None = None
    priority: PriorityEnum = PriorityEnum.media
    status: StatusEnum = StatusEnum.pendente

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("O título da tarefa é obrigatório")
        if len(value) > 200:
            raise ValueError("O título deve ter no máximo 200 caracteres")
        return value


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    due_date: str | None = None
    priority: PriorityEnum | None = None
    status: StatusEnum | None = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("O título da tarefa é obrigatório")
        if len(value) > 200:
            raise ValueError("O título deve ter no máximo 200 caracteres")
        return value


# ===========================================================================
# AUTH
# ===========================================================================

@app.post("/api/auth/signup", response_model=AuthResponse)
def signup(body: AuthRequest):
    client = get_supabase()
    try:
        client.auth.admin.create_user({
            "email": body.email,
            "password": body.password,
            "email_confirm": True,
        })
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        result = client.auth.sign_in_with_password(
            {"email": body.email, "password": body.password}
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    if result.session is None:
        raise HTTPException(status_code=400, detail="Falha no login após cadastro")

    return AuthResponse(
        access_token=result.session.access_token,
        refresh_token=result.session.refresh_token,
        user_id=result.user.id,
        email=result.user.email,
    )


@app.post("/api/auth/login", response_model=AuthResponse)
def login(body: AuthRequest):
    client = get_supabase()
    try:
        result = client.auth.sign_in_with_password(
            {"email": body.email, "password": body.password}
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    if result.session is None:
        raise HTTPException(status_code=400, detail="Falha no login")

    return AuthResponse(
        access_token=result.session.access_token,
        refresh_token=result.session.refresh_token,
        user_id=result.user.id,
        email=result.user.email,
    )


@app.post("/api/auth/logout")
def logout(user=Depends(get_current_user)):
    get_supabase().auth.admin.sign_out(user.id)
    return {"status": "ok"}


@app.get("/api/auth/me")
def me(user=Depends(get_current_user)):
    return {"id": user.id, "email": user.email}


# ===========================================================================
# TASKS
# ===========================================================================

@app.get("/api/tasks")
def list_tasks(user=Depends(get_current_user)):
    result = (
        get_supabase().table("tasks")
        .select("*")
        .eq("user_id", user.id)
        .order("created_at", desc=True)
        .execute()
    )
    return result.data


@app.post("/api/tasks", status_code=201)
def create_task(body: TaskCreate, user=Depends(get_current_user)):
    result = (
        get_supabase().table("tasks")
        .insert({
            "user_id": user.id,
            "title": body.title,
            "description": body.description,
            "due_date": body.due_date,
            "priority": body.priority.value,
            "status": body.status.value,
        })
        .execute()
    )
    return result.data[0] if result.data else {}


@app.put("/api/tasks/{task_id}")
def update_task(task_id: str, body: TaskUpdate, user=Depends(get_current_user)):
    data = body.model_dump()
    payload = {
        key: value
        for key, value in data.items()
        if key in body.model_fields_set and (value is not None or key == "due_date")
    }
    if not payload:
        raise HTTPException(status_code=400, detail="Nada para atualizar")

    # Converte enum para valor string
    if "priority" in payload and hasattr(payload["priority"], "value"):
        payload["priority"] = payload["priority"].value
    if "status" in payload and hasattr(payload["status"], "value"):
        payload["status"] = payload["status"].value

    result = (
        get_supabase().table("tasks")
        .update(payload)
        .eq("id", task_id)
        .eq("user_id", user.id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    return result.data[0]


@app.delete("/api/tasks/{task_id}", status_code=204)
def delete_task(task_id: str, user=Depends(get_current_user)):
    result = (
        get_supabase().table("tasks")
        .delete()
        .eq("id", task_id)
        .eq("user_id", user.id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
