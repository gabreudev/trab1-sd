import { useState } from "react";
import type * as api from "../lib/api";

interface TaskFormProps {
  initialData?: Partial<api.Task>;
  onSubmit: (data: api.TaskInput) => Promise<void>;
  onCancel: () => void;
  submitLabel: string;
}

export default function TaskForm({
  initialData,
  onSubmit,
  onCancel,
  submitLabel,
}: TaskFormProps) {
  const [title, setTitle] = useState(initialData?.title ?? "");
  const [description, setDescription] = useState(initialData?.description ?? "");
  const [dueDate, setDueDate] = useState(initialData?.due_date ?? "");
  const [priority, setPriority] = useState<api.Priority>(initialData?.priority ?? "media");
  const [status, setStatus] = useState<api.Status>(initialData?.status ?? "pendente");
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await onSubmit({
        title,
        description,
        due_date: dueDate || null,
        priority,
        status,
      });
    } finally {
      setSaving(false);
    }
  };

  return (
    <form className="task-form" onSubmit={handleSubmit}>
      <div className="form-group">
        <label>Título *</label>
        <input
          type="text"
          placeholder="Ex: Estudar para prova"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          required
          autoFocus
        />
      </div>

      <div className="form-group">
        <label>Descrição</label>
        <textarea
          placeholder="Detalhes da tarefa..."
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={3}
        />
      </div>

      <div className="form-grid">
        <div className="form-group">
          <label>Data limite</label>
          <input
            type="date"
            value={dueDate}
            onChange={(e) => setDueDate(e.target.value)}
          />
        </div>

        <div className="form-group">
          <label>Prioridade</label>
          <div className="priority-options">
            {(["baixa", "media", "alta"] as const).map((p) => (
              <button
                key={p}
                type="button"
                className={`priority-btn priority-btn-${p} ${priority === p ? "active" : ""}`}
                onClick={() => setPriority(p)}
              >
                {p === "baixa" ? "Baixa" : p === "media" ? "Média" : "Alta"}
              </button>
            ))}
          </div>
        </div>

        <div className="form-group">
          <label>Status</label>
          <div className="status-options">
            {(["pendente", "em_andamento", "concluida"] as const).map((s) => (
              <button
                key={s}
                type="button"
                className={`status-btn status-btn-${s} ${status === s ? "active" : ""}`}
                onClick={() => setStatus(s)}
              >
                {s === "pendente"
                  ? "Pendente"
                  : s === "em_andamento"
                  ? "Em andamento"
                  : "Concluída"}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="form-actions">
        <button type="button" className="btn-secondary" onClick={onCancel}>
          Cancelar
        </button>
        <button type="submit" className="btn-primary" disabled={saving}>
          {saving ? "Salvando..." : submitLabel}
        </button>
      </div>
    </form>
  );
}
