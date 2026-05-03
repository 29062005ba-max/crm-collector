"use client";
import { useEffect, useState, Suspense, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import AppShell from "@/components/layout/AppShell";
import { apiClient } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import toast from "react-hot-toast";
import {
  Plus, Search, Filter, X, Check, Clock, AlertCircle, ListChecks,
  Phone, Calendar as CalendarIcon, FileText, Eye, DollarSign,
  ChevronRight, Trash2, Edit3, ArrowRight, User as UserIcon, RefreshCw,
} from "lucide-react";
import TaskFormModal from "@/components/forms/TaskFormModal";

// === Maps ===
const STATUS_LABELS: Record<string, { label: string; color: string; dot: string }> = {
  new:         { label: "Новая",         color: "bg-blue-50 text-blue-700",       dot: "bg-blue-500" },
  open:        { label: "Новая",         color: "bg-blue-50 text-blue-700",       dot: "bg-blue-500" },
  in_progress: { label: "В работе",      color: "bg-amber-50 text-amber-700",     dot: "bg-amber-500" },
  on_review:   { label: "На проверке",   color: "bg-purple-50 text-purple-700",   dot: "bg-purple-500" },
  done:        { label: "Выполнена",     color: "bg-emerald-50 text-emerald-700", dot: "bg-emerald-500" },
  cancelled:   { label: "Отменена",      color: "bg-gray-100 text-gray-600",      dot: "bg-gray-400" },
};

const PRIORITY_MAP: Record<string, { label: string; bar: string; chip: string }> = {
  urgent: { label: "Срочный",  bar: "bg-red-500",    chip: "bg-red-50 text-red-700 border-red-200" },
  high:   { label: "Высокий",  bar: "bg-orange-500", chip: "bg-orange-50 text-orange-700 border-orange-200" },
  medium: { label: "Средний",  bar: "bg-yellow-400", chip: "bg-yellow-50 text-yellow-700 border-yellow-200" },
  normal: { label: "Средний",  bar: "bg-yellow-400", chip: "bg-yellow-50 text-yellow-700 border-yellow-200" },
  low:    { label: "Низкий",   bar: "bg-gray-300",   chip: "bg-gray-50 text-gray-600 border-gray-200" },
};

const TYPE_ICONS: Record<string, any> = {
  call:            Phone,
  meeting:         UserIcon,
  document:        FileText,
  review:          Eye,
  payment_control: DollarSign,
  followup:        ListChecks,
  other:           ListChecks,
};

const TYPE_LABELS: Record<string, string> = {
  call:            "Звонок",
  meeting:         "Встреча",
  document:        "Документ",
  review:          "Проверка",
  payment_control: "Контроль платежа",
  followup:        "Follow-up",
  other:           "Другое",
};

interface Task {
  id: number;
  title: string;
  description?: string;
  type: string;
  status: string;
  raw_status?: string;
  priority: string;
  due_date?: string;
  completed_at?: string;
  created_at: string;
  assignee_id?: number;
  assignee_name?: string;
  created_by_id?: number;
  debtor_id?: number;
  debtor_name?: string;
  contract_id?: number;
}

interface Stats {
  total: number;
  by_status: Record<string, number>;
  by_priority: Record<string, number>;
  overdue: number;
  due_today: number;
  completed_today: number;
}

function TasksContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user } = useAuth();
  const isAdmin = ["ADMIN", "HEAD"].includes((user?.role || "").toUpperCase());

  const initialStatus = searchParams?.get("status") || "";

  // State
  const [scope, setScope] = useState<"my" | "created" | "all">("my");
  const [items, setItems] = useState<Task[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>(initialStatus);
  const [priorityFilter, setPriorityFilter] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState("");
  const [sortBy, setSortBy] = useState("due_date");
  const [showCreate, setShowCreate] = useState(false);
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [editingTask, setEditingTask] = useState<Task | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params: any = { scope, sort_by: sortBy, per_page: 100 };
      if (statusFilter) params.status = statusFilter;
      if (priorityFilter) params.priority = priorityFilter;
      if (searchQuery) params.search = searchQuery;
      const [tasksRes, statsRes] = await Promise.all([
        apiClient.get("/tasks", { params }),
        apiClient.get("/tasks/stats", { params: { scope: scope === "created" ? "my" : scope } }),
      ]);
      setItems(tasksRes.data.items || []);
      setStats(statsRes.data);
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Не удалось загрузить задачи");
    } finally {
      setLoading(false);
    }
  }, [scope, statusFilter, priorityFilter, searchQuery, sortBy]);

  useEffect(() => { load(); }, [load]);

  const handleQuickStatus = async (taskId: number, newStatus: string) => {
    try {
      await apiClient.patch(`/tasks/${taskId}/status`, { status: newStatus });
      toast.success("Статус изменён");
      setSelectedTask(null);
      load();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Не удалось изменить статус");
    }
  };

  const handleDelete = async (taskId: number) => {
    if (!confirm("Удалить задачу?")) return;
    try {
      await apiClient.delete(`/tasks/${taskId}`);
      toast.success("Удалено");
      setSelectedTask(null);
      load();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Не удалось удалить");
    }
  };

  const updateStatusFilter = (s: string) => {
    setStatusFilter(s);
    const url = new URL(window.location.href);
    if (s) url.searchParams.set("status", s); else url.searchParams.delete("status");
    window.history.replaceState({}, "", url.toString());
  };

  const isOverdue = (t: Task) => {
    if (!t.due_date) return false;
    if (["done", "cancelled"].includes(t.status)) return false;
    return new Date(t.due_date) < new Date();
  };

  const isDueToday = (t: Task) => {
    if (!t.due_date) return false;
    const d = new Date(t.due_date);
    const today = new Date();
    return d.toDateString() === today.toDateString();
  };

  // Подсчёт активных по статусам для чипсов (из stats — все задачи в scope)
  const cntStatus = (s: string) => stats?.by_status?.[s] ?? 0;

  return (
    <AppShell>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-gray-900">Задачи</h1>
            <p className="mt-1 text-sm text-gray-500">
              Управление и контроль задач
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={load}
              className="flex h-10 w-10 items-center justify-center rounded-full border border-gray-200 bg-white text-gray-600 shadow-soft hover:bg-gray-50 transition"
              title="Обновить"
            >
              <RefreshCw size={16} />
            </button>
            <button
              onClick={() => { setEditingTask(null); setShowCreate(true); }}
              className="flex items-center gap-2 rounded-full bg-primary-500 px-5 py-2.5 text-sm font-semibold text-white shadow-soft hover:bg-primary-600 transition-all hover:-translate-y-0.5"
            >
              <Plus size={16} /> Новая задача
            </button>
          </div>
        </div>

        {/* KPI карточки */}
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <KpiCard label="Всего" value={stats?.total ?? 0} color="blue" />
          <KpiCard label="В работе" value={cntStatus("in_progress")} color="amber" />
          <KpiCard label="Просрочено" value={stats?.overdue ?? 0} color="red" alert={Boolean(stats?.overdue)} />
          <KpiCard label="Сегодня" value={stats?.due_today ?? 0} color="purple" />
        </div>

        {/* Tabs */}
        <div className="flex items-center gap-2 rounded-2xl bg-gray-100 p-1 w-fit">
          <TabButton active={scope === "my"} onClick={() => setScope("my")} label="Мои задачи" />
          <TabButton active={scope === "created"} onClick={() => setScope("created")} label="Созданные мной" />
          {isAdmin && <TabButton active={scope === "all"} onClick={() => setScope("all")} label="Все задачи" />}
        </div>

        {/* Filters */}
        <div className="rounded-3xl bg-white p-5 shadow-card space-y-4">
          {/* Search */}
          <div className="relative">
            <Search size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Поиск по названию..."
              className="w-full rounded-full border border-gray-200 bg-gray-50 pl-11 pr-4 py-2.5 text-sm focus:bg-white focus:border-primary-300 focus:outline-none focus:ring-4 focus:ring-primary-100"
            />
          </div>

          {/* Status chips */}
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-semibold uppercase text-gray-400 mr-1">Статус:</span>
            <Chip active={statusFilter === ""} onClick={() => updateStatusFilter("")} label={`Все ${stats?.total ? `(${stats.total})` : ""}`} />
            {["new", "in_progress", "on_review", "done", "cancelled"].map((s) => (
              <Chip
                key={s}
                active={statusFilter === s}
                onClick={() => updateStatusFilter(statusFilter === s ? "" : s)}
                label={`${STATUS_LABELS[s].label} ${cntStatus(s) ? `(${cntStatus(s)})` : ""}`}
                dot={STATUS_LABELS[s].dot}
              />
            ))}
          </div>

          {/* Priority chips */}
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-semibold uppercase text-gray-400 mr-1">Приоритет:</span>
            <Chip active={priorityFilter === ""} onClick={() => setPriorityFilter("")} label="Любой" />
            {["urgent", "high", "medium", "low"].map((p) => (
              <Chip
                key={p}
                active={priorityFilter === p}
                onClick={() => setPriorityFilter(priorityFilter === p ? "" : p)}
                label={PRIORITY_MAP[p].label}
                dot={PRIORITY_MAP[p].bar}
              />
            ))}
          </div>

          {/* Sort */}
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold uppercase text-gray-400">Сортировка:</span>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="rounded-full border border-gray-200 bg-white px-4 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary-200"
            >
              <option value="due_date">По дедлайну</option>
              <option value="priority">По приоритету</option>
              <option value="created_at">По дате создания</option>
              <option value="status">По статусу</option>
            </select>
          </div>
        </div>

        {/* Tasks list */}
        <div className="space-y-3">
          {loading ? (
            <div className="rounded-3xl bg-white p-12 text-center shadow-card">
              <div className="h-8 w-8 mx-auto animate-spin rounded-full border-[3px] border-gray-200 border-t-primary-500" />
            </div>
          ) : items.length === 0 ? (
            <div className="rounded-3xl bg-white p-16 text-center shadow-card">
              <ListChecks size={48} className="mx-auto mb-3 text-gray-300" />
              <p className="text-gray-500 font-medium">Задач не найдено</p>
              <p className="text-xs text-gray-400 mt-1">Попробуйте изменить фильтры или создайте новую</p>
            </div>
          ) : (
            items.map((task) => {
              const TypeIcon = TYPE_ICONS[task.type] || ListChecks;
              const overdue = isOverdue(task);
              const dueToday = isDueToday(task);
              const prio = PRIORITY_MAP[task.priority] || PRIORITY_MAP.medium;
              const status = STATUS_LABELS[task.status] || STATUS_LABELS.new;

              return (
                <div
                  key={task.id}
                  onClick={() => setSelectedTask(task)}
                  className="group relative flex items-center gap-4 rounded-3xl bg-white p-5 shadow-card cursor-pointer transition-all hover:shadow-lifted hover:-translate-y-0.5"
                >
                  {/* Priority bar */}
                  <div className={`absolute left-0 top-4 bottom-4 w-1.5 rounded-r-full ${prio.bar}`} />

                  {/* Type icon */}
                  <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gray-50 text-gray-600 shrink-0">
                    <TypeIcon size={20} />
                  </div>

                  {/* Main */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="font-semibold text-gray-900 truncate">{task.title}</h3>
                      {overdue && (
                        <span className="flex items-center gap-1 rounded-full bg-red-50 px-2 py-0.5 text-xs font-bold text-red-600">
                          <AlertCircle size={10} /> Просрочена
                        </span>
                      )}
                      {dueToday && !overdue && (
                        <span className="flex items-center gap-1 rounded-full bg-amber-50 px-2 py-0.5 text-xs font-bold text-amber-700">
                          <Clock size={10} /> Сегодня
                        </span>
                      )}
                    </div>

                    <div className="flex flex-wrap items-center gap-3 text-xs text-gray-500">
                      <span className="flex items-center gap-1">
                        <span className={`h-2 w-2 rounded-full ${status.dot}`} />
                        {status.label}
                      </span>
                      <span>{TYPE_LABELS[task.type] || task.type}</span>
                      {task.assignee_name && (
                        <span className="flex items-center gap-1">
                          <UserIcon size={11} /> {task.assignee_name}
                        </span>
                      )}
                      {task.due_date && (
                        <span className={overdue ? "text-red-600 font-semibold" : ""}>
                          📅 {new Date(task.due_date).toLocaleDateString("ru-RU", { day: "2-digit", month: "short" })}
                        </span>
                      )}
                      {task.debtor_name && (
                        <button
                          onClick={(e) => { e.stopPropagation(); router.push(`/debtors/${task.debtor_id}`); }}
                          className="flex items-center gap-1 text-primary-600 hover:underline"
                        >
                          👤 {task.debtor_name}
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Right arrow */}
                  <ChevronRight size={18} className="text-gray-300 group-hover:text-gray-500 transition shrink-0" />
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Task detail modal */}
      {selectedTask && (
        <TaskDetailModal
          task={selectedTask}
          onClose={() => setSelectedTask(null)}
          onChangeStatus={(s) => handleQuickStatus(selectedTask.id, s)}
          onEdit={() => { setEditingTask(selectedTask); setSelectedTask(null); setShowCreate(true); }}
          onDelete={() => handleDelete(selectedTask.id)}
          isAdmin={isAdmin}
          currentUserId={user?.id}
        />
      )}

      {/* Create / Edit modal */}
      {showCreate && (
        <TaskFormModal
          task={editingTask}
          onClose={() => { setShowCreate(false); setEditingTask(null); }}
          onSaved={() => { setShowCreate(false); setEditingTask(null); load(); }}
        />
      )}
    </AppShell>
  );
}

// === Sub-components ===

function KpiCard({ label, value, color, alert }: { label: string; value: number; color: string; alert?: boolean }) {
  const bg: Record<string, string> = {
    blue:   "from-blue-50 to-blue-100/30",
    amber:  "from-amber-50 to-amber-100/30",
    red:    "from-red-50 to-red-100/30",
    purple: "from-purple-50 to-purple-100/30",
  };
  return (
    <div className={`rounded-3xl bg-gradient-to-br ${bg[color]} bg-white p-5 shadow-card`}>
      <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">{label}</p>
      <p className={`mt-2 text-3xl font-bold tracking-tight ${alert ? "text-red-600" : "text-gray-900"}`}>{value}</p>
    </div>
  );
}

function TabButton({ active, onClick, label }: { active: boolean; onClick: () => void; label: string }) {
  return (
    <button
      onClick={onClick}
      className={
        active
          ? "rounded-xl bg-white px-4 py-2 text-sm font-semibold text-gray-900 shadow-soft transition"
          : "rounded-xl px-4 py-2 text-sm font-medium text-gray-600 hover:text-gray-900 transition"
      }
    >
      {label}
    </button>
  );
}

function Chip({ active, onClick, label, dot }: { active: boolean; onClick: () => void; label: string; dot?: string }) {
  return (
    <button
      onClick={onClick}
      className={
        active
          ? "flex items-center gap-1.5 rounded-full bg-primary-500 px-3 py-1.5 text-xs font-semibold text-white shadow-soft transition"
          : "flex items-center gap-1.5 rounded-full border border-gray-200 bg-white px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50 transition"
      }
    >
      {dot && <span className={`h-2 w-2 rounded-full ${dot}`} />}
      {label}
    </button>
  );
}

function TaskDetailModal({
  task, onClose, onChangeStatus, onEdit, onDelete, isAdmin, currentUserId,
}: {
  task: Task;
  onClose: () => void;
  onChangeStatus: (s: string) => void;
  onEdit: () => void;
  onDelete: () => void;
  isAdmin: boolean;
  currentUserId?: number;
}) {
  const TypeIcon = TYPE_ICONS[task.type] || ListChecks;
  const status = STATUS_LABELS[task.status] || STATUS_LABELS.new;
  const prio = PRIORITY_MAP[task.priority] || PRIORITY_MAP.medium;
  const canEdit = isAdmin || task.assignee_id === currentUserId || task.created_by_id === currentUserId;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 animate-fade-in">
      <div className="absolute inset-0 bg-gray-900/40 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-2xl rounded-3xl bg-white shadow-modal animate-scale-in">
        {/* Header */}
        <div className="flex items-start justify-between gap-4 border-b border-gray-100 px-6 py-5">
          <div className="flex items-start gap-3 flex-1 min-w-0">
            <div className={`flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br ${prio.bar.replace("bg-", "from-").replace("-500", "-100")} to-white shrink-0`}>
              <TypeIcon size={20} className="text-gray-700" />
            </div>
            <div className="min-w-0">
              <h3 className="text-xl font-bold tracking-tight text-gray-900 mb-1">{task.title}</h3>
              <div className="flex items-center gap-2 flex-wrap">
                <span className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold ${status.color}`}>
                  <span className={`h-2 w-2 rounded-full ${status.dot}`} />
                  {status.label}
                </span>
                <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${prio.chip}`}>
                  {prio.label}
                </span>
                <span className="rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-600">
                  {TYPE_LABELS[task.type] || task.type}
                </span>
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            className="flex h-9 w-9 items-center justify-center rounded-full text-gray-400 hover:bg-gray-100 hover:text-gray-700 shrink-0"
          >
            <X size={18} />
          </button>
        </div>

        {/* Body */}
        <div className="px-6 py-5 space-y-4 max-h-[60vh] overflow-y-auto">
          {task.description && (
            <div>
              <p className="text-xs font-semibold uppercase text-gray-400 mb-1">Описание</p>
              <p className="text-sm text-gray-700 whitespace-pre-wrap">{task.description}</p>
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            {task.due_date && (
              <div>
                <p className="text-xs font-semibold uppercase text-gray-400 mb-1">Дедлайн</p>
                <p className="text-sm font-medium text-gray-900">
                  {new Date(task.due_date).toLocaleString("ru-RU", { dateStyle: "short", timeStyle: "short" })}
                </p>
              </div>
            )}
            {task.assignee_name && (
              <div>
                <p className="text-xs font-semibold uppercase text-gray-400 mb-1">Исполнитель</p>
                <p className="text-sm font-medium text-gray-900">{task.assignee_name}</p>
              </div>
            )}
            {task.debtor_name && (
              <div className="col-span-2">
                <p className="text-xs font-semibold uppercase text-gray-400 mb-1">Должник</p>
                <a
                  href={`/debtors/${task.debtor_id}`}
                  className="text-sm font-medium text-primary-600 hover:underline"
                >
                  {task.debtor_name} →
                </a>
              </div>
            )}
            {task.completed_at && (
              <div>
                <p className="text-xs font-semibold uppercase text-gray-400 mb-1">Завершена</p>
                <p className="text-sm font-medium text-gray-900">
                  {new Date(task.completed_at).toLocaleString("ru-RU", { dateStyle: "short", timeStyle: "short" })}
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Quick status buttons */}
        {canEdit && (
          <div className="border-t border-gray-100 px-6 py-4">
            <p className="text-xs font-semibold uppercase text-gray-400 mb-3">Изменить статус</p>
            <div className="flex flex-wrap gap-2">
              {task.status !== "in_progress" && (
                <button onClick={() => onChangeStatus("in_progress")} className="flex items-center gap-1.5 rounded-full bg-amber-100 px-4 py-2 text-sm font-semibold text-amber-700 hover:bg-amber-200 transition">
                  <ArrowRight size={14} /> Взять в работу
                </button>
              )}
              {task.status !== "on_review" && (
                <button onClick={() => onChangeStatus("on_review")} className="flex items-center gap-1.5 rounded-full bg-purple-100 px-4 py-2 text-sm font-semibold text-purple-700 hover:bg-purple-200 transition">
                  <Eye size={14} /> На проверку
                </button>
              )}
              {task.status !== "done" && (
                <button onClick={() => onChangeStatus("done")} className="flex items-center gap-1.5 rounded-full bg-emerald-100 px-4 py-2 text-sm font-semibold text-emerald-700 hover:bg-emerald-200 transition">
                  <Check size={14} /> Завершить
                </button>
              )}
              {task.status !== "cancelled" && (
                <button onClick={() => onChangeStatus("cancelled")} className="flex items-center gap-1.5 rounded-full bg-gray-100 px-4 py-2 text-sm font-semibold text-gray-600 hover:bg-gray-200 transition">
                  <X size={14} /> Отменить
                </button>
              )}
            </div>
          </div>
        )}

        {/* Footer actions */}
        {canEdit && (
          <div className="flex items-center justify-between border-t border-gray-100 px-6 py-4">
            <button
              onClick={onDelete}
              className="flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium text-red-600 hover:bg-red-50 transition"
            >
              <Trash2 size={14} /> Удалить
            </button>
            <button
              onClick={onEdit}
              className="flex items-center gap-2 rounded-full border border-gray-200 bg-white px-5 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-50 shadow-soft transition"
            >
              <Edit3 size={14} /> Редактировать
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

// Default export with Suspense wrapper
export default function TasksPage() {
  return (
    <Suspense fallback={<div className="p-12 text-center text-gray-400">Загрузка...</div>}>
      <TasksContent />
    </Suspense>
  );
}
