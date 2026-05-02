"use client";
import { useEffect, useState } from "react";
import AppShell from "@/components/layout/AppShell";
import { apiClient } from "@/lib/api-client";
import toast from "react-hot-toast";
import { Spinner } from "@/components/ui";
import {
  PhoneCall, PhoneMissed, PhoneOff, CalendarClock,
  CheckCircle2, AlertTriangle, SkipForward, User, FileText, Banknote, History,
} from "lucide-react";

interface QueueItem {
  id: number;
  queue_id: number;
  debtor_id: number;
  contract_id: number | null;
  attempt_count: number;
  debtor_full_name: string | null;
  debtor_iin: string | null;
  debtor_phone_primary: string | null;
  debtor_phone_secondary: string | null;
  contract_number: string | null;
  total_debt: number | null;
}

interface MyProgress {
  manager_id: number;
  manager_name: string;
  total_assigned: number;
  completed_today: number;
  reached_today: number;
  not_reached_today: number;
  promises_today: number;
  pending: number;
}

const OUTCOMES = [
  { value: "reached", label: "Дозвонился", icon: PhoneCall, color: "bg-green-500 hover:bg-green-600" },
  { value: "promise", label: "Обещание", icon: CalendarClock, color: "bg-blue-500 hover:bg-blue-600" },
  { value: "callback", label: "Перезвонить", icon: PhoneCall, color: "bg-purple-500 hover:bg-purple-600" },
  { value: "not_reached", label: "Недозвон", icon: PhoneMissed, color: "bg-orange-500 hover:bg-orange-600" },
  { value: "refused", label: "Отказ", icon: PhoneOff, color: "bg-gray-500 hover:bg-gray-600" },
  { value: "wrong_number", label: "Не тот номер", icon: AlertTriangle, color: "bg-red-500 hover:bg-red-600" },
];

