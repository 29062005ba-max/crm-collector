"use client";
import { useEffect, useState, useRef } from "react";
import { Bell, X, Check } from "lucide-react";
import { useRouter } from "next/navigation";
import { apiClient } from "@/lib/api-client";

interface Notification {
  id: number;
  type: string;
  title: string;
  message: string | null;
  link: string | null;
  is_read: boolean;
  related_debtor_id: number | null;
  created_at: string;
}

const TYPE_ICONS: Record<string, string> = {
  promise_overdue: "⚠️",
  schedule_overdue: "🚨",
  task_assigned: "📋",
  payment_received: "💰",
};

export default function NotificationBell() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<Notification[]>([]);
  const [count, setCount] = useState(0);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadCount();
    const interval = setInterval(loadCount, 30000); // every 30s
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const loadCount = async () => {
    try {
      const { data } = await apiClient.get("/notifications/unread-count");
      setCount(data.count);
    } catch {}
  };

  const loadItems = async () => {
    try {
      const { data } = await apiClient.get("/notifications", { params: { limit: 20 } });
      setItems(data);
    } catch {}
  };

  const toggle = () => {
    if (!open) loadItems();
    setOpen(!open);
  };

  const markRead = async (id: number) => {
    try {
      await apiClient.post(`/notifications/${id}/read`);
      setItems(items.map(n => n.id === id ? { ...n, is_read: true } : n));
      setCount(c => Math.max(0, c - 1));
    } catch {}
  };

  const markAllRead = async () => {
    try {
      await apiClient.post("/notifications/mark-all-read");
      setItems(items.map(n => ({ ...n, is_read: true })));
      setCount(0);
    } catch {}
  };

  const handleClick = (n: Notification) => {
    if (!n.is_read) markRead(n.id);
    if (n.link) router.push(n.link);
    setOpen(false);
  };

  const ago = (dateStr: string) => {
    const diff = (Date.now() - new Date(dateStr).getTime()) / 1000;
    if (diff < 60) return "только что";
    if (diff < 3600) return `${Math.floor(diff / 60)} мин назад`;
    if (diff < 86400) return `${Math.floor(diff / 3600)} ч назад`;
    return `${Math.floor(diff / 86400)} дн назад`;
  };

  return (
    <div ref={ref} className="relative">
      <button onClick={toggle}
        className="relative p-2 rounded-lg hover:bg-gray-100 transition-colors"
        title="Уведомления">
        <Bell size={20} className="text-gray-600" />
        {count > 0 && (
          <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs font-bold rounded-full min-w-[18px] h-[18px] flex items-center justify-center px-1">
            {count > 9 ? "9+" : count}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-96 bg-white rounded-xl shadow-2xl border border-gray-100 z-50 overflow-hidden">
          <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
            <div className="font-semibold text-gray-800">Уведомления</div>
            <div className="flex items-center gap-2">
              {count > 0 && (
                <button onClick={markAllRead}
                  className="text-xs text-blue-600 hover:underline flex items-center gap-1">
                  <Check size={12} /> Прочитать все
                </button>
              )}
              <button onClick={() => setOpen(false)}>
                <X size={16} className="text-gray-400 hover:text-gray-600" />
              </button>
            </div>
          </div>
          <div className="max-h-96 overflow-y-auto">
            {items.length === 0 ? (
              <div className="px-4 py-12 text-center text-sm text-gray-400">Нет уведомлений</div>
            ) : items.map(n => (
              <button key={n.id} onClick={() => handleClick(n)}
                className={`w-full text-left px-4 py-3 border-b border-gray-50 last:border-0 hover:bg-gray-50 transition-colors flex gap-3 ${!n.is_read ? "bg-blue-50/50" : ""}`}>
                <div className="text-xl shrink-0 mt-0.5">{TYPE_ICONS[n.type] || "📌"}</div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p className={`text-sm truncate ${!n.is_read ? "font-semibold text-gray-900" : "text-gray-600"}`}>{n.title}</p>
                    {!n.is_read && <span className="w-2 h-2 bg-blue-600 rounded-full shrink-0" />}
                  </div>
                  {n.message && <p className="text-xs text-gray-500 truncate mt-0.5">{n.message}</p>}
                  <p className="text-xs text-gray-400 mt-1">{ago(n.created_at)}</p>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
