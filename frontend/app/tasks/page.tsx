"use client";
import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import AppShell from "@/components/layout/AppShell";
import { apiClient } from "@/lib/api-client";
import toast from "react-hot-toast";
import { Spinner } from "@/components/ui";
import { useAuth } from "@/lib/auth-context";
import { CheckCircle2, Circle, Clock, AlertTriangle, Trash2 } from "lucide-react";

interface Task {
  id: number;
  title: string;
  description: string | null;
  type: string;
  status: string;
  priority: string;
  due_date: string | null;
  debtor_id: number | null;
  contract_id: number | null;
  debtor_name: string | null;
  contract_number: string | null;
  assignee_name: string | null;
  completed_at: string | null;
  created_at: string;
}

const PRIORITY_COLORS: Record<string, string> = {
  low: "bg-gray-100 text-gray-600",
  normal: "bg-blue-100 text-blue-700",
  high: "bg-orange-100 text-orange-700",
  urgent: "bg-red-100 text-red-700",
};
const PRIORITY_LABELS: Record<string, string> = {
  low: "Низкий", normal: "Обычный", high: "Высокий", urgent: "СРОЧНО",
};
const STATUS_LABELS: Record<string, string> = {
  open: "Открыта", in_progress: "В работе", done: "Выполнена", cancelled: "Отменена",
};
const TYPE_LABELS: Record<string, string> = {
  followup: "Повторный контакт", call: "Звонок", visit: "Визит", document: "Документ", other: "Другое",
};