export default function CallQueuePage() {
  const [item, setItem] = useState<QueueItem | null>(null);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState<MyProgress | null>(null);
  const [showResult, setShowResult] = useState(false);
  const [tab, setTab] = useState<"active" | "history">("active");
  const [outcome, setOutcome] = useState<string>("");
  const [duration, setDuration] = useState<string>("");
  const [notes, setNotes] = useState<string>("");
  const [phoneUsed, setPhoneUsed] = useState<string>("");
  const [promiseAmount, setPromiseAmount] = useState<string>("");
  const [promiseDate, setPromiseDate] = useState<string>("");
  const [callbackAt, setCallbackAt] = useState<string>("");
  const [submitting, setSubmitting] = useState(false);

  const fetchProgress = async () => {
    try {
      const { data } = await apiClient.get("/call-queue/my-progress");
      setProgress(data);
    } catch {}
  };

  useEffect(() => { fetchProgress(); }, []);

  const takeNext = async () => {
    setLoading(true);
    try {
      const { data } = await apiClient.post("/call-queue/take-next", {});
      if (!data.item) {
        toast(data.message || "Очередь пуста");
        setItem(null);
      } else {
        setItem(data.item);
        setPhoneUsed(data.item.debtor_phone_primary || "");
      }
    } catch (e: any) {
      toast.error(e.response?.data?.detail || "Ошибка");
    } finally {
      setLoading(false);
    }
  };

  const releaseItem = async () => {
    if (!item) return;
    try {
      await apiClient.post(`/call-queue/release/${item.id}`);
      toast.success("Должник возвращён в очередь");
      setItem(null);
      fetchProgress();
    } catch (e: any) {
      toast.error(e.response?.data?.detail || "Не удалось пропустить");
    }
  };

  const openResult = (oc: string) => {
    setOutcome(oc);
    setShowResult(true);
  };

  const submitResult = async () => {
    if (!item || !outcome) return;
    if (outcome === "promise" && (!promiseAmount || !promiseDate)) {
      toast.error("Укажите сумму и дату обещания");
      return;
    }
    if (outcome === "callback" && !callbackAt) {
      toast.error("Укажите дату/время перезвона");
      return;
    }
    setSubmitting(true);
    try {
      const payload: any = {
        item_id: item.id,
        outcome,
        duration_seconds: duration ? parseInt(duration) : null,
        phone_number: phoneUsed,
        notes: notes || null,
      };
      if (outcome === "promise") {
        payload.promise_amount = parseFloat(promiseAmount);
        payload.promise_date = promiseDate;
      }
      if (outcome === "callback") {
        payload.callback_at = new Date(callbackAt).toISOString();
      }
      const { data } = await apiClient.post("/call-queue/submit-result", payload);
      toast.success(data.message);
      setShowResult(false);
      setItem(null);
      setOutcome("");
      setDuration("");
      setNotes("");
      setPromiseAmount("");
      setPromiseDate("");
      setCallbackAt("");
      fetchProgress();
    } catch (e: any) {
      toast.error(e.response?.data?.detail || "Ошибка");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AppShell>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">Автодозвон</h1>
          <div className="flex items-center gap-1 rounded-lg border border-gray-200 bg-gray-50 p-1">
            <button
              onClick={() => setTab("active")}
              className={
                tab === "active"
                  ? "flex items-center gap-2 rounded-md bg-white px-3 py-1.5 text-sm font-medium text-gray-900 shadow-sm"
                  : "flex items-center gap-2 rounded-md px-3 py-1.5 text-sm text-gray-600 hover:text-gray-900"
              }
            >
              <PhoneCall size={14} /> Очередь
            </button>
            <button
              onClick={() => setTab("history")}
              className={
                tab === "history"
                  ? "flex items-center gap-2 rounded-md bg-white px-3 py-1.5 text-sm font-medium text-gray-900 shadow-sm"
                  : "flex items-center gap-2 rounded-md px-3 py-1.5 text-sm text-gray-600 hover:text-gray-900"
              }
            >
              <History size={14} /> История
            </button>
          </div>
        </div>

        {tab === "history" ? (
          <CallHistoryTab />
        ) : (
          <>
        {/* My progress */}
        {progress && (
          <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
            <div className="rounded-lg border bg-white p-4">
              <div className="text-xs text-gray-500">Назначено всего</div>
              <div className="text-2xl font-bold">{progress.total_assigned}</div>
            </div>
            <div className="rounded-lg border bg-white p-4">
              <div className="text-xs text-gray-500">В очереди</div>
              <div className="text-2xl font-bold text-orange-600">{progress.pending}</div>
            </div>
            <div className="rounded-lg border bg-white p-4">
              <div className="text-xs text-gray-500">Дозвоны сегодня</div>
              <div className="text-2xl font-bold text-green-600">{progress.reached_today}</div>
            </div>
            <div className="rounded-lg border bg-white p-4">
              <div className="text-xs text-gray-500">Недозвоны сегодня</div>
              <div className="text-2xl font-bold text-orange-600">{progress.not_reached_today}</div>
            </div>
            <div className="rounded-lg border bg-white p-4">
              <div className="text-xs text-gray-500">Обещания сегодня</div>
              <div className="text-2xl font-bold text-blue-600">{progress.promises_today}</div>
            </div>
          </div>
        )}

        {/* Take next */}
        {!item ? (
          <div className="rounded-lg border bg-white p-12 text-center">
            <PhoneCall size={48} className="mx-auto mb-4 text-primary-600" />
            <h2 className="mb-2 text-xl font-semibold">Готовы к работе?</h2>
            <p className="mb-6 text-gray-600">Нажмите кнопку, чтобы взять следующего должника из очереди</p>
            <button
              onClick={takeNext}
              disabled={loading}
              className="rounded-lg bg-primary-600 px-8 py-4 text-lg font-medium text-white hover:bg-primary-700 disabled:opacity-50"
            >
              {loading ? <Spinner /> : "📞 Следующий звонок"}
            </button>
          </div>
        ) : (
          <div className="rounded-lg border-2 border-primary-300 bg-white p-6">
            <div className="mb-4 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="rounded-full bg-primary-100 px-3 py-1 text-sm font-medium text-primary-700">
                  Попытка #{item.attempt_count + 1}
                </span>
              </div>
              <button
                onClick={releaseItem}
                className="flex items-center gap-2 rounded-lg border px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50"
              >
                <SkipForward size={14} /> Пропустить
              </button>
            </div>

            <div className="mb-6 grid gap-4 md:grid-cols-2">
              <div>
                <div className="mb-2 flex items-center gap-2 text-gray-700">
                  <User size={18} /> <span className="font-semibold">{item.debtor_full_name}</span>
                </div>
                {item.debtor_iin && <div className="text-sm text-gray-500">ИИН: {item.debtor_iin}</div>}
                <div className="mt-3 space-y-1">
                  {item.debtor_phone_primary && (
                    <a href={`tel:${item.debtor_phone_primary}`} className="block text-lg font-semibold text-blue-600 hover:underline">
                      📱 {item.debtor_phone_primary}
                    </a>
                  )}
                  {item.debtor_phone_secondary && (
                    <a href={`tel:${item.debtor_phone_secondary}`} className="block text-blue-600 hover:underline">
                      ☎️ {item.debtor_phone_secondary}
                    </a>
                  )}
                </div>
              </div>

              <div className="rounded bg-gray-50 p-4">
                {item.contract_number && (
                  <div className="mb-2 flex items-center gap-2 text-sm">
                    <FileText size={14} /> Договор {item.contract_number}
                  </div>
                )}
                {item.total_debt && (
                  <div className="flex items-center gap-2 text-lg">
                    <Banknote size={18} className="text-red-600" />
                    <span className="font-bold">{Number(item.total_debt).toLocaleString("ru-RU")} ₸</span>
                  </div>
                )}
                <a
                  href={`/debtors/${item.debtor_id}`}
                  target="_blank"
                  className="mt-3 inline-block text-sm text-primary-600 hover:underline"
                >
                  Открыть карточку →
                </a>
              </div>
            </div>

            <div className="mb-2 text-sm font-medium text-gray-700">Результат звонка:</div>
            <div className="grid grid-cols-2 gap-2 md:grid-cols-3">
              {OUTCOMES.map((oc) => (
                <button
                  key={oc.value}
                  onClick={() => openResult(oc.value)}
                  className={`flex items-center justify-center gap-2 rounded-lg px-4 py-3 font-medium text-white ${oc.color}`}
                >
                  <oc.icon size={16} /> {oc.label}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Result modal */}
        {showResult && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
            <div className="w-full max-w-md rounded-lg bg-white p-6">
              <h3 className="mb-4 text-lg font-bold">
                Результат: {OUTCOMES.find((o) => o.value === outcome)?.label}
              </h3>

              <div className="space-y-3">
                <div>
                  <label className="block text-sm font-medium">Длительность (сек)</label>
                  <input
                    type="number"
                    value={duration}
                    onChange={(e) => setDuration(e.target.value)}
                    className="mt-1 w-full rounded border px-3 py-2"
                    placeholder="0"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium">Номер</label>
                  <input
                    value={phoneUsed}
                    onChange={(e) => setPhoneUsed(e.target.value)}
                    className="mt-1 w-full rounded border px-3 py-2"
                  />
                </div>

                {outcome === "promise" && (
                  <>
                    <div>
                      <label className="block text-sm font-medium">Сумма обещания (₸)</label>
                      <input
                        type="number"
                        value={promiseAmount}
                        onChange={(e) => setPromiseAmount(e.target.value)}
                        className="mt-1 w-full rounded border px-3 py-2"
                        required
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium">Дата обещания</label>
                      <input
                        type="date"
                        value={promiseDate}
                        onChange={(e) => setPromiseDate(e.target.value)}
                        className="mt-1 w-full rounded border px-3 py-2"
                        required
                      />
                    </div>
                  </>
                )}

                {outcome === "callback" && (
                  <div>
                    <label className="block text-sm font-medium">Когда перезвонить</label>
                    <input
                      type="datetime-local"
                      value={callbackAt}
                      onChange={(e) => setCallbackAt(e.target.value)}
                      className="mt-1 w-full rounded border px-3 py-2"
                      required
                    />
                  </div>
                )}

                <div>
                  <label className="block text-sm font-medium">Комментарий</label>
                  <textarea
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    rows={3}
                    className="mt-1 w-full rounded border px-3 py-2"
                  />
                </div>
              </div>

              <div className="mt-6 flex gap-2">
                <button
                  onClick={() => setShowResult(false)}
                  className="flex-1 rounded border px-4 py-2 hover:bg-gray-50"
                >
                  Отмена
                </button>
                <button
                  onClick={submitResult}
                  disabled={submitting}
                  className="flex-1 rounded bg-primary-600 px-4 py-2 font-medium text-white hover:bg-primary-700 disabled:opacity-50"
                >
                  {submitting ? <Spinner /> : "Записать"}
                </button>
              </div>
            </div>
          </div>
        )}
        </>
        )}
      </div>
    </AppShell>
  );
}

// ===========================================================================
// Tab: История моих звонков (CallLog filtered to current user via backend)
// ===========================================================================
function CallHistoryTab() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const today = new Date().toISOString().split("T")[0];
  const sevenAgo = new Date(Date.now() - 7 * 86400e3).toISOString().split("T")[0];
  const [dateFrom, setDateFrom] = useState(sevenAgo);
  const [dateTo, setDateTo] = useState(today);

  const load = async () => {
    setLoading(true);
    try {
      const { data: res } = await apiClient.get("/dashboard/calls-history", {
        params: { date_from: dateFrom, date_to: dateTo, page_size: 200 },
      });
      setData(res);
      setLoadError(null);
    } catch (err: any) {
      const msg = err?.response?.data?.detail || "Не удалось загрузить историю";
      setLoadError(msg);
      toast.error(msg, { id: "call-history-load" });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); /* eslint-disable-next-line */ }, [dateFrom, dateTo]);

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const reached = items.filter((c: any) => ["reached", "promise"].includes(c.outcome) || c.result === "reached").length;
  const reachRate = total ? Math.round((reached / total) * 100) : 0;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-3 rounded-lg border bg-white p-4">
        <label className="flex flex-col text-xs">
          <span className="mb-1 text-gray-500">С:</span>
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            className="rounded border px-2 py-1 text-sm"
          />
        </label>
        <label className="flex flex-col text-xs">
          <span className="mb-1 text-gray-500">По:</span>
          <input
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            className="rounded border px-2 py-1 text-sm"
          />
        </label>
        <button onClick={load} className="h-9 rounded bg-primary-600 px-4 text-sm font-medium text-white hover:bg-primary-700">
          Обновить
        </button>
      </div>

      <div className="grid grid-cols-3 gap-3">
        <div className="rounded-lg border bg-white p-4">
          <div className="text-xs text-gray-500">Всего звонков</div>
          <div className="text-2xl font-bold">{total}</div>
        </div>
        <div className="rounded-lg border bg-white p-4">
          <div className="text-xs text-gray-500">Дозвонов</div>
          <div className="text-2xl font-bold text-green-600">{reached}</div>
        </div>
        <div className="rounded-lg border bg-white p-4">
          <div className="text-xs text-gray-500">% дозвона</div>
          <div className="text-2xl font-bold text-blue-600">{reachRate}%</div>
        </div>
      </div>

      <div className="overflow-hidden rounded-lg border bg-white">
        {loading ? (
          <div className="p-8 text-center"><Spinner /></div>
        ) : loadError ? (
          <div className="p-8 text-center text-red-600">{loadError}</div>
        ) : items.length === 0 ? (
          <div className="p-8 text-center text-gray-500">Нет звонков за выбранный период</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-left text-xs uppercase text-gray-500">
              <tr>
                <th className="p-3">Дата/Время</th>
                <th className="p-3">Договор</th>
                <th className="p-3">Результат</th>
                <th className="p-3 text-right">Длительность</th>
                <th className="p-3">Заметки</th>
              </tr>
            </thead>
            <tbody>
              {items.map((c: any) => (
                <tr key={c.id} className="border-t hover:bg-gray-50">
                  <td className="p-3 text-xs">{new Date(c.called_at).toLocaleString("ru-RU")}</td>
                  <td className="p-3 text-xs">#{c.contract_id}</td>
                  <td className="p-3"><ResultBadge result={c.result} /></td>
                  <td className="p-3 text-right">{c.duration_seconds ?? "—"}с</td>
                  <td className="p-3 text-xs text-gray-600">{c.notes || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

function ResultBadge({ result }: { result: string }) {
  const map: Record<string, { label: string; cls: string }> = {
    reached: { label: "Дозвон", cls: "bg-green-100 text-green-700" },
    not_reached: { label: "Недозвон", cls: "bg-orange-100 text-orange-700" },
    no_answer: { label: "Не отвечает", cls: "bg-gray-100 text-gray-700" },
    refused: { label: "Отказ", cls: "bg-red-100 text-red-700" },
  };
  const v = map[result] || { label: result, cls: "bg-gray-100 text-gray-700" };
  return <span className={`rounded px-2 py-0.5 text-xs ${v.cls}`}>{v.label}</span>;
}
