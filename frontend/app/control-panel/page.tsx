"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import AppShell from "@/components/layout/AppShell";
import { apiClient } from "@/lib/api-client";
import { Spinner } from "@/components/ui";
import toast from "react-hot-toast";
import { useAuth } from "@/lib/auth-context";
import {
  Crown, Banknote, TrendingUp, AlertTriangle, Sparkles, Phone,
  Trophy, RefreshCw, Calendar, Users, Flame,
} from "lucide-react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Bar, BarChart,
} from "recharts";

interface Summary {
  collection_today: number;
  collection_week: number;
  collection_month: number;
  promises_active_today: number;
  promises_broken_total: number;
  promises_kept_month: number;
  promises_given_month: number;
  ptp_conversion_month_pct: number;
  promises_auto_fulfilled_month: number;
  promise_fulfillment_rate_pct: number;
  active_managers: number;
  calls_today: number;
}

interface ManagerKPI {
  manager_id: number;
  manager_name: string;
  collection_amount: number;
  payments_count: number;
  promises_given: number;
  promises_kept: number;
  promises_broken: number;
  promises_auto_fulfilled: number;
  ptp_conversion_pct: number;
  calls_made: number;
  calls_reached: number;
  reach_rate_pct: number;
  queue_items_processed: number;
  tasks_completed: number;
}

interface BrokenPromise {
  promise_id: number;
  promise_date: string;
  amount: number;
  status: string;
  days_overdue: number;
  debtor_id: number;
  debtor_full_name: string;
  debtor_phone: string | null;
  debtor_score_tier: string | null;
  contract_number: string | null;
  manager_id: number | null;
  manager_name: string;
}

interface DailyPoint {
  date: string;
  amount: number;
  count: number;
}

const PERIOD_LABELS: Record<string, string> = {
  day: "Сегодня",
  week: "Неделя",
  month: "Месяц",
};

