"use client";
import { useEffect, useState, useCallback } from "react";
import AppShell from "@/components/layout/AppShell";
import { PageHeader, Spinner } from "@/components/ui";
import { apiClient } from "@/lib/api-client";
import { formatDateTime } from "@/lib/utils";
import { userService } from "@/services/api";
import { useAuth } from "@/lib/auth-context";
import toast from "react-hot-toast";

const RESULT_LABELS: Record<string, string> = {
  reached: "Дозвон",
  not_reached: "Не дозвон",
  busy: "Занято",
  wrong_number: "Неверный номер",
  refused: "Отказ",
};

const RESULT_COLORS: Record<string, string> = {
  reached: "bg-green-100 text-green-800",
  not_reached: "bg-red-100 text-red-800",
  busy: "bg-yellow-100 text-yellow-800",
  wrong_number: "bg-gray-100 text-gray-600",
  refused: "bg-orange-100 text-orange-800",
};

export default function CallsPage() {
  const { user } = useAuth();
  const isManager = user?.role?.toUpperCase() === "MANAGER";
  const [data, setData] = useState<any>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [dateFrom, setDateFrom] = useState(() => {
    const d = new Date(); d.setDate(d.getDate() - 7);
    return d.toISOString().slice(0, 10);
  });
  const [dateTo, setDateTo] = useState(() => new Date().toISOString().slice(0, 10));
  const [managerFilter, setManagerFilter] = useState("");
  const [managers, setManagers] = useState<any[]>([]);

  useEffect(() => {
    if (!isManager) userService.list().then((d: any) => setManagers(d.items || d)).catch(() => {});
  }, [isManager]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params: any = { page, page_size: 50, date_from: dateFrom, date_to: dateTo };
      if (managerFilter) params.manager_id = parseInt(managerFilter);
      const { data: res } = await apiClient.get("/dashboard/calls-history", { params });
      setData(res);
      setLoadError(null);
    } catch (err: any) {
      const msg = err?.response?.data?.detail || "Не удалось загрузить историю звонков";
      setLoadError(msg);
      toast.error(msg, { id: "calls-load" });
    }
    finally { setLoading(false); }
  }, [page, dateFrom, dateTo, managerFilter]);

  useEffect(() => { load(); }, [load]);

  // Stats
  const items = data?.items ?? [];
  const totalCalls = data?.total ?? 0;
  const reached = items.filter((c: any) => c.result === "reached").length;

  return (
    <AppShell>
      <PageHeader title="История звонков" subtitle={`Всего: ${totalCalls}`} />

      <div className="card mb-4 p-3">
        <div className="flex flex-wrap gap-2 items-center">
          <div className="flex items-center gap-1">
            <label className="text-sm text-gray-500">С:</label>
            <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} className="input h-9 w-36 text-sm" />
          </div>
          <div className="flex items-center gap-1">
            <label className="text-sm text-gray-500">По:</label>
            <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} className="input h-9 w-36 text-sm" />
          </div>
          {!isManager && managers.length > 0 && (
            <select className="input h-9 text-sm w-44" value={managerFilter} onChange={(e) => setManagerFilter(e.target.value)}>
              <option value="">Все менеджеры</option>
              {managers.filter(m => ["MANAGER","HEAD"].includes((m.role||"").toUpperCase())).map(m => (
                <option key={m.id} value={m.id}>{m.full_name}</option>
              ))}
            </select>
          )}
          <button onClick={load} className="btn-primary h-9 text-sm">Найти</button>
        </div>
      </div>

      {/* Stats */}
      <div className="mb-4 grid grid-cols-3 gap-3">
        <div className="card p-3 text-center">
          <p className="text-xs text-gray-500">Всего звонков</p>
          <p className="text-2xl font-bold">{totalCalls}</p>
        </div>
        <div className="card p-3 text-center">
          <p className="text-xs text-gray-500">Дозвонов</p>
          <p className="text-2xl font-bold text-green-600">{reached}</p>
        </div>
        <div className="card p-3 text-center">
          <p className="text-xs text-gray-500">% дозвона</p>
          <p className="text-2xl font-bold text-blue-600">
            {items.length > 0 ? Math.round(reached / items.length * 100) : 0}%
          </p>
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center py-12"><Spinner size="lg" /></div>
      ) : (
        <div className="card overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50 text-xs font-semibold text-gray-500 uppercase">
                <th className="px-4 py-3 text-left">Дата/время</th>
                <th className="px-4 py-3 text-left">Договор</th>
                <th className="px-4 py-3 text-left">Результат</th>
                <th className="px-4 py-3 text-left">Длительность</th>
                <th className="px-4 py-3 text-left">Заметки</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {items.length === 0 ? (
                <tr><td colSpan={5} className="py-8 text-center text-gray-400">Нет звонков за период</td></tr>
              ) : items.map((c: any) => (
                <tr key={c.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-xs text-gray-500">{formatDateTime(c.called_at)}</td>
                  <td className="px-4 py-3 font-mono text-xs">#{c.contract_id}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${RESULT_COLORS[c.result] || "bg-gray-100"}`}>
                      {RESULT_LABELS[c.result] || c.result}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-500">
                    {c.duration_seconds ? `${Math.floor(c.duration_seconds/60)}м ${c.duration_seconds%60}с` : "—"}
                  </td>
                  <td className="px-4 py-3 text-gray-600 max-w-xs truncate">{c.notes || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </AppShell>
  );
}
