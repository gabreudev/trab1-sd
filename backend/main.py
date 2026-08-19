from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from supabase import create_client, Client
from pydantic import BaseModel
from enum import Enum
import os

load_dotenv()

app = FastAPI(title="Task Manager API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Supabase
# ---------------------------------------------------------------------------
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
def get_current_user(request: Request):
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token ausente")
    token = auth.split(" ")[1]
    try:
        resp = supabase.auth.get_user(token)
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


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    due_date: str | None = None
    priority: PriorityEnum | None = None
    status: StatusEnum | None = None


# ===========================================================================
# AUTH
# ===========================================================================

@app.post("/api/auth/signup", response_model=AuthResponse)
def signup(body: AuthRequest):
    try:
        supabase.auth.admin.create_user({
            "email": body.email,
            "password": body.password,
            "email_confirm": True,
        })
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        result = supabase.auth.sign_in_with_password(
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
    try:
        result = supabase.auth.sign_in_with_password(
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
    supabase.auth.admin.sign_out(user.id)
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
        supabase.table("tasks")
        .select("*")
        .eq("user_id", user.id)
        .order("created_at", desc=True)
        .execute()
    )
    return result.data


@app.post("/api/tasks", status_code=201)
def create_task(body: TaskCreate, user=Depends(get_current_user)):
    result = (
        supabase.table("tasks")
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
    payload = {k: v for k, v in body.model_dump().items() if v is not None}
    if not payload:
        raise HTTPException(status_code=400, detail="Nada para atualizar")

    # Converte enum para valor string
    if "priority" in payload and hasattr(payload["priority"], "value"):
        payload["priority"] = payload["priority"].value
    if "status" in payload and hasattr(payload["status"], "value"):
        payload["status"] = payload["status"].value

    result = (
        supabase.table("tasks")
        .update(payload)
        .eq("id", task_id)
        .eq("user_id", user.id)
        .execute()
    )
    return result.data[0] if result.data else {}


@app.delete("/api/tasks/{task_id}", status_code=204)
def delete_task(task_id: str, user=Depends(get_current_user)):
    supabase.table("tasks").delete().eq("id", task_id).eq("user_id", user.id).execute()
