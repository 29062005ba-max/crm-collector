"use client";
import { useEffect, useState } from "react";
import AppShell from "@/components/layout/AppShell";
import { apiClient } from "@/lib/api-client";
import toast from "react-hot-toast";
import { Spinner } from "@/components/ui";
import { Plus, Users, Trash2, Play, RefreshCw } from "lucide-react";

interface Queue {
  id: number;
  name: string;
  description: string | null;
  is_active: boolean;
  max_attempts: number;
  retry_after_hours: number;
  total_items: number;
  pending_items: number;
  completed_items: number;
}

interface ManagerProgress {
  manager_id: number;
  manager_name: string;
  total_assigned: number;
  pending: number;
  completed_today: number;
  reached_today: number;
  not_reached_today: number;
  promises_today: number;
}

export default function CallQueueAdminPage() {
  const [queues, setQueues] = useState<Queue[]>([]);
  const [progress, setProgress] = useState<ManagerProgress[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [populating, setPopulating] = useState<number | null>(null);

  const [form, setForm] = useState({
    name: "",
    description: "",
    filter_overdue_min_days: "",
    filter_overdue_max_days: "",
    filter_debt_min: "",
    filter_debt_max: "",
    filter_contract_status: "",
    max_attempts: 3,
    retry_after_hours: 2,
  });

  const fetchAll = async () => {
    try {
      const [q, p] = await Promise.all([
        apiClient.get("/call-queue/queues"),
        apiClient.get("/call-queue/all-progress"),
      ]);
      setQueues(q.data);
      setProgress(p.data);
    } catch (e: any) {
      toast.error(e.response?.data?.detail || "Ошибка загрузки");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchAll(); }, []);

  const createQueue = async () => {
    if (!form.name) {
      toast.error("Укажите название");
      return;
    }
    try {
      const payload: any = {
        name: form.name,
        description: form.description || null,
        max_attempts: form.max_attempts,
        retry_after_hours: form.retry_after_hours,
        auto_assign_strategy: "round_robin",
      };
      if (form.filter_overdue_min_days) payload.filter_overdue_min_days = parseInt(form.filter_overdue_min_days);
      if (form.filter_overdue_max_days) payload.filter_overdue_max_days = parseInt(form.filter_overdue_max_days);
      if (form.filter_debt_min) payload.filter_debt_min = parseFloat(form.filter_debt_min);
      if (form.filter_debt_max) payload.filter_debt_max = parseFloat(form.filter_debt_max);
      if (form.filter_contract_status) payload.filter_contract_status = form.filter_contract_status;

      await apiClient.post("/call-queue/queues", payload);
      toast.success("Очередь создана");
      setShowCreate(false);
      setForm({
        name: "", description: "", filter_overdue_min_days: "", filter_overdue_max_days: "",
        filter_debt_min: "", filter_debt_max: "", filter_contract_status: "",
        max_attempts: 3, retry_after_hours: 2,
      });
      fetchAll();
    } catch (e: any) {
      toast.error(e.response?.data?.detail || "Ошибка");
    }
  };

  const populateQueue = async (id: number) => {
    setPopulating(id);
    try {
      const { data } = await apiClient.post(`/call-queue/queues/${id}/populate`, { limit: 500, priority: 0 });
      toast.success(`Добавлено ${data.added} должников`);
      fetchAll();
    } catch (e: any) {
      toast.error(e.response?.data?.detail || "Ошибка");
    } finally {
      setPopulating(null);
    }
  };

  const deleteQueue = async (id: number) => {
    if (!confirm("Удалить очередь со всеми элементами?")) return;
    try {
      await apiClient.delete(`/call-queue/queues/${id}`);
      toast.success("Удалено");
      fetchAll();
    } catch (e: any) {
      toast.error(e.response?.data?.detail || "Ошибка");
    }
  };

  if (loading) return <AppShell><Spinner /></AppShell>;

  return (
    <AppShell>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">Управление автодозвоном</h1>
          <div className="flex gap-2">
            <button onClick={fetchAll} className="rounded border px-3 py-2 text-sm hover:bg-gray-50">
              <RefreshCw size={14} className="inline" /> Обновить
            </button>
            <button
              onClick={() => setShowCreate(true)}
              className="flex items-center gap-2 rounded bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
            >
              <Plus size={16} /> Создать очередь
            </button>
          </div>
        </div>

        {/* Queues table */}
        <div className="rounded-lg border bg-white">
          <div className="border-b p-4 font-semibold">Очереди звонков</div>
          {queues.length === 0 ? (
            <div className="p-8 text-center text-gray-500">Нет очередей. Создайте первую.</div>
          ) : (
            <table className="w-full">
              <thead className="bg-gray-50 text-left text-xs uppercase text-gray-500">
                <tr>
                  <th className="p-3">Название</th>
                  <th className="p-3">Должников</th>
                  <th className="p-3">В работе</th>
                  <th className="p-3">Завершено</th>
                  <th className="p-3">Попыток</th>
                  <th className="p-3"></th>
                </tr>
              </thead>
              <tbody className="text-sm">
                {queues.map((q) => (
                  <tr key={q.id} className="border-t hover:bg-gray-50">
                    <td className="p-3">
                      <div className="font-medium">{q.name}</div>
                      {q.description && <div className="text-xs text-gray-500">{q.description}</div>}
                    </td>
                    <td className="p-3">{q.total_items}</td>
                    <td className="p-3 text-orange-600">{q.pending_items}</td>
                    <td className="p-3 text-green-600">{q.completed_items}</td>
                    <td className="p-3">{q.max_attempts}</td>
                    <td className="p-3">
                      <div className="flex gap-2">
                        <button
                          onClick={() => populateQueue(q.id)}
                          disabled={populating === q.id}
                          className="flex items-center gap-1 rounded bg-blue-50 px-3 py-1 text-xs text-blue-700 hover:bg-blue-100 disabled:opacity-50"
                        >
                          <Play size={12} /> {populating === q.id ? "..." : "Наполнить"}
                        </button>
                        <button
                          onClick={() => deleteQueue(q.id)}
                          className="rounded bg-red-50 p-1 text-red-600 hover:bg-red-100"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Manager progress */}
        <div className="rounded-lg border bg-white">
          <div className="border-b p-4 font-semibold">Прогресс менеджеров сегодня</div>
          {progress.length === 0 ? (
            <div className="p-8 text-center text-gray-500">Нет менеджеров</div>
          ) : (
            <table className="w-full">
              <thead className="bg-gray-50 text-left text-xs uppercase text-gray-500">
                <tr>
                  <th className="p-3">Менеджер</th>
                  <th className="p-3">Назначено</th>
                  <th className="p-3">В очереди</th>
                  <th className="p-3">Дозвонов</th>
                  <th className="p-3">Недозвонов</th>
                  <th className="p-3">Обещаний</th>
                  <th className="p-3">Эффективность</th>
                </tr>
              </thead>
              <tbody className="text-sm">
                {progress.map((p) => {
                  const total_calls = p.reached_today + p.not_reached_today;
                  const eff = total_calls ? Math.round((p.reached_today / total_calls) * 100) : 0;
                  return (
                    <tr key={p.manager_id} className="border-t">
                      <td className="p-3 font-medium">{p.manager_name}</td>
                      <td className="p-3">{p.total_assigned}</td>
                      <td className="p-3 text-orange-600">{p.pending}</td>
                      <td className="p-3 text-green-600">{p.reached_today}</td>
                      <td className="p-3 text-orange-600">{p.not_reached_today}</td>
                      <td className="p-3 font-semibold text-blue-600">{p.promises_today}</td>
                      <td className="p-3">
                        <span className={`rounded px-2 py-0.5 text-xs ${
                          eff >= 60 ? "bg-green-100 text-green-700" :
                          eff >= 30 ? "bg-yellow-100 text-yellow-700" :
                          "bg-red-100 text-red-700"
                        }`}>
                          {eff}%
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>

        {/* Create modal */}
        {showCreate && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
            <div className="w-full max-w-2xl rounded-lg bg-white p-6">
              <h3 className="mb-4 text-lg font-bold">Новая очередь обзвона</h3>
              <div className="space-y-3">
                <div>
                  <label className="block text-sm font-medium">Название *</label>
                  <input
                    value={form.name}
                    onChange={(e) => setForm({ ...form, name: e.target.value })}
                    placeholder="Например: Просрочка > 30 дней"
                    className="mt-1 w-full rounded border px-3 py-2"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium">Описание</label>
                  <textarea
                    value={form.description}
                    onChange={(e) => setForm({ ...form, description: e.target.value })}
                    className="mt-1 w-full rounded border px-3 py-2"
                    rows={2}
                  />
                </div>

                <div className="rounded border bg-gray-50 p-3">
                  <div className="mb-2 text-sm font-semibold">Фильтры наполнения</div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="text-xs">Просрочка от (дней)</label>
                      <input
                        type="number"
                        value={form.filter_overdue_min_days}
                        onChange={(e) => setForm({ ...form, filter_overdue_min_days: e.target.value })}
                        className="mt-1 w-full rounded border px-2 py-1 text-sm"
                      />
                    </div>
                    <div>
                      <label className="text-xs">Просрочка до (дней)</label>
                      <input
                        type="number"
                        value={form.filter_overdue_max_days}
                        onChange={(e) => setForm({ ...form, filter_overdue_max_days: e.target.value })}
                        className="mt-1 w-full rounded border px-2 py-1 text-sm"
                      />
                    </div>
                    <div>
                      <label className="text-xs">Долг от (₸)</label>
                      <input
                        type="number"
                        value={form.filter_debt_min}
                        onChange={(e) => setForm({ ...form, filter_debt_min: e.target.value })}
                        className="mt-1 w-full rounded border px-2 py-1 text-sm"
                      />
                    </div>
                    <div>
                      <label className="text-xs">Долг до (₸)</label>
                      <input
                        type="number"
                        value={form.filter_debt_max}
                        onChange={(e) => setForm({ ...form, filter_debt_max: e.target.value })}
                        className="mt-1 w-full rounded border px-2 py-1 text-sm"
                      />
                    </div>
                    <div className="col-span-2">
                      <label className="text-xs">Статус договора</label>
                      <input
                        value={form.filter_contract_status}
                        onChange={(e) => setForm({ ...form, filter_contract_status: e.target.value })}
                        placeholder="например: overdue"
                        className="mt-1 w-full rounded border px-2 py-1 text-sm"
                      />
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-sm font-medium">Макс. попыток</label>
                    <input
                      type="number"
                      min={1}
                      max={10}
                      value={form.max_attempts}
                      onChange={(e) => setForm({ ...form, max_attempts: parseInt(e.target.value) || 3 })}
                      className="mt-1 w-full rounded border px-3 py-2"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium">Повтор через (часы)</label>
                    <input
                      type="number"
                      min={1}
                      max={72}
                      value={form.retry_after_hours}
                      onChange={(e) => setForm({ ...form, retry_after_hours: parseInt(e.target.value) || 2 })}
                      className="mt-1 w-full rounded border px-3 py-2"
                    />
                  </div>
                </div>
              </div>

              <div className="mt-6 flex gap-2">
                <button onClick={() => setShowCreate(false)} className="flex-1 rounded border px-4 py-2 hover:bg-gray-50">
                  Отмена
                </button>
                <button
                  onClick={createQueue}
                  className="flex-1 rounded bg-primary-600 px-4 py-2 font-medium text-white hover:bg-primary-700"
                >
                  Создать
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
