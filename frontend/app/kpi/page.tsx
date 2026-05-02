"use client";
import { useEffect, useState } from "react";
import AppShell from "@/components/layout/AppShell";
import { PageHeader, Spinner } from "@/components/ui";
import { apiClient } from "@/lib/api-client";
import { formatMoney } from "@/lib/utils";
import { RefreshCw, Users, UserX } from "lucide-react";
import toast from "react-hot-toast";

interface KpiRow {
  manager_id: number;
  manager_name: string;
  role: string;
  contracts_count: number;
  payments_count: number;
  payments_amount: number;
  calls_total: number;
  calls_reached: number;
  contact_rate: number;
  promises_total: number;
  promises_done: number;
  promises_overdue: number;
  promise_kept_rate: number;
}

export default function KpiPage() {
  const [data, setData] = useState<KpiRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [assigning, setAssigning] = useState(false);
  const [clearing, setClearing] = useState(false);
  const [dateFrom, setDateFrom] = useState(() => {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-01`;
  });
  const [dateTo, setDateTo] = useState(() => new Date().toISOString().slice(0, 10));

  const load = async () => {
    setLoading(true);
    try {
      const { data: kpi } = await apiClient.get("/management/kpi", {
        params: { date_from: dateFrom, date_to: dateTo },
      });
      setData(kpi);
    } catch {
      toast.error("Ошибка загрузки KPI");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [dateFrom, dateTo]);

  const handleAutoAssign = async () => {
    setAssigning(true);
    try {
      const { data: res } = await apiClient.post("/management/auto-assign");
      toast.success(`Распределено договоров: ${res.assigned}`);
      load();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? "Ошибка");
    } finally {
      setAssigning(false);
    }
  };

  const handleClearAssignments = async () => {
    if (!confirm("Снять всех менеджеров со всех договоров?")) return;
    setClearing(true);
    try {
      const { data: res } = await apiClient.delete("/management/assignments/clear");
      toast.success(`Снято назначений: ${res.cleared}`);
      load();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? "Ошибка");
    } finally {
      setClearing(false);
    }
  };

  const totalPayments = data.reduce((s, r) => s + r.payments_amount, 0);
  const totalCalls = data.reduce((s, r) => s + r.calls_total, 0);

  return (
    <AppShell>
      <PageHeader
        title="KPI менеджеров"
        subtitle="Эффективность за период"
        actions={
          <div className="flex gap-2">
            <button onClick={handleClearAssignments} disabled={clearing} className="btn-secondary flex items-center gap-1 text-red-600 border-red-200 hover:bg-red-50">
              <UserX size={16} />
              {clearing ? "Снимаю..." : "Снять всех"}
            </button>
            <button onClick={handleAutoAssign} disabled={assigning} className="btn-primary flex items-center gap-1">
              <Users size={16} />
              {assigning ? "Распределяю..." : "Авторазмещение"}
            </button>
          </div>
        }
      />

      <div className="card mb-6 p-4">
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-2">
            <label className="text-sm text-gray-600">С:</label>
            <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} className="input w-40" />
          </div>
          <div className="flex items-center gap-2">
            <label className="text-sm text-gray-600">По:</label>
            <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} className="input w-40" />
          </div>
          <button onClick={load} className="btn-secondary flex items-center gap-1">
            <RefreshCw size={14} /> Обновить
          </button>
        </div>
      </div>

      <div className="mb-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
        <div className="card p-4 text-center">
          <p className="text-xs text-gray-500">Менеджеров</p>
          <p className="text-2xl font-bold text-gray-900">{data.length}</p>
        </div>
        <div className="card p-4 text-center">
          <p className="text-xs text-gray-500">Собрано итого</p>
          <p className="text-xl font-bold text-green-700">{formatMoney(totalPayments)}</p>
        </div>
        <div className="card p-4 text-center">
          <p className="text-xs text-gray-500">Звонков итого</p>
          <p className="text-2xl font-bold text-blue-700">{totalCalls.toLocaleString()}</p>
        </div>
        <div className="card p-4 text-center">
          <p className="text-xs text-gray-500">Договоров в работе</p>
          <p className="text-2xl font-bold text-gray-900">
            {data.reduce((s, r) => s + r.contracts_count, 0).toLocaleString()}
          </p>
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center py-16"><Spinner size="lg" /></div>
      ) : data.length === 0 ? (
        <div className="card p-12 text-center text-gray-400">
          Нет данных. Добавьте менеджеров и назначьте им договора.
        </div>
      ) : (
        <div className="card overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50 text-xs font-semibold text-gray-500 uppercase">
                <th className="px-4 py-3 text-left">Менеджер</th>
                <th className="px-4 py-3 text-right">Договоров</th>
                <th className="px-4 py-3 text-right">Платежей</th>
                <th className="px-4 py-3 text-right">Собрано</th>
                <th className="px-4 py-3 text-right">Звонков</th>
                <th className="px-4 py-3 text-right">Дозвон %</th>
                <th className="px-4 py-3 text-right">Обещаний</th>
                <th className="px-4 py-3 text-right">Выполнено %</th>
                <th className="px-4 py-3 text-right">Просрочено</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {data.map((row, i) => (
                <tr key={row.manager_id} className={i === 0 ? "bg-yellow-50" : "hover:bg-gray-50"}>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      {i === 0 && <span className="text-yellow-500">🏆</span>}
                      <div>
                        <p className="font-medium text-gray-900">{row.manager_name}</p>
                        <p className="text-xs text-gray-400">{row.role}</p>
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right font-medium">{row.contracts_count}</td>
                  <td className="px-4 py-3 text-right">{row.payments_count}</td>
                  <td className="px-4 py-3 text-right font-semibold text-green-700">
                    {formatMoney(row.payments_amount)}
                  </td>
                  <td className="px-4 py-3 text-right">{row.calls_total}</td>
                  <td className="px-4 py-3 text-right">
                    <span className={`font-medium ${row.contact_rate >= 50 ? "text-green-600" : row.contact_rate >= 30 ? "text-yellow-600" : "text-red-600"}`}>
                      {row.contact_rate}%
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">{row.promises_total}</td>
                  <td className="px-4 py-3 text-right">
                    <span className={`font-medium ${row.promise_kept_rate >= 70 ? "text-green-600" : row.promise_kept_rate >= 40 ? "text-yellow-600" : "text-red-600"}`}>
                      {row.promise_kept_rate}%
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right text-red-600 font-medium">
                    {row.promises_overdue}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </AppShell>
  );
}
