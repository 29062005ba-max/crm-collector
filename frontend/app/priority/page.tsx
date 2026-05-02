"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import AppShell from "@/components/layout/AppShell";
import { apiClient } from "@/lib/api-client";
import { Spinner } from "@/components/ui";
import toast from "react-hot-toast";
import { useAuth } from "@/lib/auth-context";
import { Flame, Snowflake, Thermometer, RefreshCw, Phone } from "lucide-react";

interface PriorityDebtor {
  id: number;
  iin: string;
  full_name: string;
  phone_primary: string | null;
  score: number | null;
  score_tier: string | null;
  score_calculated_at: string | null;
  kanban_status: string;
  total_debt: number;
  manager_name: string | null;
  manager_id: number | null;
}

interface TierSummary {
  hot: number;
  medium: number;
  low: number;
  unscored: number;
}

const TIER_LABELS: Record<string, string> = {
  hot: "Горячий",
  medium: "Средний",
  low: "Низкий",
};

const tierStyle = (t: string | null) => {
  switch (t) {
    case "hot":
      return { bg: "bg-red-100", text: "text-red-800", dot: "bg-red-500", icon: Flame };
    case "medium":
      return { bg: "bg-yellow-100", text: "text-yellow-800", dot: "bg-yellow-500", icon: Thermometer };
    case "low":
      return { bg: "bg-blue-100", text: "text-blue-800", dot: "bg-blue-500", icon: Snowflake };
    default:
      return { bg: "bg-gray-100", text: "text-gray-600", dot: "bg-gray-400", icon: Snowflake };
  }
};

