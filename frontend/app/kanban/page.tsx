"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import AppShell from "@/components/layout/AppShell";
import { apiClient } from "@/lib/api-client";
import toast from "react-hot-toast";
import { Spinner } from "@/components/ui";

interface KanbanCard {
  id: number;
  full_name: string;
  iin: string;
  phone: string | null;
  total_debt: number;
  assigned_manager_id: number | null;
}

const COLUMNS: { key: string; label: string; color: string; bg: string }[] = [
  { key: "new", label: "Новый", color: "text-yellow-700", bg: "bg-yellow-50 border-yellow-200" },
  { key: "contact", label: "Контакт", color: "text-blue-700", bg: "bg-blue-50 border-blue-200" },
  { key: "promise", label: "Обещание", color: "text-purple-700", bg: "bg-purple-50 border-purple-200" },
  { key: "schedule", label: "График", color: "text-indigo-700", bg: "bg-indigo-50 border-indigo-200" },
  { key: "overdue", label: "Просрочка", color: "text-red-700", bg: "bg-red-50 border-red-200" },
  { key: "paid", label: "Оплачено", color: "text-green-700", bg: "bg-green-50 border-green-200" },
];

export default function KanbanPage() {
  const router = useRouter();
  const [data, setData] = useState<Record<string, KanbanCard[]>>({});
  const [loading, setLoading] = useState(true);
  const [draggedId, setDraggedId] = useState<number | null>(null);

  useEffect(() => { load(); }, []);

  const load = async () => {
    try {
      setLoading(true);
      const { data: res } = await apiClient.get("/kanban");
      setData(res);
    } catch { toast.error("Ошибка загрузки"); }
    finally { setLoading(false); }
  };

  const handleDragStart = (id: number) => setDraggedId(id);

  const handleDragOver = (e: React.DragEvent) => e.preventDefault();

  const handleDrop = async (e: React.DragEvent, newStatus: string) => {
    e.preventDefault();
    if (!draggedId) return;
    try {
      await apiClient.patch(`/kanban/debtor/${draggedId}/status`, { kanban_status: newStatus });
      toast.success("Статус обновлён");
      await load();
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || "Ошибка");
    }
    setDraggedId(null);
  };

  const fmt = (n: number) => Math.round(n).toLocaleString("ru-KZ") + " ₸";

  if (loading) return (
    <AppShell>
      <div className="flex justify-center py-20"><Spinner size="lg" /></div>
    </AppShell>
  );

  const totalCount = Object.values(data).reduce((s, arr) => s + arr.length, 0);

  return (
    <AppShell>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Канбан-доска</h1>
        <p className="text-sm text-gray-500 mt-1">Перетащите карточку, чтобы изменить статус. Всего: {totalCount}</p>
      </div>

      <div className="flex gap-3 overflow-x-auto pb-4">
        {COLUMNS.map(col => {
          const cards = data[col.key] || [];
          const sumDebt = cards.reduce((s, c) => s + c.total_debt, 0);
          return (
            <div key={col.key}
              onDragOver={handleDragOver}
              onDrop={(e) => handleDrop(e, col.key)}
              className={`min-w-[280px] w-80 shrink-0 rounded-2xl border-2 ${col.bg} ${draggedId ? "border-dashed" : ""}`}>
              <div className="px-4 py-3 border-b border-current/10">
                <div className="flex items-center justify-between">
                  <h3 className={`font-semibold text-sm ${col.color}`}>{col.label}</h3>
                  <span className={`text-xs font-bold px-2 py-0.5 rounded-full bg-white/60 ${col.color}`}>
                    {cards.length}
                  </span>
                </div>
                {sumDebt > 0 && (
                  <p className={`text-xs ${col.color} opacity-70 mt-1`}>Σ {fmt(sumDebt)}</p>
                )}
              </div>
              <div className="p-3 space-y-2 max-h-[calc(100vh-280px)] overflow-y-auto">
                {cards.length === 0 ? (
                  <div className="text-center text-xs text-gray-400 py-6">пусто</div>
                ) : cards.map(card => (
                  <div key={card.id}
                    draggable
                    onDragStart={() => handleDragStart(card.id)}
                    onClick={() => router.push(`/debtors/${card.id}`)}
                    className="bg-white rounded-xl p-3 shadow-sm hover:shadow-md transition-all cursor-grab active:cursor-grabbing border border-gray-100">
                    <p className="font-semibold text-sm text-gray-800 truncate">{card.full_name}</p>
                    <p className="text-xs text-gray-400 font-mono mt-0.5">{card.iin}</p>
                    {card.phone && <p className="text-xs text-gray-500 mt-1">{card.phone}</p>}
                    <div className={`text-sm font-bold mt-2 ${col.color}`}>
                      {fmt(card.total_debt)}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </AppShell>
  );
}
