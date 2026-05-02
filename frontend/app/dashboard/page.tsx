"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import AppShell from "@/components/layout/AppShell";
import { apiClient } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { Spinner } from "@/components/ui";
import { Users, AlertTriangle, Calendar, TrendingUp, Wallet, CheckCircle2, Clock, FileText } from "lucide-react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, Cell,
} from "recharts";

interface KPI {
  total_debtors: number;
  debtors_by_kanban: Record<string, number>;
  promises_today: number;
  promises_today_amount: number;
  promises_overdue: number;
  active_schedules: number;
  overdue_schedules: number;
  payments_today: number;
  payments_this_week: number;
  payments_this_month: number;
  daily_collections: { date: string; amount: number; count: number }[];
}

interface ManagerKPI {
  manager_id: number;
  manager_name: string;
  debtors_count: number;
  active_promises: number;
  overdue_promises: number;
  promises_kept_count: number;
  payments_this_month: number;
  payments_count: number;
  completion_rate: number;
}

const KANBAN_LABELS: Record<string, string> = {
  new: "Новые", contact: "Контакт", promise: "Обещание",
  schedule: "График", overdue: "Просрочка", paid: "Оплачено",
};
const KANBAN_COLORS: Record<string, string> = {
  new: "#eab308", contact: "#3b82f6", promise: "#a855f7",
  schedule: "#6366f1", overdue: "#ef4444", paid: "#22c55e",
};