export default function TasksPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const validStatuses = new Set(["open", "in_progress", "done", "cancelled"]);
  const initialStatus = (() => {
    const v = searchParams?.get("status") || "";
    return validStatuses.has(v) ? v : "";
  })();
  const { user } = useAuth();
  const isAdmin = ["ADMIN", "HEAD"].includes((user?.role || "").toUpperCase());
  const [items, setItems] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState(initialStatus);
  const [scope, setScope] = useState<"my" | "all">("my");

  useEffect(() => { load(); }, [statusFilter, scope]);

  const load = async () => {
    try {
      setLoading(true);
      const path = scope === "all" && isAdmin ? "/tasks/all" : "/tasks/my";
      const params: any = {};
      if (statusFilter) params.status = statusFilter;
      const { data } = await apiClient.get(path, { params });
      setItems(data);
    } catch { toast.error("Ошибка загрузки"); }
    finally { setLoading(false); }
  };

  const updateStatus = async (id: number, status: string) => {
    try {
      await apiClient.patch(`/tasks/${id}`, { status });
      toast.success(status === "done" ? "Задача выполнена" : "Статус обновлён");
      load();
    } catch { toast.error("Ошибка"); }
  };

  const remove = async (id: number) => {
    if (!confirm("Удалить задачу?")) return;
    try {
      await apiClient.delete(`/tasks/${id}`);
      toast.success("Удалено");
      load();
    } catch { toast.error("Ошибка"); }
  };

  const isOverdue = (dueDate: string | null, status: string) => {
    if (!dueDate || status === "done" || status === "cancelled") return false;
    return new Date(dueDate) < new Date();
  };

  const counts = {
    open: items.filter(i => i.status === "open").length,
    in_progress: items.filter(i => i.status === "in_progress").length,
    overdue: items.filter(i => isOverdue(i.due_date, i.status)).length,
    done: items.filter(i => i.status === "done").length,
  };

  return (
    <AppShell>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Задачи</h1>
        <p className="text-sm text-gray-500 mt-1">Всего: {items.length}</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
        <div className="card p-3 text-center">
          <Circle size={20} className="mx-auto text-blue-500" />
          <p className="text-xs text-gray-500 mt-1">Открытые</p>
          <p className="text-2xl font-bold">{counts.open}</p>
        </div>
        <div className="card p-3 text-center">
          <Clock size={20} className="mx-auto text-amber-500" />
          <p className="text-xs text-gray-500 mt-1">В работе</p>
          <p className="text-2xl font-bold">{counts.in_progress}</p>
        </div>
        <div className="card p-3 text-center">
          <AlertTriangle size={20} className="mx-auto text-red-500" />
          <p className="text-xs text-gray-500 mt-1">Просроченные</p>
          <p className="text-2xl font-bold text-red-600">{counts.overdue}</p>
        </div>
        <div className="card p-3 text-center">
          <CheckCircle2 size={20} className="mx-auto text-green-500" />
          <p className="text-xs text-gray-500 mt-1">Выполнено</p>
          <p className="text-2xl font-bold text-green-600">{counts.done}</p>
        </div>
      </div>

      <div className="card mb-4 p-3">
        <div className="flex flex-wrap gap-2 items-center">
          {isAdmin && (
            <div className="flex bg-gray-100 rounded-lg p-0.5">
              <button onClick={() => setScope("my")}
                className={`px-3 py-1.5 text-xs rounded-md ${scope === "my" ? "bg-white shadow text-blue-700" : "text-gray-600"}`}>Мои</button>
              <button onClick={() => setScope("all")}
                className={`px-3 py-1.5 text-xs rounded-md ${scope === "all" ? "bg-white shadow text-blue-700" : "text-gray-600"}`}>Все</button>
            </div>
          )}
          <select value={statusFilter} onChange={(e) => {
            const v = e.target.value;
            setStatusFilter(v);
            const url = new URL(window.location.href);
            if (v) url.searchParams.set("status", v); else url.searchParams.delete("status");
            window.history.replaceState({}, "", url.toString());
          }}
            className="input h-9 text-sm w-44">
            <option value="">Все статусы</option>
            <option value="open">Открытые</option>
            <option value="in_progress">В работе</option>
            <option value="done">Выполненные</option>
            <option value="cancelled">Отменённые</option>
          </select>
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center py-20"><Spinner size="lg" /></div>
      ) : items.length === 0 ? (
        <div className="card p-12 text-center text-gray-400">
          <CheckCircle2 size={48} className="mx-auto opacity-30 mb-3" />
          <p>Задач нет</p>
        </div>
      ) : (
        <div className="space-y-2">
          {items.map(t => {
            const overdue = isOverdue(t.due_date, t.status);
            return (
              <div key={t.id}
                className={`card p-4 transition-all ${t.status === "done" ? "opacity-60" : ""} ${overdue ? "border-l-4 border-l-red-500" : ""}`}>
                <div className="flex items-start gap-3">
                  <button onClick={() => updateStatus(t.id, t.status === "done" ? "open" : "done")}
                    className="mt-1 shrink-0">
                    {t.status === "done"
                      ? <CheckCircle2 size={22} className="text-green-500" />
                      : <Circle size={22} className="text-gray-300 hover:text-blue-500 transition-colors" />}
                  </button>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-2 flex-wrap">
                      <div className="flex-1 min-w-0">
                        <p className={`font-semibold text-gray-800 ${t.status === "done" ? "line-through" : ""}`}>{t.title}</p>
                        {t.description && <p className="text-sm text-gray-500 mt-1">{t.description}</p>}
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        <span className={`text-xs px-2 py-0.5 rounded-full ${PRIORITY_COLORS[t.priority] || ""}`}>
                          {PRIORITY_LABELS[t.priority] || t.priority}
                        </span>
                        <button onClick={() => remove(t.id)}
                          className="text-gray-300 hover:text-red-500 transition-colors p-1">
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </div>
                    <div className="flex items-center gap-3 mt-2 text-xs text-gray-500 flex-wrap">
                      <span>{TYPE_LABELS[t.type] || t.type}</span>
                      {t.debtor_name && (
                        <button onClick={() => t.debtor_id && router.push(`/debtors/${t.debtor_id}`)}
                          className="text-blue-600 hover:underline">
                          👤 {t.debtor_name}
                        </button>
                      )}
                      {t.due_date && (
                        <span className={overdue ? "text-red-600 font-medium" : ""}>
                          📅 до {new Date(t.due_date).toLocaleDateString("ru-KZ")}
                          {overdue && " ⚠ ПРОСРОЧЕНО"}
                        </span>
                      )}
                      {t.assignee_name && scope === "all" && (
                        <span>→ {t.assignee_name}</span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </AppShell>
  );
}
