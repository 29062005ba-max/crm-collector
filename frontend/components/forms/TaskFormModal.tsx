"use client";
import { useEffect, useState } from "react";
import { apiClient } from "@/lib/api-client";
import toast from "react-hot-toast";
import { X, Calendar, Phone, FileText, Eye, DollarSign, ListChecks, User as UserIcon } from "lucide-react";

interface Task {
  id?: number;
  title: string;
  description?: string;
  type: string;
  status?: string;
  priority: string;
  due_date?: string;
  assignee_id?: number;
  debtor_id?: number;
  contract_id?: number;
}

const TYPE_OPTIONS = [
  { value: "call",            label: "Звонок",          icon: Phone },
  { value: "meeting",         label: "Встреча",         icon: UserIcon },
  { value: "document",        label: "Документ",        icon: FileText },
  { value: "review",          label: "Проверка",        icon: Eye },
  { value: "payment_control", label: "Контроль платежа", icon: DollarSign },
  { value: "other",           label: "Другое",          icon: ListChecks },
];

const PRIORITY_OPTIONS = [
  { value: "urgent", label: "🔴 Срочный" },
  { value: "high",   label: "🟠 Высокий" },
  { value: "medium", label: "🟡 Средний" },
  { value: "low",    label: "⚪ Низкий" },
];