export default function ControlPanelPage() {
  const { user } = useAuth();
  const [summary, setSummary] = useState<Summary | null>(null);
  const [managers, setManagers] = useState<ManagerKPI[]>([]);
  const [broken, setBroken] = useState<BrokenPromise[]>([]);
  const [chart, setChart] = useState<DailyPoint[]>([]);
  const [period, setPeriod] = useState<"day" | "week" | "month">("day");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchAll = async (showSpinner = true) => {
    if (showSpinner) setLoading(true);
    try {
      const [s, m, b, c] = await Promise.all([
        apiClient.get("/analytics/control-panel"),
        apiClient.get("/analytics/manager-performance", { params: { period, source: "live" } }),
        apiClient.get("/analytics/broken-promises", { params: { limit: 50 } }),
        apiClient.get("/analytics/daily-collection", { params: { days: 30 } }),
      ]);
      setSummary(s.data);
      setManagers(m.data);
      setBroken(b.data);
      setChart(c.data);
    } catch (e: any) {
      toast.error(e.response?.data?.detail || "Ошибка загрузки");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchAll(); }, [period]);

  const recalcSnapshots = async () => {
    setRefreshing(true);
    try {
      const { data } = await apiClient.post("/analytics/snapshot/recalculate");
      toast.success(`Snapshots: ${data.snapshots_written}`);
      fetchAll(false);
    } catch (e: any) {
      toast.error(e.response?.data?.detail || "Ошибка");
    } finally {
      setRefreshing(false);
    }
  };

  if (loading) return <AppShell><Spinner /></AppShell>;
  if (!summary) return <AppShell><div className="p-8 text-center">Нет данных</div></AppShell>;

  const total_collection_chart = chart.reduce((s, p) => s + p.amount, 0);
  const top3 = managers.slice(0, 3);

  return (
    <AppShell>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="flex items-center gap-2 text-2xl font-bold">
              <Crown className="text-yellow-500" /> Контрольная панель
            </h1>
            <p className="text-sm text-gray-600">Мониторинг работы команды в реальном времени</p>
          </div>
          <button
            onClick={recalcSnapshots}
            disabled={refreshing}
            className="flex items-center gap-2 rounded border px-3 py-2 text-sm hover:bg-gray-50 disabled:opacity-50"
          >
            <RefreshCw size={14} className={refreshing ? "animate-spin" : ""} />
            {refreshing ? "Считаем..." : "Пересчитать KPI"}
          </button>
        </div>

        {/* Top KPI strip */}
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <div className="rounded-lg border bg-gradient-to-br from-green-50 to-emerald-50 p-4">
            <div className="flex items-center gap-2 text-green-700">
              <Banknote size={18} />
              <span className="text-xs font-bold uppercase">Сегодня собрано</span>
            </div>
            <div className="mt-1 text-2xl font-bold text-green-900">
              {summary.collection_today.toLocaleString("ru-RU")} ₸
            </div>
          </div>
          <div className="rounded-lg border bg-gradient-to-br from-blue-50 to-cyan-50 p-4">
            <div className="flex items-center gap-2 text-blue-700">
              <Calendar size={18} />
              <span className="text-xs font-bold uppercase">За неделю</span>
            </div>
            <div className="mt-1 text-2xl font-bold text-blue-900">
              {summary.collection_week.toLocaleString("ru-RU")} ₸
            </div>
          </div>
          <div className="rounded-lg border bg-gradient-to-br from-purple-50 to-fuchsia-50 p-4">
            <div className="flex items-center gap-2 text-purple-700">
              <TrendingUp size={18} />
              <span className="text-xs font-bold uppercase">За месяц</span>
            </div>
            <div className="mt-1 text-2xl font-bold text-purple-900">
              {summary.collection_month.toLocaleString("ru-RU")} ₸
            </div>
          </div>
          <div className="rounded-lg border bg-gradient-to-br from-yellow-50 to-orange-50 p-4">
            <div className="flex items-center gap-2 text-orange-700">
              <Trophy size={18} />
              <span className="text-xs font-bold uppercase">PTP Conversion</span>
            </div>
            <div className="mt-1 text-2xl font-bold text-orange-900">
              {summary.ptp_conversion_month_pct}%
            </div>
            <div className="text-xs text-gray-500">{summary.promises_kept_month} / {summary.promises_given_month} за месяц</div>
          </div>
        </div>

        {/* Promise health row */}
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <div className="rounded-lg border bg-white p-4">
            <div className="text-xs font-bold uppercase text-gray-600">Promise Fulfillment Rate</div>
            <div className={`mt-1 text-2xl font-bold ${
              summary.promise_fulfillment_rate_pct >= 60 ? "text-green-600" :
              summary.promise_fulfillment_rate_pct >= 30 ? "text-yellow-600" : "text-red-600"
            }`}>
              {summary.promise_fulfillment_rate_pct}%
            </div>
            <div className="text-xs text-gray-500">от всех завершённых обещаний</div>
          </div>
          <div className="rounded-lg border bg-white p-4">
            <div className="flex items-center gap-1 text-xs font-bold uppercase text-gray-600">
              <Sparkles size={12} className="text-blue-500" />
              Auto-Fulfilled (system)
            </div>
            <div className="mt-1 text-2xl font-bold text-blue-700">
              {summary.promises_auto_fulfilled_month}
            </div>
            <div className="text-xs text-gray-500">авто-закрыто платежами за месяц</div>
          </div>
          <div className="rounded-lg border bg-white p-4">
            <div className="flex items-center gap-1 text-xs font-bold uppercase text-gray-600">
              <AlertTriangle size={12} className="text-red-500" />
              Сорванных всего
            </div>
            <div className="mt-1 text-2xl font-bold text-red-600">{summary.promises_broken_total}</div>
            <div className="text-xs text-gray-500">требуют внимания</div>
          </div>
          <div className="rounded-lg border bg-white p-4">
            <div className="flex items-center gap-1 text-xs font-bold uppercase text-gray-600">
              <Phone size={12} className="text-cyan-500" />
              Звонков сегодня
            </div>
            <div className="mt-1 text-2xl font-bold text-cyan-700">{summary.calls_today}</div>
            <div className="text-xs text-gray-500">{summary.active_managers} менеджеров активны</div>
          </div>
        </div>

        {/* Daily collection chart */}
        <div className="rounded-lg border bg-white p-4">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-lg font-bold">Динамика сборов · 30 дней</h2>
            <div className="text-sm text-gray-500">
              Итого: <strong>{total_collection_chart.toLocaleString("ru-RU")} ₸</strong>
            </div>
          </div>
          <div style={{ width: "100%", height: 240 }}>
            <ResponsiveContainer>
              <BarChart data={chart}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => (v / 1000).toFixed(0) + "k"} />
                <Tooltip
                  formatter={(value: any) => [Number(value).toLocaleString("ru-RU") + " ₸", "Сумма"]}
                />
                <Bar dataKey="amount" fill="#10b981" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Period filter for leaderboard */}
        <div className="flex gap-2">
          {(["day", "week", "month"] as const).map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={`rounded px-4 py-1.5 text-sm font-medium ${
                period === p ? "bg-primary-600 text-white" : "bg-white border hover:bg-gray-50"
              }`}
            >
              {PERIOD_LABELS[p]}
            </button>
          ))}
        </div>

        {/* Top 3 podium */}
        {top3.length >= 1 && (
          <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
            {top3.map((m, i) => (
              <div
                key={m.manager_id}
                className={`rounded-lg border-2 p-4 ${
                  i === 0 ? "border-yellow-400 bg-yellow-50" :
                  i === 1 ? "border-gray-300 bg-gray-50" :
                  "border-orange-300 bg-orange-50"
                }`}
              >
                <div className="flex items-center gap-2">
                  <span className="text-2xl">{i === 0 ? "🥇" : i === 1 ? "🥈" : "🥉"}</span>
                  <div className="font-bold">{m.manager_name}</div>
                </div>
                <div className="mt-2 text-2xl font-bold">
                  {m.collection_amount.toLocaleString("ru-RU")} ₸
                </div>
                <div className="text-xs text-gray-600">
                  PTP {m.ptp_conversion_pct}% · {m.calls_made} звонков
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Leaderboard table */}
        <div className="rounded-lg border bg-white">
          <div className="border-b p-4 font-semibold">
            Leaderboard · {PERIOD_LABELS[period]}
          </div>
          {managers.length === 0 ? (
            <div className="p-8 text-center text-gray-500">Нет менеджеров</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 text-left text-xs uppercase text-gray-500">
                  <tr>
                    <th className="p-3">#</th>
                    <th className="p-3">Менеджер</th>
                    <th className="p-3 text-right">Собрано</th>
                    <th className="p-3 text-right">Платежей</th>
                    <th className="p-3 text-right">PTP %</th>
                    <th className="p-3 text-right">Дано / Сдержал / Сорвал</th>
                    <th className="p-3 text-right">Auto-fulfill</th>
                    <th className="p-3 text-right">Звонки</th>
                    <th className="p-3 text-right">Reach %</th>
                    <th className="p-3 text-right">Задач</th>
                  </tr>
                </thead>
                <tbody>
                  {managers.map((m, i) => (
                    <tr key={m.manager_id} className="border-t hover:bg-gray-50">
                      <td className="p-3 font-bold text-gray-400">{i + 1}</td>
                      <td className="p-3 font-medium">{m.manager_name}</td>
                      <td className="p-3 text-right font-bold text-green-700">
                        {m.collection_amount.toLocaleString("ru-RU")} ₸
                      </td>
                      <td className="p-3 text-right">{m.payments_count}</td>
                      <td className="p-3 text-right">
                        <span className={`rounded px-2 py-0.5 text-xs ${
                          m.ptp_conversion_pct >= 60 ? "bg-green-100 text-green-700" :
                          m.ptp_conversion_pct >= 30 ? "bg-yellow-100 text-yellow-700" :
                          "bg-red-100 text-red-700"
                        }`}>
                          {m.ptp_conversion_pct}%
                        </span>
                      </td>
                      <td className="p-3 text-right text-xs">
                        {m.promises_given} / <span className="text-green-600">{m.promises_kept}</span> / <span className="text-red-600">{m.promises_broken}</span>
                      </td>
                      <td className="p-3 text-right text-blue-600 font-semibold">{m.promises_auto_fulfilled}</td>
                      <td className="p-3 text-right">{m.calls_made}</td>
                      <td className="p-3 text-right">
                        <span className={`text-xs ${
                          m.reach_rate_pct >= 50 ? "text-green-600" : "text-orange-600"
                        }`}>{m.reach_rate_pct}%</span>
                      </td>
                      <td className="p-3 text-right">{m.tasks_completed}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Broken promises (Leakage) */}
        <div className="rounded-lg border bg-white">
          <div className="flex items-center justify-between border-b p-4">
            <div className="flex items-center gap-2 font-semibold">
              <AlertTriangle size={18} className="text-red-500" />
              Сорванные обещания (потери)
            </div>
            <span className="text-sm text-gray-500">{broken.length} записей</span>
          </div>
          {broken.length === 0 ? (
            <div className="p-8 text-center text-gray-500">Нет сорванных обещаний 🎉</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 text-left text-xs uppercase text-gray-500">
                  <tr>
                    <th className="p-3">Должник</th>
                    <th className="p-3 text-right">Обещано</th>
                    <th className="p-3">Дата</th>
                    <th className="p-3 text-right">Просрочка</th>
                    <th className="p-3">Менеджер</th>
                    <th className="p-3">Контакт</th>
                  </tr>
                </thead>
                <tbody>
                  {broken.map((b) => (
                    <tr key={b.promise_id} className="border-t hover:bg-gray-50">
                      <td className="p-3">
                        <div className="flex items-center gap-2">
                          {b.debtor_score_tier === "hot" && <Flame size={12} className="text-red-500" />}
                          <Link href={`/debtors/${b.debtor_id}`} className="font-medium text-primary-600 hover:underline">
                            {b.debtor_full_name}
                          </Link>
                        </div>
                      </td>
                      <td className="p-3 text-right font-semibold">
                        {b.amount.toLocaleString("ru-RU")} ₸
                      </td>
                      <td className="p-3 text-xs">{b.promise_date}</td>
                      <td className="p-3 text-right">
                        <span className="rounded bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">
                          {b.days_overdue}д
                        </span>
                      </td>
                      <td className="p-3 text-gray-700">{b.manager_name}</td>
                      <td className="p-3">
                        {b.debtor_phone && (
                          <a href={`tel:${b.debtor_phone}`} className="text-xs text-blue-600 hover:underline">
                            {b.debtor_phone}
                          </a>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
}
