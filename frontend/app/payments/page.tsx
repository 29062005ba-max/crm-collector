"use client";
import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import AppShell from "@/components/layout/AppShell";
import { PageHeader, Spinner } from "@/components/ui";
import { apiClient } from "@/lib/api-client";
import { formatDate, formatMoney } from "@/lib/utils";
import { useAuth } from "@/lib/auth-context";
import { userService } from "@/services/api";
import { X } from "lucide-react";
import toast from "react-hot-toast";

const SOURCE_LABELS: Record<string, string> = {
  cash: "Наличные",
  card: "Внутр. ПТ",
  bank: "Банк",
  court: "Судебный",
};

export default function PaymentsPage() {
  const router = useRouter();
  const { user } = useAuth();
  const isManager = user?.role?.toUpperCase() === "MANAGER";
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [managerFilter, setManagerFilter] = useState("");
  const [sourceFilter, setSourceFilter] = useState("own"); // own = свои (без bank)
  const [managers, setManagers] = useState<any[]>([]);
  const [page, setPage] = useState(1);
  const [receiptModal, setReceiptModal] = useState<any>(null);
  const [dateFrom, setDateFrom] = useState(() => {
    const d = new Date(); d.setDate(1);
    return d.toISOString().slice(0, 10);
  });
  const [dateTo, setDateTo] = useState(() => new Date().toISOString().slice(0, 10));

  useEffect(() => {
    if (!isManager) userService.list().then((d: any) => setManagers(d.items || d)).catch(() => {});
  }, [isManager]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params: any = { page, page_size: 200, date_from: dateFrom, date_to: dateTo };
      if (managerFilter) params.manager_id = parseInt(managerFilter);
      const { data: res } = await apiClient.get("/payments/all", { params });
      setData(res);
      setLoadError(null);
    } catch (err: any) {
      const msg = err?.response?.data?.detail || "Не удалось загрузить платежи";
      setLoadError(msg);
      toast.error(msg, { id: "payments-load" });
    }
    finally { setLoading(false); }
  }, [page, dateFrom, dateTo, managerFilter]);

  useEffect(() => { load(); }, [load]);

  const allItems = data?.items ?? [];

  // Фильтр по источнику
  const items = allItems.filter((p: any) => {
    if (sourceFilter === "own") return p.source !== "bank";  // свои - без банковских
    if (sourceFilter === "all") return true;
    if (sourceFilter) return p.source === sourceFilter;
    return true;
  });

  const total = items.length;
  const totalAmount = items.reduce((s: number, p: any) => s + (Number(p.amount) || 0), 0);

  // Подсчёт по источникам (для статистики)
  const bySource = allItems.reduce((acc: any, p: any) => {
    const src = p.source || "other";
    if (!acc[src]) acc[src] = { count: 0, sum: 0 };
    acc[src].count++;
    acc[src].sum += Number(p.amount) || 0;
    return acc;
  }, {});

  return (
    <AppShell>
      <PageHeader title="Платежи" subtitle={`Показано: ${total} из ${allItems.length}`} />

      <div className="card mb-4 p-3">
        <div className="flex flex-wrap gap-2 items-center">
          <div className="flex items-center gap-1">
            <label className="text-sm text-gray-500">С:</label>
            <input type="date" value={dateFrom} onChange={(e) => { setDateFrom(e.target.value); setPage(1); }} className="input h-9 w-36 text-sm" />
          </div>
          <div className="flex items-center gap-1">
            <label className="text-sm text-gray-500">По:</label>
            <input type="date" value={dateTo} onChange={(e) => { setDateTo(e.target.value); setPage(1); }} className="input h-9 w-36 text-sm" />
          </div>
          <select className="input h-9 text-sm w-44" value={sourceFilter} onChange={(e) => setSourceFilter(e.target.value)}>
            <option value="own">Свои (без банковских)</option>
            <option value="all">Все источники</option>
            <option value="cash">Только наличные</option>
            <option value="card">Только внутр. ПТ</option>
            <option value="bank">Только банковские</option>
            <option value="court">Только судебные</option>
          </select>
          {!isManager && managers.length > 0 && (
            <select className="input h-9 text-sm w-44" value={managerFilter} onChange={(e) => { setManagerFilter(e.target.value); setPage(1); }}>
              <option value="">Все менеджеры</option>
              {managers.filter((m: any) => ["MANAGER","HEAD"].includes((m.role||"").toUpperCase())).map((m: any) => (
                <option key={m.id} value={m.id}>{m.full_name}</option>
              ))}
            </select>
          )}
        </div>
      </div>

      <div className="mb-4 grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="card p-3 text-center">
          <p className="text-xs text-gray-500">Количество</p>
          <p className="text-2xl font-bold">{total}</p>
        </div>
        <div className="card p-3 text-center">
          <p className="text-xs text-gray-500">{sourceFilter === "own" ? "Свои (наличные/ПТ/суд)" : "Итого сумма"}</p>
          <p className="text-xl font-bold text-green-700">{formatMoney(totalAmount)}</p>
        </div>
        <div className="card p-3 text-center">
          <p className="text-xs text-gray-500">Наличные</p>
          <p className="text-sm font-bold text-blue-700">{formatMoney(bySource.cash?.sum || 0)}</p>
          <p className="text-xs text-gray-400">{bySource.cash?.count || 0} шт.</p>
        </div>
        <div className="card p-3 text-center">
          <p className="text-xs text-gray-500">Банковские</p>
          <p className="text-sm font-bold text-gray-500">{formatMoney(bySource.bank?.sum || 0)}</p>
          <p className="text-xs text-gray-400">{bySource.bank?.count || 0} шт.</p>
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center py-12"><Spinner size="lg" /></div>
      ) : (
        <div className="card overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50 text-xs font-semibold text-gray-500 uppercase">
                <th className="px-4 py-3 text-left">Должник</th>
                <th className="px-4 py-3 text-left">Договор</th>
                <th className="px-4 py-3 text-left">Дата</th>
                <th className="px-4 py-3 text-right">Сумма</th>
                <th className="px-4 py-3 text-left">Источник</th>
                <th className="px-4 py-3 text-left">Менеджер</th>
                <th className="px-4 py-3 text-center">Чек</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {items.length === 0 ? (
                <tr><td colSpan={7} className="py-8 text-center text-gray-400">Нет платежей за период</td></tr>
              ) : items.map((p: any) => (
                <tr key={p.id} className="hover:bg-gray-50 cursor-pointer" onClick={() => router.push(`/debtors/${p.debtor_id}`)}>
                  <td className="px-4 py-3 font-medium">{p.debtor_name}</td>
                  <td className="px-4 py-3 font-mono text-xs text-gray-500">{p.contract_number}</td>
                  <td className="px-4 py-3 text-gray-600">{formatDate(p.payment_date)}</td>
                  <td className="px-4 py-3 text-right font-semibold text-green-700">{formatMoney(p.amount)}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                      p.source === "bank" ? "bg-gray-100 text-gray-600" :
                      p.source === "cash" ? "bg-green-100 text-green-700" :
                      p.source === "court" ? "bg-purple-100 text-purple-700" :
                      "bg-blue-100 text-blue-700"
                    }`}>
                      {SOURCE_LABELS[p.source] || p.source}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-700">{p.manager_name}</td>
                  <td className="px-4 py-3 text-center" onClick={(e) => e.stopPropagation()}>
                    {p.receipt_path ? (
                      <button
                        onClick={() => setReceiptModal(p)}
                        className="inline-flex items-center gap-1 rounded bg-green-100 px-2 py-1 text-xs font-medium text-green-700 hover:bg-green-200 transition-colors"
                      >
                        📎 Чек
                      </button>
                    ) : <span className="text-gray-300">—</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {receiptModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onClick={() => setReceiptModal(null)}>
          <div className="relative w-full max-w-2xl rounded-xl bg-white shadow-2xl" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between border-b px-4 py-3">
              <div>
                <p className="font-semibold text-gray-900">Чек платежа</p>
                <p className="text-xs text-gray-500">{receiptModal.debtor_name} — {formatMoney(receiptModal.amount)} — {formatDate(receiptModal.payment_date)}</p>
              </div>
              <button onClick={() => setReceiptModal(null)} className="text-gray-400 hover:text-gray-600">
                <X size={20} />
              </button>
            </div>
            <div className="p-4">
              <ReceiptViewer paymentId={receiptModal.id} receiptPath={receiptModal.receipt_path} />
            </div>
          </div>
        </div>
      )}
    </AppShell>
  );
}

function ReceiptViewer({ paymentId, receiptPath }: { paymentId: number; receiptPath: string }) {
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const isPdf = /\.pdf$/i.test(receiptPath);

  useEffect(() => {
    apiClient.get(`/payments/${paymentId}/receipt/view`, { responseType: "arraybuffer" })
      .then((res) => {
        const mimeType = isPdf ? "application/pdf" : "image/jpeg";
        const blob = new Blob([res.data], { type: mimeType });
        setBlobUrl(URL.createObjectURL(blob));
      })
      .catch((e) => {
        const status = e?.response?.status;
        setErr(`Ошибка загрузки (${status || e?.message})`);
      })
      .finally(() => setLoading(false));

    return () => { if (blobUrl) URL.revokeObjectURL(blobUrl); };
  }, [paymentId]);

  if (loading) return (
    <div className="flex justify-center py-10">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-blue-500 border-t-transparent" />
    </div>
  );

  if (err || !blobUrl) return (
    <div className="py-6 text-center text-sm text-red-500">{err || "Не удалось загрузить чек"}</div>
  );

  if (isPdf) {
    return (
      <div className="space-y-2">
        <iframe src={blobUrl} className="h-[500px] w-full rounded-lg border" title="Чек" />
        <a href={blobUrl} download={`receipt_${paymentId}.pdf`} className="block text-center text-sm text-blue-600 underline">
          ⬇ Скачать PDF
        </a>
      </div>
    );
  }

  return <img src={blobUrl} alt="Чек" className="max-h-[500px] w-full rounded-lg object-contain" />;
}
