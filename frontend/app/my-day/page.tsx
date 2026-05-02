"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import AppShell from "@/components/layout/AppShell";
import { apiClient } from "@/lib/api-client";
import { Spinner } from "@/components/ui";
import toast from "react-hot-toast";
import { useAuth } from "@/lib/auth-context";
import {
  Flame, Calendar, AlertCircle, CheckCircle2, Phone, Banknote,
  Sun, RefreshCw, Sparkles,
} from "lucide-react";

interface MyDayItem {
  type: "promise" | "task";
  kind: string;
  id: number;
  // promise fields
  promise_date?: string | null;
  promise_date_iso?: string | null;
  amount?: number | null;
  status?: string;
  notes?: string | null;
  contract_id?: number;
  contract_number?: string | null;
  // task fields
  title?: string;
  description?: string | null;
  task_type?: string;
  priority?: string;
  due_date?: string | null;
  due_date_iso?: string | null;
  // common
  debtor_id: number | null;
  debtor_full_name: string | null;
  debtor_phone: string | null;
  debtor_score?: number | null;
  debtor_score_tier?: string | null;
  is_hot: boolean;
  debt: number | null;
}

interface MyDay {
  manager_id: number;
  date: string;
  summary: {
    hot_count: number;
    today_count: number;
    overdue_count: number;
    promises_today_count: number;
    promises_today_amount: number;
    promises_overdue_count: number;
    tasks_today_count: number;
    tasks_overdue_count: number;
  };
  hot: MyDayItem[];
  today: MyDayItem[];
  overdue: MyDayItem[];
}

