"use client";
import { useEffect, useState, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import AppShell from "@/components/layout/AppShell";
import { PageHeader, Spinner } from "@/components/ui";
import { apiClient } from "@/lib/api-client";
import { formatDate, formatMoney } from "@/lib/utils";
import { useAuth } from "@/lib/auth-context";
import { userService } from "@/services/api";
import { Trash2 } from "lucide-react";
import toast from "react-hot-toast";

const STATUS_LABELS: Record<string, string> = {
  active: "Активное",
  done: "Выполнено",
  fulfilled: "Выполнено",
  overdue: "Просрочено",
  cancelled: "Отменено",
};
const STATUS_COLORS: Record<string, string> = {
  active: "bg-blue-100 text-blue-800",
  done: "bg-green-100 text-green-800",
  fulfilled: "bg-green-100 text-green-800",
  overdue: "bg-red-100 text-red-800",
  cancelled: "bg-gray-100 text-gray-600",
};

export default function PromisesPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  // Whitelist валидных значений status — защита от мусора в URL
  const validStatuses = new Set(["active", "overdue", "fulfilled", "done", "cancelled"]);
  const initialStatus = (() => {
    const v = searchParams?.get("status") || "";
    return validStatuses.has(v) ? v : "";
  })();
  const { user } = useAuth();
  const isManager = user?.role?.toUpperCase() === "MANAGER";
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState(initialStatus);
  const [managerFilter, setManagerFilter] = useState("");
  const [managers, setManagers] = useState<any[]>([]);
  const [page, setPage] = useState(1);

  useEffect(() => {
    if (!isManager) userService.list().then((d: any) => setManagers(d.items || d)).catch(() => {});
  }, [isManager]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params: any = { page, page_size: 50 };
      if (statusFilter) params.status = statusFilter;
      if (managerFilter) params.manager_id = parseInt(managerFilter);
      const { data: res } = await apiClient.get("/promises/all", { params });
      setData(res);
    } catch { toast.error("Ошибка загрузки"); }
    finally { setLoading(false); }
  }, [page, statusFilter, managerFilter]);

  useEffect(() => { load(); }, [load]);

  const handleUpdateOverdue = async () => {
    try {
      await apiClient.post("/promises/process-overdue");
      toast.success("Статусы обновлены");
      load();
    } catch { toast.error("Ошибка"); }
  };

  const handleDelete = async (id: number, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm("Удалить обещание?")) return;
    try {
      await apiClient.delete(`/promises/${id}`);
      toast.success("Обещание удалено");
      load();
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || "Ошибка удаления");
    }
  };

  const items = data?.items ?? [];
  const total = data?.total ?? 0;

  // Группировка по должникам с суммами
  const byDebtor: Record<string, { name: string; debtor_id: number; sum: number; count: number; active: number }> = {};
  items.forEach((p: any) => {
    const key = String(p.debtor_id);
    if (!byDebtor[key]) {
      byDebtor[key] = { name: p.debtor_name, debtor_id: p.debtor_id, sum: 0, count: 0, active: 0 };
    }
    byDebtor[key].sum += Number(p.amount) || 0;
    byDebtor[key].count++;
    if (p.status === "active") byDebtor[key].active++;
  });
  const debtorSummary = Object.values(byDebtor).sort((a, b) => b.sum - a.sum);

  // Общая сумма обещаний
  const totalAmount = items.reduce((s: number, p: any) => s + (Number(p.amount) || 0), 0);
  const activeAmount = items.filter((p: any) => p.status === "active").reduce((s: number, p: any) => s + (Number(p.amount) || 0), 0);

  return (
    <AppShell>
      <PageHeader
        title="Обещания оплаты"
        subtitle={`Всего: ${total}`}
        actions={
          <button onClick={handleUpdateOverdue} className="btn-secondary flex items-center gap-1">
            Обновить статусы
          </button>
        }
      />

      {/* Сводка по суммам */}
      <div className="mb-4 grid grid-cols-2 md:grid-cols-3 gap-3">
        <div className="card p-3 text-center">
          <p className="text-xs text-gray-500">Всего обещаний</p>
          <p className="text-2xl font-bold">{total}</p>
        </div>
        <div className="card p-3 text-center">
          <p className="text-xs text-gray-500">Сумма обещаний</p>
          <p className="text-xl font-bold text-blue-700">{formatMoney(totalAmount)}</p>
        </div>
        <div className="card p-3 text-center">
          <p className="text-xs text-gray-500">Активных обещаний</p>
          <p className="text-xl font-bold text-green-700">{formatMoney(activeAmount)}</p>
        </div>
      </div>

      {/* Filters */}
      <div className="card mb-4 p-3">
        <div className="flex flex-wrap gap-2">
          <select className="input h-9 text-sm w-40" value={statusFilter} onChange={(e) => {
            const v = e.target.value;
            setStatusFilter(v);
            setPage(1);
            // Синхронизируем URL — без перезагрузки страницы
            const url = new URL(window.location.href);
            if (v) url.searchParams.set("status", v); else url.searchParams.delete("status");
            window.history.replaceState({}, "", url.toString());
          }}>
            <option value="">Все статусы</option>
            <option value="active">Активные</option>
            <option value="overdue">Просроченные</option>
            <option value="done">Выполненные</option>
            <option value="cancelled">Отменённые</option>
          </select>
          {!isManager && managers.length > 0 && (
            <select className="input h-9 text-sm w-44" value={managerFilter} onChange={(e) => { setManagerFilter(e.target.value); setPage(1); }}>
              <option value="">Все менеджеры</option>
              {managers.filter((m: any) => ["MANAGER","HEAD"].includes((m.role||"").toUpperCase())).map((m: any) => (
                <option key={m.id} value={m.id}>{m.full_name}</option>
              ))}
            </select>
          )}
        </div>
      </div>

      {/* Сводка по должникам */}
      {debtorSummary.length > 0 && (
        <details className="card mb-4 p-3">
          <summary className="font-medium text-sm cursor-pointer text-blue-700">
            📊 Сводка по должникам ({debtorSummary.length})
          </summary>
          <div className="mt-3 max-h-64 overflow-y-auto">
            <table className="w-full text-sm">
              <thead className="text-xs text-gray-400 uppercase border-b">
                <tr>
                  <th className="text-left py-2">Должник</th>
                  <th className="text-center py-2">Кол-во</th>
                  <th className="text-right py-2">Сумма</th>
                </tr>
              </thead>
              <tbody>
                {debtorSummary.map(d => (
                  <tr key={d.debtor_id} className="hover:bg-gray-50 cursor-pointer border-b border-gray-50"
                      onClick={() => router.push(`/debtors/${d.debtor_id}`)}>
                    <td className="py-2 font-medium">{d.name}</td>
                    <td className="text-center py-2 text-gray-500">
                      {d.count} {d.active > 0 && <span className="text-blue-600">(активных {d.active})</span>}
                    </td>
                    <td className="text-right py-2 font-semibold">{formatMoney(d.sum)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      )}

      {loading ? (
        <div className="flex justify-center py-12"><Spinner size="lg" /></div>
      ) : (
        <div className="card overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50 text-xs font-semibold text-gray-500 uppercase">
                <th className="px-4 py-3 text-left">Должник</th>
                <th className="px-4 py-3 text-left">Договор</th>
                <th className="px-4 py-3 text-left">Дата обещания</th>
                <th className="px-4 py-3 text-right">Сумма</th>
                <th className="px-4 py-3 text-left">Статус</th>
                <th className="px-4 py-3 text-left">Примечание</th>
                <th className="px-4 py-3 text-center">Действие</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {items.length === 0 ? (
                <tr><td colSpan={7} className="py-8 text-center text-gray-400">Нет обещаний</td></tr>
              ) : items.map((p: any) => (
                <tr key={p.id} className="hover:bg-gray-50 cursor-pointer" onClick={() => router.push(`/debtors/${p.debtor_id}`)}>
                  <td className="px-4 py-3 font-medium">{p.debtor_name}</td>
                  <td className="px-4 py-3 font-mono text-xs text-gray-500">{p.contract_number}</td>
                  <td className="px-4 py-3 text-gray-600">{formatDate(p.promise_date)}</td>
                  <td className="px-4 py-3 text-right font-semibold">{formatMoney(p.amount)}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[p.status] || "bg-gray-100"}`}>
                      {STATUS_LABELS[p.status] || p.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-500 max-w-xs truncate">{p.notes || "—"}</td>
                  <td className="px-4 py-3 text-center" onClick={(e) => e.stopPropagation()}>
                    <button
                      onClick={(e) => handleDelete(p.id, e)}
                      className="inline-flex items-center justify-center w-8 h-8 rounded-lg hover:bg-red-50 text-gray-400 hover:text-red-500 transition-colors"
                      title="Удалить обещание"
                    >
                      <Trash2 size={15} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {data && Math.ceil(total / 50) > 1 && (
        <div className="mt-4 flex justify-center gap-2">
          <button disabled={page <= 1} onClick={() => setPage(p => p-1)} className="btn-secondary">←</button>
          <span className="px-3 py-2 text-sm text-gray-600">Стр. {page} из {Math.ceil(total/50)}</span>
          <button disabled={page >= Math.ceil(total/50)} onClick={() => setPage(p => p+1)} className="btn-secondary">→</button>
        </div>
      )}
    </AppShell>
  );
}
