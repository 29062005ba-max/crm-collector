"use client";
import { useState, useEffect } from "react";
import { Activity, AlertCircle, CheckCircle2, Clock, Play, RefreshCw } from "lucide-react";
import { apiClient } from "@/lib/api-client";

interface Job {
  id: number;
  task_id: string;
  task_name: string;
  queue: string;
  status: string;
  attempt: number;
  company_id: number | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  error: string | null;
}

interface Stats {
  window_hours: number;
  stats: Record<string, Record<string, number>>;
}

const STATUS_COLORS: Record<string, string> = {
  pending: "bg-gray-100 text-gray-700",
  running: "bg-blue-100 text-blue-700",
  success: "bg-green-100 text-green-700",
  failed: "bg-red-100 text-red-700",
  retry: "bg-yellow-100 text-yellow-700",
  dead_letter: "bg-red-200 text-red-900 font-bold",
};

const STATUS_ICONS: Record<string, any> = {
  pending: Clock,
  running: Play,
  success: CheckCircle2,
  failed: AlertCircle,
  retry: RefreshCw,
  dead_letter: AlertCircle,
};

export default function AdminJobsPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [queueFilter, setQueueFilter] = useState<string>("");

  const load = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (statusFilter) params.append("status", statusFilter);
      if (queueFilter) params.append("queue", queueFilter);
      const [j, s] = await Promise.all([
        apiClient.get(`/admin/jobs?${params.toString()}`),
        apiClient.get("/admin/jobs/stats?hours=24"),
      ]);
      setJobs(j.data);
      setStats(s.data);
    } catch (e) {
      console.error("Failed to load jobs", e);
    }
    setLoading(false);
  };

  useEffect(() => {
    load();
    const interval = setInterval(load, 10000); // refresh every 10s
    return () => clearInterval(interval);
  }, [statusFilter, queueFilter]);

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Activity className="h-6 w-6" />
          Background Jobs Monitor
        </h1>
        <button
          onClick={load}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          <RefreshCw className="h-4 w-4" /> Обновить
        </button>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          {Object.entries(stats.stats).map(([queue, statuses]) => {
            const total = Object.values(statuses).reduce((a, b) => a + b, 0);
            const failed = (statuses.failed || 0) + (statuses.dead_letter || 0);
            return (
              <div key={queue} className="bg-white p-4 rounded-lg shadow border">
                <div className="text-xs text-gray-500 uppercase tracking-wide">{queue}</div>
                <div className="text-3xl font-bold mt-1">{total}</div>
                <div className="text-xs mt-2 space-y-1">
                  {Object.entries(statuses).map(([s, n]) => (
                    <div key={s} className="flex justify-between">
                      <span className="text-gray-600">{s}:</span>
                      <span className={failed > 0 && (s === "failed" || s === "dead_letter") ? "text-red-600 font-bold" : ""}>
                        {n}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Filters */}
      <div className="flex gap-3">
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="border rounded px-3 py-1.5"
        >
          <option value="">All statuses</option>
          {["pending", "running", "success", "failed", "retry", "dead_letter"].map(s => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
        <select
          value={queueFilter}
          onChange={(e) => setQueueFilter(e.target.value)}
          className="border rounded px-3 py-1.5"
        >
          <option value="">All queues</option>
          {["workflow_queue", "notification_queue", "schedule_queue", "kpi_queue", "default", "dead_letter_queue"].map(q => (
            <option key={q} value={q}>{q}</option>
          ))}
        </select>
      </div>

      {/* Jobs table */}
      <div className="bg-white rounded-lg shadow overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="px-4 py-3 text-left">Task</th>
              <th className="px-4 py-3 text-left">Queue</th>
              <th className="px-4 py-3 text-left">Status</th>
              <th className="px-4 py-3 text-left">Attempt</th>
              <th className="px-4 py-3 text-left">Company</th>
              <th className="px-4 py-3 text-left">Created</th>
              <th className="px-4 py-3 text-left">Duration</th>
              <th className="px-4 py-3 text-left">Error</th>
            </tr>
          </thead>
          <tbody>
            {loading && jobs.length === 0 ? (
              <tr><td colSpan={8} className="text-center py-8 text-gray-500">Loading…</td></tr>
            ) : jobs.length === 0 ? (
              <tr><td colSpan={8} className="text-center py-8 text-gray-500">No jobs found</td></tr>
            ) : (
              jobs.map(job => {
                const Icon = STATUS_ICONS[job.status] || Clock;
                const duration = job.started_at && job.completed_at
                  ? `${((new Date(job.completed_at).getTime() - new Date(job.started_at).getTime()) / 1000).toFixed(1)}s`
                  : "—";
                return (
                  <tr key={job.id} className="border-b hover:bg-gray-50">
                    <td className="px-4 py-2 font-mono text-xs">{job.task_name.split('.').slice(-1)[0]}</td>
                    <td className="px-4 py-2 text-xs">{job.queue}</td>
                    <td className="px-4 py-2">
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs ${STATUS_COLORS[job.status] || "bg-gray-100"}`}>
                        <Icon className="h-3 w-3" /> {job.status}
                      </span>
                    </td>
                    <td className="px-4 py-2">{job.attempt}</td>
                    <td className="px-4 py-2">{job.company_id ?? "—"}</td>
                    <td className="px-4 py-2 text-xs">{new Date(job.created_at).toLocaleString("ru-KZ")}</td>
                    <td className="px-4 py-2 text-xs">{duration}</td>
                    <td className="px-4 py-2 text-xs text-red-600 max-w-md truncate" title={job.error || ""}>{job.error || "—"}</td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
