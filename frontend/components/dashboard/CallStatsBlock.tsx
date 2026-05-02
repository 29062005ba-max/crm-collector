"use client";
import { useEffect, useState } from "react";
import { apiClient } from "@/lib/api-client";
import { PhoneCall, PhoneMissed, CalendarClock, TrendingUp } from "lucide-react";

interface CallStats {
  total_calls_today: number;
  reached_today: number;
  not_reached_today: number;
  promises_after_call_today: number;
  reach_rate_percent: number;
}

export default function CallStatsBlock() {
  const [stats, setStats] = useState<CallStats | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const { data } = await apiClient.get("/call-queue/dashboard-stats");
        setStats(data);
      } catch {}
    };
    load();
    const t = setInterval(load, 60000);
    return () => clearInterval(t);
  }, []);

  if (!stats) return null;

  const cards = [
    { label: "Звонков сегодня", value: stats.total_calls_today, icon: PhoneCall, color: "text-blue-600", bg: "bg-blue-50" },
    { label: "Дозвонов", value: stats.reached_today, icon: PhoneCall, color: "text-green-600", bg: "bg-green-50" },
    { label: "Недозвонов", value: stats.not_reached_today, icon: PhoneMissed, color: "text-orange-600", bg: "bg-orange-50" },
    { label: "Обещаний после звонка", value: stats.promises_after_call_today, icon: CalendarClock, color: "text-purple-600", bg: "bg-purple-50" },
    { label: "Эффективность дозвона", value: `${stats.reach_rate_percent}%`, icon: TrendingUp, color: "text-indigo-600", bg: "bg-indigo-50" },
  ];

  return (
    <div>
      <h2 className="mb-3 text-lg font-semibold text-gray-800">📞 Активность звонков сегодня</h2>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
        {cards.map((c) => (
          <div key={c.label} className={`rounded-lg border ${c.bg} p-4`}>
            <div className="flex items-center justify-between">
              <c.icon className={c.color} size={20} />
            </div>
            <div className="mt-2 text-2xl font-bold text-gray-900">{c.value}</div>
            <div className="text-xs text-gray-600">{c.label}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