export default function PriorityPage() {
  const { user } = useAuth();
  const [debtors, setDebtors] = useState<PriorityDebtor[]>([]);
  const [summary, setSummary] = useState<TierSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [tier, setTier] = useState<string>("");
  const [onlyMine, setOnlyMine] = useState(false);
  const [recalculating, setRecalculating] = useState(false);

  const isManager = (user?.role || "").toUpperCase() === "MANAGER";
  const canRecalculate = ["ADMIN", "HEAD"].includes((user?.role || "").toUpperCase());

  const fetchData = async () => {
    setLoading(true);
    try {
      const params: any = { limit: 500 };
      if (tier) params.tier = tier;
      if (onlyMine || isManager) params.only_mine = true;

      const [list, sum] = await Promise.all([
        apiClient.get("/scoring/priority", { params }),
        apiClient.get("/scoring/summary"),
      ]);
      setDebtors(list.data);
      setSummary(sum.data);
    } catch (e: any) {
      toast.error(e.response?.data?.detail || "Ошибка");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, [tier, onlyMine]);

  const recalculateAll = async () => {
    if (!confirm("Пересчитать скоринг всех должников? Может занять минуту.")) return;
    setRecalculating(true);
    try {
      const { data } = await apiClient.post("/scoring/recalculate");
      toast.success(`Пересчитано: ${data.updated}`);
      fetchData();
    } catch (e: any) {
      toast.error(e.response?.data?.detail || "Ошибка");
    } finally {
      setRecalculating(false);
    }
  };

  return (
    <AppShell>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">🔥 Приоритет взыскания</h1>
            <p className="text-sm text-gray-600">Должники, отсортированные по вероятности оплаты</p>
          </div>
          {canRecalculate && (
            <button
              onClick={recalculateAll}
              disabled={recalculating}
              className="flex items-center gap-2 rounded border px-3 py-2 text-sm hover:bg-gray-50 disabled:opacity-50"
            >
              <RefreshCw size={14} className={recalculating ? "animate-spin" : ""} />
              {recalculating ? "Считаем..." : "Пересчитать"}
            </button>
          )}
        </div>

        {/* Summary */}
        {summary && (
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <button
              onClick={() => setTier(tier === "hot" ? "" : "hot")}
              className={`rounded-lg border p-4 text-left transition ${
                tier === "hot" ? "border-red-400 bg-red-50" : "bg-white hover:bg-gray-50"
              }`}
            >
              <div className="flex items-center gap-2 text-red-600">
                <Flame size={18} /> <span className="text-xs font-semibold uppercase">Горячий</span>
              </div>
              <div className="mt-1 text-2xl font-bold">{summary.hot}</div>
              <div className="text-xs text-gray-500">высокая вероятность оплаты</div>
            </button>
            <button
              onClick={() => setTier(tier === "medium" ? "" : "medium")}
              className={`rounded-lg border p-4 text-left transition ${
                tier === "medium" ? "border-yellow-400 bg-yellow-50" : "bg-white hover:bg-gray-50"
              }`}
            >
              <div className="flex items-center gap-2 text-yellow-700">
                <Thermometer size={18} /> <span className="text-xs font-semibold uppercase">Средний</span>
              </div>
              <div className="mt-1 text-2xl font-bold">{summary.medium}</div>
              <div className="text-xs text-gray-500">нужна работа</div>
            </button>
            <button
              onClick={() => setTier(tier === "low" ? "" : "low")}
              className={`rounded-lg border p-4 text-left transition ${
                tier === "low" ? "border-blue-400 bg-blue-50" : "bg-white hover:bg-gray-50"
              }`}
            >
              <div className="flex items-center gap-2 text-blue-700">
                <Snowflake size={18} /> <span className="text-xs font-semibold uppercase">Низкий</span>
              </div>
              <div className="mt-1 text-2xl font-bold">{summary.low}</div>
              <div className="text-xs text-gray-500">мало шансов</div>
            </button>
            <div className="rounded-lg border bg-gray-50 p-4">
              <div className="text-xs font-semibold uppercase text-gray-600">Без оценки</div>
              <div className="mt-1 text-2xl font-bold text-gray-700">{summary.unscored}</div>
              <div className="text-xs text-gray-500">нужен пересчёт</div>
            </div>
          </div>
        )}

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-3 rounded-lg border bg-white p-3">
          <button
            onClick={() => setTier("")}
            className={`rounded px-3 py-1 text-sm ${
              tier === "" ? "bg-primary-600 text-white" : "bg-gray-100 hover:bg-gray-200"
            }`}
          >
            Все
          </button>
          {!isManager && (
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={onlyMine} onChange={(e) => setOnlyMine(e.target.checked)} />
              Только мои
            </label>
          )}
          <span className="ml-auto text-sm text-gray-500">{debtors.length} должников</span>
        </div>

        {/* Table */}
        {loading ? (
          <div className="p-12 text-center"><Spinner /></div>
        ) : (
          <div className="overflow-hidden rounded-lg border bg-white">
            <table className="w-full">
              <thead className="bg-gray-50 text-left text-xs uppercase text-gray-500">
                <tr>
                  <th className="p-3">Балл</th>
                  <th className="p-3">Категория</th>
                  <th className="p-3">Должник</th>
                  <th className="p-3">Телефон</th>
                  <th className="p-3 text-right">Долг</th>
                  <th className="p-3">Менеджер</th>
                  <th className="p-3">Канбан</th>
                </tr>
              </thead>
              <tbody className="text-sm">
                {debtors.map((d) => {
                  const s = tierStyle(d.score_tier);
                  return (
                    <tr key={d.id} className="border-t hover:bg-gray-50">
                      <td className="p-3">
                        <div className="flex items-center gap-2">
                          <span className={`h-2 w-2 rounded-full ${s.dot}`} />
                          <span className="font-mono text-lg font-bold">{d.score ?? "—"}</span>
                        </div>
                      </td>
                      <td className="p-3">
                        <span className={`inline-flex items-center gap-1 rounded px-2 py-0.5 text-xs font-medium ${s.bg} ${s.text}`}>
                          <s.icon size={12} />
                          {d.score_tier ? TIER_LABELS[d.score_tier] : "—"}
                        </span>
                      </td>
                      <td className="p-3">
                        <Link href={`/debtors/${d.id}`} className="font-medium text-primary-600 hover:underline">
                          {d.full_name}
                        </Link>
                        <div className="text-xs text-gray-500">{d.iin}</div>
                      </td>
                      <td className="p-3">
                        {d.phone_primary ? (
                          <a href={`tel:${d.phone_primary}`} className="flex items-center gap-1 text-blue-600 hover:underline">
                            <Phone size={12} />
                            {d.phone_primary}
                          </a>
                        ) : (
                          <span className="text-gray-400">нет</span>
                        )}
                      </td>
                      <td className="p-3 text-right font-mono">{d.total_debt.toLocaleString("ru-RU")} ₸</td>
                      <td className="p-3 text-gray-600">{d.manager_name || "—"}</td>
                      <td className="p-3 text-xs text-gray-500">{d.kanban_status}</td>
                    </tr>
                  );
                })}
                {debtors.length === 0 && (
                  <tr><td colSpan={7} className="p-8 text-center text-gray-500">Нет данных</td></tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </AppShell>
  );
}