function ItemCard({ item, onCompleteTask }: { item: MyDayItem; onCompleteTask: (id: number) => void }) {
  const isPromise = item.type === "promise";
  const isOverdue = item.kind.includes("overdue");

  return (
    <div className={`rounded-lg border p-4 transition hover:shadow-sm ${
      item.is_hot ? "border-red-300 bg-red-50/40" : isOverdue ? "border-orange-300 bg-orange-50/30" : "border-gray-200 bg-white"
    }`}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          {/* Header — debtor + hot badge */}
          <div className="mb-2 flex items-center gap-2">
            {item.is_hot && (
              <span className="inline-flex items-center gap-1 rounded bg-red-100 px-2 py-0.5 text-xs font-bold text-red-700">
                <Flame size={11} /> HOT
              </span>
            )}
            {isOverdue && (
              <span className="inline-flex items-center gap-1 rounded bg-orange-100 px-2 py-0.5 text-xs font-bold text-orange-700">
                <AlertCircle size={11} /> просрочено
              </span>
            )}
            <span className={`inline-flex rounded px-2 py-0.5 text-xs font-medium ${
              isPromise ? "bg-blue-100 text-blue-700" : "bg-purple-100 text-purple-700"
            }`}>
              {isPromise ? "Обещание" : `Задача: ${item.task_type || "—"}`}
            </span>
            {!isPromise && item.priority === "high" && (
              <span className="inline-flex rounded bg-rose-100 px-2 py-0.5 text-xs font-medium text-rose-700">
                ⚡ срочно
              </span>
            )}
          </div>

          {/* Debtor */}
          {item.debtor_id ? (
            <Link href={`/debtors/${item.debtor_id}`} className="font-semibold text-gray-900 hover:text-primary-600 hover:underline">
              {item.debtor_full_name}
            </Link>
          ) : (
            <span className="font-semibold text-gray-900">{item.title || "—"}</span>
          )}

          {/* Body */}
          <div className="mt-2 space-y-1 text-sm text-gray-700">
            {isPromise && item.amount != null && (
              <div className="flex items-center gap-2">
                <Banknote size={14} className="text-green-600" />
                <span className="font-medium">{Number(item.amount).toLocaleString("ru-RU")} ₸</span>
                <span className="text-gray-500">на {item.promise_date}</span>
              </div>
            )}
            {!isPromise && item.title && (
              <div className="font-medium">{item.title}</div>
            )}
            {!isPromise && item.due_date && (
              <div className="text-xs text-gray-500">
                до {new Date(item.due_date).toLocaleString("ru-RU", { dateStyle: "short", timeStyle: "short" })}
              </div>
            )}
            {item.debt != null && item.debt > 0 && (
              <div className="text-xs text-gray-500">Общий долг: {Number(item.debt).toLocaleString("ru-RU")} ₸</div>
            )}
            {item.notes && <div className="mt-1 text-xs italic text-gray-500">{item.notes}</div>}
            {item.description && <div className="mt-1 text-xs italic text-gray-500">{item.description}</div>}
          </div>
        </div>

        <div className="flex flex-col gap-2">
          {item.debtor_phone && (
            <a
              href={`tel:${item.debtor_phone}`}
              className="inline-flex items-center gap-1 rounded bg-blue-50 px-3 py-1.5 text-xs text-blue-700 hover:bg-blue-100"
            >
              <Phone size={12} />
              {item.debtor_phone}
            </a>
          )}
          {!isPromise && (
            <button
              onClick={() => onCompleteTask(item.id)}
              className="inline-flex items-center gap-1 rounded bg-green-50 px-3 py-1.5 text-xs text-green-700 hover:bg-green-100"
            >
              <CheckCircle2 size={12} /> Закрыть
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function Section({
  title, icon: Icon, items, color, onCompleteTask, emptyText,
}: {
  title: string;
  icon: any;
  items: MyDayItem[];
  color: string;
  onCompleteTask: (id: number) => void;
  emptyText: string;
}) {
  return (
    <div>
      <div className="mb-3 flex items-center gap-2">
        <Icon size={20} className={color} />
        <h2 className="text-lg font-bold text-gray-900">{title}</h2>
        <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600">
          {items.length}
        </span>
      </div>
      {items.length === 0 ? (
        <div className="rounded-lg border border-dashed border-gray-200 p-6 text-center text-sm text-gray-400">
          {emptyText}
        </div>
      ) : (
        <div className="space-y-2">
          {items.map((it) => (
            <ItemCard key={`${it.kind}-${it.id}`} item={it} onCompleteTask={onCompleteTask} />
          ))}
        </div>
      )}
    </div>
  );
}

export default function MyDayPage() {
  const { user } = useAuth();
  const [data, setData] = useState<MyDay | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    try {
      const { data } = await apiClient.get("/tasks/my-day");
      setData(data);
    } catch (e: any) {
      toast.error(e.response?.data?.detail || "Ошибка загрузки");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, []);

  const completeTask = async (taskId: number) => {
    try {
      await apiClient.post(`/tasks/my-day/complete/${taskId}`);
      toast.success("Задача закрыта");
      fetchData();
    } catch (e: any) {
      toast.error(e.response?.data?.detail || "Ошибка");
    }
  };

  if (loading) return <AppShell><Spinner /></AppShell>;
  if (!data) return <AppShell><div className="p-8 text-center text-gray-500">Нет данных</div></AppShell>;

  const sum = data.summary;

  return (
    <AppShell>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="flex items-center gap-2 text-2xl font-bold">
              <Sun className="text-yellow-500" /> План на день
            </h1>
            <p className="text-sm text-gray-600">
              {user?.full_name} · {new Date(data.date).toLocaleDateString("ru-RU", {
                weekday: "long", day: "numeric", month: "long",
              })}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Link
              href="/promises?status=active"
              className="flex items-center gap-1.5 rounded border border-blue-200 bg-blue-50 px-3 py-2 text-sm text-blue-700 hover:bg-blue-100"
            >
              <Calendar size={14} /> Все мои обещания
            </Link>
            <Link
              href="/tasks?status=open"
              className="flex items-center gap-1.5 rounded border border-purple-200 bg-purple-50 px-3 py-2 text-sm text-purple-700 hover:bg-purple-100"
            >
              <CheckCircle2 size={14} /> Все мои задачи
            </Link>
            <button
              onClick={fetchData}
              className="flex items-center gap-2 rounded border px-3 py-2 text-sm hover:bg-gray-50"
            >
              <RefreshCw size={14} /> Обновить
            </button>
          </div>
        </div>

        {/* Summary */}
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <div className="rounded-lg border bg-red-50 p-4">
            <div className="flex items-center gap-2 text-red-600">
              <Flame size={18} /> <span className="text-xs font-bold uppercase">Горящие</span>
            </div>
            <div className="mt-1 text-2xl font-bold">{sum.hot_count}</div>
          </div>
          <div className="rounded-lg border bg-blue-50 p-4">
            <div className="flex items-center gap-2 text-blue-600">
              <Calendar size={18} /> <span className="text-xs font-bold uppercase">На сегодня</span>
            </div>
            <div className="mt-1 text-2xl font-bold">{sum.today_count}</div>
            <div className="text-xs text-gray-500">из них обещаний: {sum.promises_today_count}</div>
          </div>
          <div className="rounded-lg border bg-orange-50 p-4">
            <div className="flex items-center gap-2 text-orange-600">
              <AlertCircle size={18} /> <span className="text-xs font-bold uppercase">Просроченные</span>
            </div>
            <div className="mt-1 text-2xl font-bold">{sum.overdue_count}</div>
          </div>
          <div className="rounded-lg border bg-green-50 p-4">
            <div className="flex items-center gap-2 text-green-600">
              <Banknote size={18} /> <span className="text-xs font-bold uppercase">Сумма обещаний</span>
            </div>
            <div className="mt-1 text-xl font-bold">
              {Number(sum.promises_today_amount || 0).toLocaleString("ru-RU")} ₸
            </div>
          </div>
        </div>

        {/* Sections */}
        <Section
          title="🔥 Горящие (HOT)"
          icon={Flame}
          color="text-red-600"
          items={data.hot}
          onCompleteTask={completeTask}
          emptyText="Нет горящих задач — отличная работа!"
        />
        <Section
          title="📅 На сегодня"
          icon={Calendar}
          color="text-blue-600"
          items={data.today}
          onCompleteTask={completeTask}
          emptyText="Нет задач на сегодня"
        />
        <Section
          title="⚠️ Просроченные"
          icon={AlertCircle}
          color="text-orange-600"
          items={data.overdue}
          onCompleteTask={completeTask}
          emptyText="Просроченных нет — браво!"
        />

        {sum.hot_count === 0 && sum.today_count === 0 && sum.overdue_count === 0 && (
          <div className="rounded-lg border-2 border-dashed border-green-200 bg-green-50 p-8 text-center">
            <Sparkles size={32} className="mx-auto mb-3 text-green-600" />
            <h3 className="text-lg font-bold text-green-800">Все задачи выполнены</h3>
            <p className="text-sm text-green-700">Загляните в очередь обзвона или приоритет взыскания.</p>
          </div>
        )}
      </div>
    </AppShell>
  );
}
