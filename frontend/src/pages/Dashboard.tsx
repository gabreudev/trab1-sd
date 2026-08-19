import { useEffect, useState, useMemo } from "react";
import { useAuth } from "../contexts/AuthContext";
import { useNavigate } from "react-router-dom";
import * as api from "../lib/api";
import Modal from "../components/Modal";
import TaskForm from "../components/TaskForm";

// ---------------------------------------------------------------------------
// Labels
// ---------------------------------------------------------------------------
const PRIORITY_LABELS: Record<api.Priority, string> = {
  baixa: "Baixa",
  media: "Média",
  alta: "Alta",
};

const PRIORITY_ICONS: Record<api.Priority, string> = {
  baixa: "🟢",
  media: "🟡",
  alta: "🔴",
};

const STATUS_LABELS: Record<api.Status, string> = {
  pendente: "Pendente",
  em_andamento: "Em andamento",
  concluida: "Concluída",
};

const STATUS_ICONS: Record<api.Status, string> = {
  pendente: "⏳",
  em_andamento: "🔄",
  concluida: "✅",
};

// ---------------------------------------------------------------------------
// Toast
// ---------------------------------------------------------------------------
function showToast(msg: string, type: "success" | "error" = "success") {
  const el = document.createElement("div");
  el.className = `toast toast-${type}`;
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 3000);
}

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------
export default function Dashboard() {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();

  const [tasks, setTasks] = useState<api.Task[]>([]);
  const [loading, setLoading] = useState(true);

  // Modals
  const [showCreate, setShowCreate] = useState(false);
  const [editingTask, setEditingTask] = useState<api.Task | null>(null);

  // Filters
  const [filterStatus, setFilterStatus] = useState<api.Status | "todas">("todas");
  const [filterPriority, setFilterPriority] = useState<api.Priority | "todas">("todas");
  const [searchQuery, setSearchQuery] = useState("");

  // ---------------------------------------------------------------------------
  // Fetch
  // ---------------------------------------------------------------------------
  const fetchTasks = async () => {
    try {
      const data = await api.listTasks();
      setTasks(data);
    } catch {
      await signOut();
      navigate("/login");
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchTasks();
  }, []);

  // ---------------------------------------------------------------------------
  // Filtered tasks
  // ---------------------------------------------------------------------------
  const filteredTasks = useMemo(() => {
    return tasks.filter((t) => {
      if (filterStatus !== "todas" && t.status !== filterStatus) return false;
      if (filterPriority !== "todas" && t.priority !== filterPriority) return false;
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        if (
          !t.title.toLowerCase().includes(q) &&
          !t.description.toLowerCase().includes(q)
        )
          return false;
      }
      return true;
    });
  }, [tasks, filterStatus, filterPriority, searchQuery]);

  // ---------------------------------------------------------------------------
  // Stats
  // ---------------------------------------------------------------------------
  const stats = useMemo(() => ({
    total: tasks.length,
    pendentes: tasks.filter((t) => t.status === "pendente").length,
    andamento: tasks.filter((t) => t.status === "em_andamento").length,
    concluidas: tasks.filter((t) => t.status === "concluida").length,
  }), [tasks]);

  // ---------------------------------------------------------------------------
  // CRUD
  // ---------------------------------------------------------------------------
  const handleCreate = async (data: api.TaskInput) => {
    const task = await api.createTask(data);
    setTasks((prev) => [task, ...prev]);
    setShowCreate(false);
    showToast("Tarefa criada com sucesso!");
  };

  const handleEdit = async (data: api.TaskInput) => {
    if (!editingTask) return;
    const updated = await api.updateTask(editingTask.id, data);
    setTasks((prev) => prev.map((t) => (t.id === editingTask.id ? updated : t)));
    setEditingTask(null);
    showToast("Tarefa atualizada!");
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Tem certeza que deseja excluir?")) return;
    try {
      await api.deleteTask(id);
      setTasks((prev) => prev.filter((t) => t.id !== id));
      showToast("Tarefa excluída!");
    } catch (err: any) {
      showToast(err.message, "error");
    }
  };

  const cycleStatus = async (task: api.Task) => {
    const order: api.Status[] = ["pendente", "em_andamento", "concluida"];
    const next = order[(order.indexOf(task.status) + 1) % order.length];
    try {
      const updated = await api.updateTask(task.id, { status: next });
      setTasks((prev) => prev.map((t) => (t.id === task.id ? updated : t)));
    } catch (err: any) {
      showToast(err.message, "error");
    }
  };

  const handleLogout = async () => {
    await signOut();
    navigate("/login");
  };

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------
  const isOverdue = (t: api.Task) =>
    t.due_date && t.status !== "concluida" && new Date(t.due_date) < new Date(new Date().toDateString());

  const formatDate = (d: string) =>
    new Date(d + "T00:00:00").toLocaleDateString("pt-BR", {
      day: "2-digit",
      month: "short",
    });

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------
  return (
    <div className="dashboard">
      {/* ---- Header ---- */}
      <header className="dashboard-header">
        <div>
          <h1>📋 Gerenciador de Tarefas</h1>
          <p className="subtitle">{user?.email}</p>
        </div>
        <div className="header-actions">
          <button className="btn-primary" onClick={() => setShowCreate(true)}>
            + Nova Tarefa
          </button>
          <button className="btn-ghost" onClick={handleLogout}>
            Sair
          </button>
        </div>
      </header>

      {/* ---- Stats ---- */}
      <div className="stats-bar">
        <div className="stat">
          <span className="stat-number">{stats.total}</span>
          <span className="stat-label">Total</span>
        </div>
        <div className="stat stat-pendente">
          <span className="stat-number">{stats.pendentes}</span>
          <span className="stat-label">Pendentes</span>
        </div>
        <div className="stat stat-andamento">
          <span className="stat-number">{stats.andamento}</span>
          <span className="stat-label">Em andamento</span>
        </div>
        <div className="stat stat-concluida">
          <span className="stat-number">{stats.concluidas}</span>
          <span className="stat-label">Concluídas</span>
        </div>
      </div>

      {/* ---- Filters ---- */}
      <div className="filters-bar">
        <input
          type="text"
          className="search-input"
          placeholder="🔍 Buscar tarefas..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
        <select
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value as api.Status | "todas")}
        >
          <option value="todas">Todos os status</option>
          <option value="pendente">⏳ Pendente</option>
          <option value="em_andamento">🔄 Em andamento</option>
          <option value="concluida">✅ Concluída</option>
        </select>
        <select
          value={filterPriority}
          onChange={(e) => setFilterPriority(e.target.value as api.Priority | "todas")}
        >
          <option value="todas">Todas prioridades</option>
          <option value="alta">🔴 Alta</option>
          <option value="media">🟡 Média</option>
          <option value="baixa">🟢 Baixa</option>
        </select>
      </div>

      {/* ---- Tasks ---- */}
      {loading ? (
        <div className="empty">Carregando tarefas...</div>
      ) : filteredTasks.length === 0 ? (
        <div className="empty">
          {tasks.length === 0
            ? "Nenhuma tarefa ainda. Clique em + Nova Tarefa!"
            : "Nenhuma tarefa corresponde aos filtros."}
        </div>
      ) : (
        <div className="tasks-list">
          {filteredTasks.map((task) => (
            <div
              key={task.id}
              className={`task-card priority-${task.priority} ${
                task.status === "concluida" ? "task-done" : ""
              } ${isOverdue(task) ? "task-overdue" : ""}`}
            >
              <div className="task-left">
                <button
                  className={`status-toggle status-${task.status}`}
                  onClick={() => cycleStatus(task)}
                  title="Clique para alterar status"
                >
                  {STATUS_ICONS[task.status]}
                </button>
              </div>

              <div className="task-content">
                <div className="task-top">
                  <h3 className={task.status === "concluida" ? "done-text" : ""}>
                    {task.title}
                  </h3>
                  <span className={`priority-badge priority-${task.priority}`}>
                    {PRIORITY_ICONS[task.priority]} {PRIORITY_LABELS[task.priority]}
                  </span>
                </div>

                {task.description && (
                  <p className="task-desc">{task.description}</p>
                )}

                <div className="task-footer">
                  {task.due_date && (
                    <span
                      className={`due-date ${isOverdue(task) ? "overdue" : ""}`}
                    >
                      📅 {formatDate(task.due_date)}
                    </span>
                  )}
                  <span className={`status-tag status-tag-${task.status}`}>
                    {STATUS_LABELS[task.status]}
                  </span>
                </div>
              </div>

              <div className="task-actions">
                <button
                  className="icon-btn"
                  onClick={() => setEditingTask(task)}
                  title="Editar"
                >
                  ✏️
                </button>
                <button
                  className="icon-btn icon-btn-danger"
                  onClick={() => handleDelete(task.id)}
                  title="Excluir"
                >
                  🗑️
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ---- Modal: Criar ---- */}
      <Modal open={showCreate} onClose={() => setShowCreate(false)} title="Nova Tarefa">
        <TaskForm
          onSubmit={handleCreate}
          onCancel={() => setShowCreate(false)}
          submitLabel="Criar tarefa"
        />
      </Modal>

      {/* ---- Modal: Editar ---- */}
      <Modal
        open={!!editingTask}
        onClose={() => setEditingTask(null)}
        title="Editar Tarefa"
      >
        {editingTask && (
          <TaskForm
            initialData={editingTask}
            onSubmit={handleEdit}
            onCancel={() => setEditingTask(null)}
            submitLabel="Salvar alterações"
          />
        )}
      </Modal>
    </div>
  );
}