export default function TaskFormModal({
  task,
  defaultDebtorId,
  onClose,
  onSaved,
}: {
  task?: Task | null;
  defaultDebtorId?: number;
  onClose: () => void;
  onSaved: () => void;
}) {
  const isEdit = Boolean(task?.id);

  const [title, setTitle] = useState(task?.title || "");
  const [description, setDescription] = useState(task?.description || "");
  const [type, setType] = useState(task?.type || "other");
  const [priority, setPriority] = useState(task?.priority || "medium");
  const [dueDate, setDueDate] = useState(
    task?.due_date ? task.due_date.slice(0, 16) : ""
  );
  const [assigneeId, setAssigneeId] = useState<number | "">(task?.assignee_id || "");
  const [debtorId, setDebtorId] = useState<number | "">(task?.debtor_id || defaultDebtorId || "");
  const [contractId, setContractId] = useState<number | "">(task?.contract_id || "");

  const [users, setUsers] = useState<any[]>([]);
  const [debtors, setDebtors] = useState<any[]>([]);
  const [contracts, setContracts] = useState<any[]>([]);
  const [debtorSearch, setDebtorSearch] = useState("");
  const [submitting, setSubmitting] = useState(false);

  // Load users (assignees)
  useEffect(() => {
    apiClient.get("/users").then(({ data }) => {
      const list = Array.isArray(data) ? data : data.items || [];
      setUsers(list.filter((u: any) => ["MANAGER", "HEAD", "ADMIN"].includes((u.role || "").toUpperCase())));
    }).catch(() => {});
  }, []);

  // Search debtors (debounced)
  useEffect(() => {
    if (!debtorSearch || debtorSearch.length < 2) { setDebtors([]); return; }
    const t = setTimeout(() => {
      apiClient.get("/debtors", { params: { search: debtorSearch, page_size: 10 } })
        .then(({ data }) => setDebtors(data.items || []))
        .catch(() => {});
    }, 300);
    return () => clearTimeout(t);
  }, [debtorSearch]);

  // Load contracts when debtor selected
  useEffect(() => {
    if (!debtorId) { setContracts([]); return; }
    apiClient.get(`/contracts/by-debtor/${debtorId}`).then(({ data }) => {
      setContracts(Array.isArray(data) ? data : (data.items || []));
    }).catch(() => setContracts([]));
  }, [debtorId]);

  const handleSubmit = async () => {
    if (!title.trim()) {
      toast.error("Введите название");
      return;
    }
    setSubmitting(true);
    try {
      const payload: any = {
        title: title.trim(),
        description: description || null,
        type,
        priority,
        due_date: dueDate ? new Date(dueDate).toISOString() : null,
        assignee_id: assigneeId || null,
        debtor_id: debtorId || null,
        contract_id: contractId || null,
      };
      if (isEdit && task?.id) {
        await apiClient.patch(`/tasks/${task.id}`, payload);
        toast.success("Задача обновлена");
      } else {
        await apiClient.post("/tasks", payload);
        toast.success("Задача создана");
      }
      onSaved();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Не удалось сохранить");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 animate-fade-in">
      <div className="absolute inset-0 bg-gray-900/40 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-2xl rounded-3xl bg-white shadow-modal animate-scale-in max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-100 px-6 py-5">
          <h3 className="text-xl font-bold tracking-tight text-gray-900">
            {isEdit ? "Редактировать задачу" : "Новая задача"}
          </h3>
          <button onClick={onClose} className="flex h-9 w-9 items-center justify-center rounded-full text-gray-400 hover:bg-gray-100 hover:text-gray-700">
            <X size={18} />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-4">
          {/* Title */}
          <div>
            <label className="text-xs font-semibold uppercase text-gray-400 block mb-1.5">Название *</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Например: Перезвонить клиенту"
              className="w-full rounded-2xl border border-gray-200 bg-white px-4 py-2.5 text-sm focus:border-primary-400 focus:outline-none focus:ring-4 focus:ring-primary-100"
              autoFocus
            />
          </div>

          {/* Type */}
          <div>
            <label className="text-xs font-semibold uppercase text-gray-400 block mb-2">Тип задачи</label>
            <div className="grid grid-cols-3 gap-2">
              {TYPE_OPTIONS.map((opt) => {
                const Icon = opt.icon;
                const active = type === opt.value;
                return (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => setType(opt.value)}
                    className={
                      active
                        ? "flex flex-col items-center gap-1 rounded-2xl bg-primary-500 p-3 text-white shadow-soft transition"
                        : "flex flex-col items-center gap-1 rounded-2xl border border-gray-200 bg-white p-3 text-gray-600 hover:bg-gray-50 transition"
                    }
                  >
                    <Icon size={18} />
                    <span className="text-xs font-medium">{opt.label}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Priority + Due date */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-semibold uppercase text-gray-400 block mb-1.5">Приоритет</label>
              <select
                value={priority}
                onChange={(e) => setPriority(e.target.value)}
                className="w-full rounded-2xl border border-gray-200 bg-white px-4 py-2.5 text-sm focus:border-primary-400 focus:outline-none focus:ring-4 focus:ring-primary-100"
              >
                {PRIORITY_OPTIONS.map((p) => (
                  <option key={p.value} value={p.value}>{p.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs font-semibold uppercase text-gray-400 block mb-1.5">Дедлайн</label>
              <input
                type="datetime-local"
                value={dueDate}
                onChange={(e) => setDueDate(e.target.value)}
                className="w-full rounded-2xl border border-gray-200 bg-white px-4 py-2.5 text-sm focus:border-primary-400 focus:outline-none focus:ring-4 focus:ring-primary-100"
              />
            </div>
          </div>

          {/* Assignee */}
          <div>
            <label className="text-xs font-semibold uppercase text-gray-400 block mb-1.5">Исполнитель</label>
            <select
              value={assigneeId}
              onChange={(e) => setAssigneeId(e.target.value ? Number(e.target.value) : "")}
              className="w-full rounded-2xl border border-gray-200 bg-white px-4 py-2.5 text-sm focus:border-primary-400 focus:outline-none focus:ring-4 focus:ring-primary-100"
            >
              <option value="">— Не назначено —</option>
              {users.map((u) => (
                <option key={u.id} value={u.id}>{u.full_name} ({u.role})</option>
              ))}
            </select>
          </div>

          {/* Debtor (search if not predefined) */}
          {!defaultDebtorId && (
            <div>
              <label className="text-xs font-semibold uppercase text-gray-400 block mb-1.5">Должник (опционально)</label>
              {debtorId ? (
                <div className="flex items-center justify-between rounded-2xl bg-primary-50 px-4 py-2.5">
                  <span className="text-sm font-medium text-primary-900">
                    Должник #{debtorId}
                  </span>
                  <button onClick={() => { setDebtorId(""); setContractId(""); setDebtorSearch(""); }} className="text-xs text-primary-700 hover:underline">
                    Сменить
                  </button>
                </div>
              ) : (
                <>
                  <input
                    type="text"
                    value={debtorSearch}
                    onChange={(e) => setDebtorSearch(e.target.value)}
                    placeholder="Найти должника по имени или ИИН..."
                    className="w-full rounded-2xl border border-gray-200 bg-white px-4 py-2.5 text-sm focus:border-primary-400 focus:outline-none focus:ring-4 focus:ring-primary-100"
                  />
                  {debtors.length > 0 && (
                    <div className="mt-2 rounded-2xl border border-gray-100 bg-white overflow-hidden max-h-48 overflow-y-auto">
                      {debtors.map((d) => (
                        <button
                          key={d.id}
                          type="button"
                          onClick={() => { setDebtorId(d.id); setDebtorSearch(""); setDebtors([]); }}
                          className="flex w-full items-center justify-between px-4 py-2.5 text-sm text-left hover:bg-gray-50 border-b border-gray-50 last:border-0"
                        >
                          <span className="font-medium text-gray-900">{d.full_name}</span>
                          <span className="text-xs text-gray-400">{d.iin}</span>
                        </button>
                      ))}
                    </div>
                  )}
                </>
              )}
            </div>
          )}

          {/* Contract (only if debtor selected) */}
          {debtorId && contracts.length > 0 && (
            <div>
              <label className="text-xs font-semibold uppercase text-gray-400 block mb-1.5">Договор (опционально)</label>
              <select
                value={contractId}
                onChange={(e) => setContractId(e.target.value ? Number(e.target.value) : "")}
                className="w-full rounded-2xl border border-gray-200 bg-white px-4 py-2.5 text-sm focus:border-primary-400 focus:outline-none focus:ring-4 focus:ring-primary-100"
              >
                <option value="">— Не выбран —</option>
                {contracts.map((c: any) => (
                  <option key={c.id} value={c.id}>
                    {c.contract_number || `#${c.id}`} {c.total_debt ? `— ${Number(c.total_debt).toLocaleString("ru-RU")} ₸` : ""}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Description */}
          <div>
            <label className="text-xs font-semibold uppercase text-gray-400 block mb-1.5">Описание</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={4}
              placeholder="Детали задачи..."
              className="w-full rounded-2xl border border-gray-200 bg-white px-4 py-2.5 text-sm focus:border-primary-400 focus:outline-none focus:ring-4 focus:ring-primary-100 resize-none"
            />
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-2 border-t border-gray-100 px-6 py-4">
          <button
            onClick={onClose}
            disabled={submitting}
            className="rounded-full px-5 py-2.5 text-sm font-medium text-gray-600 hover:bg-gray-100 transition"
          >
            Отмена
          </button>
          <button
            onClick={handleSubmit}
            disabled={submitting || !title.trim()}
            className="flex items-center gap-2 rounded-full bg-primary-500 px-5 py-2.5 text-sm font-semibold text-white shadow-soft hover:bg-primary-600 transition disabled:opacity-50"
          >
            {submitting ? "Сохранение..." : (isEdit ? "Сохранить" : "Создать")}
          </button>
        </div>
      </div>
    </div>
  );
}
