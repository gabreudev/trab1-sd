const API = "http://localhost:8000/api";

// ---------------------------------------------------------------------------
// Token storage
// ---------------------------------------------------------------------------
function getToken(): string {
  return localStorage.getItem("app_access_token") ?? "";
}

export function setTokens(access: string, refresh: string) {
  localStorage.setItem("app_access_token", access);
  localStorage.setItem("app_refresh_token", refresh);
}

export function clearTokens() {
  localStorage.removeItem("app_access_token");
  localStorage.removeItem("app_refresh_token");
}

// ---------------------------------------------------------------------------
// Request helper
// ---------------------------------------------------------------------------
async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };

  const token = getToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  if (options.body && typeof options.body === "string") {
    headers["Content-Type"] = "application/json";
  }

  const res = await fetch(`${API}${path}`, { ...options, headers });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Erro desconhecido" }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

// ---------------------------------------------------------------------------
// Auth API
// ---------------------------------------------------------------------------
export async function signUp(email: string, password: string) {
  const data = await request<{
    access_token: string;
    refresh_token: string;
    user_id: string;
    email: string;
  }>("/auth/signup", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });

  setTokens(data.access_token, data.refresh_token);
  return data;
}

export async function signIn(email: string, password: string) {
  const data = await request<{
    access_token: string;
    refresh_token: string;
    user_id: string;
    email: string;
  }>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });

  setTokens(data.access_token, data.refresh_token);
  return data;
}

export async function signOut() {
  try {
    await request("/auth/logout", { method: "POST" });
  } finally {
    clearTokens();
  }
}

export async function getMe() {
  return request<{ id: string; email: string }>("/auth/me");
}

// ---------------------------------------------------------------------------
// Tasks API
// ---------------------------------------------------------------------------
export type Priority = "baixa" | "media" | "alta";
export type Status = "pendente" | "em_andamento" | "concluida";

export interface Task {
  id: string;
  user_id: string;
  title: string;
  description: string;
  due_date: string | null;
  priority: Priority;
  status: Status;
  created_at: string;
  updated_at: string;
}

export interface TaskInput {
  title: string;
  description?: string;
  due_date?: string | null;
  priority?: Priority;
  status?: Status;
}

export async function listTasks(): Promise<Task[]> {
  return request<Task[]>("/tasks");
}

export async function createTask(input: TaskInput): Promise<Task> {
  return request<Task>("/tasks", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function updateTask(
  id: string,
  input: Partial<TaskInput>
): Promise<Task> {
  return request<Task>(`/tasks/${id}`, {
    method: "PUT",
    body: JSON.stringify(input),
  });
}

export async function deleteTask(id: string): Promise<void> {
  await request(`/tasks/${id}`, { method: "DELETE" });
}