export default function DashboardPage() {
  const router = useRouter();
  const { user } = useAuth();
  const isAdmin = ["ADMIN", "HEAD"].includes((user?.role || "").toUpperCase());
  const [kpi, setKpi] = useState<KPI | null>(null);
  const [managers, setManagers] = useState<ManagerKPI[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => { load(); }, []);

  const load = async () => {
    try {
      setLoading(true);
      const promises: any[] = [apiClient.get("/dashboard-kpi")];
      if (isAdmin) promises.push(apiClient.get("/dashboard-kpi/managers"));
      const [kpiRes, managersRes] = await Promise.all(promises);
      setKpi(kpiRes.data);
      if (managersRes) setManagers(managersRes.data);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  const fmt = (n: number) => Math.round(n).toLocaleString("ru-KZ") + " ₸";

  if (loading) return (
    <AppShell><div className="flex justify-center py-20"><Spinner size="lg" /></div></AppShell>
  );
  if (!kpi) return <AppShell><div>Ошибка загрузки</div></AppShell>;

  const kanbanData = Object.entries(kpi.debtors_by_kanban || {}).map(([k, v]) => ({
    name: KANBAN_LABELS[k] || k,
    value: v,
    fill: KANBAN_COLORS[k] || "#94a3b8",
  }));

  return (
    <AppShell>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Дашборд</h1>
        <p className="text-sm text-gray-500 mt-1">Обзор ключевых показателей</p>
      </div>

      {/* Top KPI cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <button onClick={() => router.push("/debtors")}
          className="card p-4 text-left hover:shadow-md transition-shadow">
          <Users size={20} className="text-blue-500 mb-2" />
          <p className="text-xs text-gray-500">Всего должников</p>
          <p className="text-3xl font-bold text-gray-900">{kpi.total_debtors}</p>
        </button>

        <button onClick={() => router.push("/promises?status=active")}
          className="card p-4 text-left hover:shadow-md transition-shadow">
          <Calendar size={20} className="text-purple-500 mb-2" />
          <p className="text-xs text-gray-500">Обещания на сегодня</p>
          <p className="text-3xl font-bold text-gray-900">{kpi.promises_today}</p>
          {kpi.promises_today_amount > 0 && (
            <p className="text-xs text-purple-600 mt-1">{fmt(kpi.promises_today_amount)}</p>
          )}
        </button>

        <button onClick={() => router.push("/promises?status=overdue")}
          className="card p-4 text-left hover:shadow-md transition-shadow">
          <AlertTriangle size={20} className="text-red-500 mb-2" />
          <p className="text-xs text-gray-500">Сорванные обещания</p>
          <p className="text-3xl font-bold text-red-600">{kpi.promises_overdue}</p>
        </button>

        <button onClick={() => router.push("/payments")}
          className="card p-4 text-left hover:shadow-md transition-shadow">
          <Wallet size={20} className="text-green-500 mb-2" />
          <p className="text-xs text-gray-500">Сборы за месяц</p>
          <p className="text-2xl font-bold text-green-700">{fmt(kpi.payments_this_month)}</p>
        </button>
      </div>

      {/* Schedules row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="card p-4">
          <FileText size={18} className="text-indigo-500 mb-2" />
          <p className="text-xs text-gray-500">Активные графики</p>
          <p className="text-2xl font-bold">{kpi.active_schedules}</p>
        </div>
        <div className="card p-4">
          <Clock size={18} className="text-orange-500 mb-2" />
          <p className="text-xs text-gray-500">Просроченные графики</p>
          <p className="text-2xl font-bold text-orange-600">{kpi.overdue_schedules}</p>
        </div>
        <div className="card p-4">
          <CheckCircle2 size={18} className="text-blue-500 mb-2" />
          <p className="text-xs text-gray-500">Сборы сегодня</p>
          <p className="text-xl font-bold text-blue-700">{fmt(kpi.payments_today)}</p>
        </div>
        <div className="card p-4">
          <TrendingUp size={18} className="text-emerald-500 mb-2" />
          <p className="text-xs text-gray-500">Сборы за неделю</p>
          <p className="text-xl font-bold text-emerald-700">{fmt(kpi.payments_this_week)}</p>
        </div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
        {/* Daily collections */}
        <div className="card p-4">
          <h3 className="font-semibold text-gray-800 mb-3">Сборы по дням (30 дней)</h3>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={kpi.daily_collections}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" tickFormatter={(d) => new Date(d).toLocaleDateString("ru-KZ", { day: "2-digit", month: "2-digit" })} />
              <YAxis tickFormatter={(v) => (v / 1000) + "k"} />
              <Tooltip
                formatter={(v: any) => fmt(v)}
                labelFormatter={(d) => new Date(d).toLocaleDateString("ru-KZ")}
              />
              <Line type="monotone" dataKey="amount" stroke="#22c55e" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Kanban distribution */}
        <div className="card p-4">
          <h3 className="font-semibold text-gray-800 mb-3">Должники по статусам</h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={kanbanData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="value">
                {kanbanData.map((entry, index) => (
                  <Cell key={index} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Manager Effectiveness (admin only) */}
      {isAdmin && managers.length > 0 && (
        <div className="card overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-100">
            <h3 className="font-semibold text-gray-800">Эффективность менеджеров</h3>
          </div>
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr className="text-xs text-gray-500 uppercase">
                <th className="px-4 py-3 text-left">Менеджер</th>
                <th className="px-4 py-3 text-center">Должников</th>
                <th className="px-4 py-3 text-center">Обещания</th>
                <th className="px-4 py-3 text-center">% выполнения</th>
                <th className="px-4 py-3 text-right">Сборы (мес)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {managers.map(m => (
                <tr key={m.manager_id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium">{m.manager_name}</td>
                  <td className="px-4 py-3 text-center">{m.debtors_count}</td>
                  <td className="px-4 py-3 text-center">
                    <span className="text-blue-600">{m.active_promises}</span>
                    {m.overdue_promises > 0 && <span className="text-red-500"> / {m.overdue_promises}⚠</span>}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className={`font-medium ${m.completion_rate >= 70 ? "text-green-600" : m.completion_rate >= 40 ? "text-orange-600" : "text-red-600"}`}>
                      {m.completion_rate}%
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right font-bold text-green-700">{fmt(m.payments_this_month)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </AppShell>
  );
}
