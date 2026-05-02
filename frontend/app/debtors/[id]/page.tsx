"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { apiClient } from "@/lib/api-client";
import ContractForm from "@/components/forms/ContractForm";
import PromiseForm from "@/components/forms/PromiseForm";
import PaymentForm from "@/components/forms/PaymentForm";
import CallLogForm from "@/components/forms/CallLogForm";
import { Calculator, ChevronDown, ChevronUp, Phone, MessageCircle, User, Briefcase, MapPin, CreditCard, TrendingDown, Clock, CheckCircle, XCircle, AlertCircle, History, ListChecks } from "lucide-react";

// =================== КАЛЬКУЛЯТОР РЕСТРУКТУРИЗАЦИИ ===================
function getDownPaymentPercent(debt: number): number {
  if (debt <= 499999) return 40;
  if (debt <= 999999) return 30;
  if (debt <= 2999999) return 20;
  return 10;
}
function getMaxMonths(debt: number): number {
  if (debt < 600000) return 10;
  if (debt <= 900000) return 20;
  if (debt <= 1500000) return 25;
  if (debt <= 2100000) return 30;
  if (debt <= 2700000) return 35;
  return 40;
}

function RestructuringCalc({ totalDebt, debtorName, debtorIin, contractNumber }: { totalDebt: number; debtorName?: string; debtorIin?: string; contractNumber?: string }) {
  const [open, setOpen] = useState(false);
  const [customMonths, setCustomMonths] = useState<number | null>(null);
  const pct = getDownPaymentPercent(totalDebt);
  const maxMonths = getMaxMonths(totalDebt);
  const minDownPayment = Math.ceil(totalDebt * pct / 100);
  const remaining = totalDebt - minDownPayment;
  const months = customMonths ?? maxMonths;
  const monthlyPayment = months > 0 ? Math.ceil(remaining / months) : 0;
  const isValid = monthlyPayment >= 30000;
  const fmt = (n: number) => (isNaN(n) ? "0" : Math.round(n).toLocaleString("ru-KZ")) + " ₸";

  const downloadPdf = () => {
    const today = new Date();
    const startDate = new Date(today);
    startDate.setMonth(startDate.getMonth() + 1);

    const rows = [];
    let balance = remaining;
    for (let i = 1; i <= months; i++) {
      const date = new Date(startDate);
      date.setMonth(date.getMonth() + i - 1);
      const payment = i === months ? balance : monthlyPayment;
      balance -= payment;
      rows.push({
        n: i,
        date: date.toLocaleDateString("ru-KZ"),
        payment: payment,
        balance: Math.max(0, balance),
      });
    }

    const html = `<!DOCTYPE html><html><head><meta charset="utf-8"><title>График реструктуризации</title>
    <style>
      @media print { @page { size: A4; margin: 15mm; } body { -webkit-print-color-adjust: exact; } .no-print { display: none; } }
      body { font-family: -apple-system, Arial, sans-serif; padding: 30px; color: #1f2937; }
      h1 { color: #1e40af; font-size: 22px; margin-bottom: 5px; }
      .subtitle { color: #6b7280; font-size: 13px; margin-bottom: 20px; }
      .info { background: #f3f4f6; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
      .info-row { display: flex; justify-content: space-between; padding: 4px 0; font-size: 14px; }
      .info-row strong { color: #111827; }
      .summary { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; margin-bottom: 20px; }
      .summary-card { background: #fef3c7; padding: 12px; border-radius: 8px; text-align: center; }
      .summary-card.green { background: #d1fae5; }
      .summary-card.blue { background: #dbeafe; }
      .summary-card .label { font-size: 11px; color: #6b7280; text-transform: uppercase; }
      .summary-card .value { font-size: 18px; font-weight: bold; color: #111827; margin-top: 4px; }
      table { width: 100%; border-collapse: collapse; font-size: 13px; }
      th { background: #1e40af; color: white; padding: 10px; text-align: left; font-weight: 600; }
      th:nth-child(1), td:nth-child(1) { text-align: center; width: 60px; }
      th:nth-child(3), td:nth-child(3), th:nth-child(4), td:nth-child(4) { text-align: right; }
      td { padding: 8px 10px; border-bottom: 1px solid #e5e7eb; }
      tr:nth-child(even) td { background: #f9fafb; }
      tr:last-child td { background: #fef3c7; font-weight: bold; }
      .footer { margin-top: 30px; padding-top: 15px; border-top: 1px solid #e5e7eb; font-size: 11px; color: #6b7280; }
      .signs { margin-top: 40px; display: flex; justify-content: space-between; gap: 40px; }
      .sign { flex: 1; border-top: 1px solid #1f2937; padding-top: 5px; font-size: 11px; text-align: center; color: #6b7280; }
      .btn { background: #1e40af; color: white; padding: 10px 20px; border: none; border-radius: 6px; cursor: pointer; font-size: 14px; }
    </style></head><body>
      <button class="btn no-print" onclick="window.print()">🖨 Скачать как PDF (Ctrl+P)</button>
      <h1>График реструктуризации задолженности</h1>
      <div class="subtitle">Дата составления: ${today.toLocaleDateString("ru-KZ")}</div>

      <div class="info">
        <div class="info-row"><span>ФИО должника:</span><strong>${debtorName || "—"}</strong></div>
        <div class="info-row"><span>ИИН:</span><strong>${debtorIin || "—"}</strong></div>
        ${contractNumber ? `<div class="info-row"><span>Номер договора:</span><strong>${contractNumber}</strong></div>` : ""}
        <div class="info-row"><span>Сумма задолженности:</span><strong>${fmt(totalDebt)}</strong></div>
      </div>

      <div class="summary">
        <div class="summary-card">
          <div class="label">Первонач. взнос (${pct}%)</div>
          <div class="value">${fmt(minDownPayment)}</div>
        </div>
        <div class="summary-card blue">
          <div class="label">Срок рассрочки</div>
          <div class="value">${months} мес.</div>
        </div>
        <div class="summary-card green">
          <div class="label">Ежемес. платёж</div>
          <div class="value">${fmt(monthlyPayment)}</div>
        </div>
      </div>

      <table>
        <thead>
          <tr><th>№</th><th>Дата платежа</th><th>Сумма</th><th>Остаток</th></tr>
        </thead>
        <tbody>
          ${rows.map(r => `<tr><td>${r.n}</td><td>${r.date}</td><td>${fmt(r.payment)}</td><td>${fmt(r.balance)}</td></tr>`).join("")}
        </tbody>
      </table>

      <div class="footer">
        Должник обязуется производить платежи в указанные сроки. Минимальный ежемесячный платёж — 30 000 ₸.
      </div>

      <div class="signs">
        <div class="sign">Должник<br/>(подпись, дата)</div>
        <div class="sign">Представитель КА<br/>(подпись, дата)</div>
      </div>
    </body></html>`;

    const w = window.open("", "_blank");
    if (w) {
      w.document.write(html);
      w.document.close();
    }
  };

  return (
    <div className="bg-white rounded-2xl border border-blue-100 shadow-sm overflow-hidden">
      <button onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-6 py-4 bg-gradient-to-r from-blue-50 to-indigo-50 hover:from-blue-100 hover:to-indigo-100 transition-all">
        <div className="flex items-center gap-3 text-blue-700 font-semibold text-sm">
          <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center">
            <Calculator size={16} className="text-blue-600" />
          </div>
          Калькулятор реструктуризации
          {totalDebt > 0 && (
            <span className="bg-blue-600 text-white text-xs px-2 py-0.5 rounded-full">
              {fmt(minDownPayment)} взнос
            </span>
          )}
        </div>
        {open ? <ChevronUp size={16} className="text-blue-400" /> : <ChevronDown size={16} className="text-blue-400" />}
      </button>

      {open && (
        <div className="p-6 space-y-4">
          {totalDebt === 0 ? (
            <p className="text-center text-gray-400 py-4">Долг не указан</p>
          ) : (
            <>
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-gray-50 rounded-xl p-4">
                  <p className="text-xs text-gray-500 mb-1">Сумма долга</p>
                  <p className="text-xl font-bold text-gray-800">{fmt(totalDebt)}</p>
                </div>
                <div className="bg-amber-50 rounded-xl p-4 border border-amber-200">
                  <p className="text-xs text-amber-600 mb-1">Мин. первоначальный взнос ({pct}%)</p>
                  <p className="text-xl font-bold text-amber-700">{fmt(minDownPayment)}</p>
                </div>
              </div>

              <div className="bg-gray-50 rounded-xl p-4 space-y-3">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Остаток после взноса</span>
                  <span className="font-semibold">{fmt(remaining)}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Макс. срок рассрочки</span>
                  <span className="font-semibold">{maxMonths} мес.</span>
                </div>
                <div className="pt-2 border-t border-gray-200">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-gray-500">Выбрать срок</span>
                    <span className="text-sm font-bold text-blue-600">{months} мес.</span>
                  </div>
                  <input type="range" min={1} max={maxMonths} value={months}
                    onChange={e => setCustomMonths(Number(e.target.value))}
                    className="w-full accent-blue-600" />
                </div>
              </div>

              <div className={`rounded-xl p-4 border-2 ${isValid ? "bg-green-50 border-green-200" : "bg-red-50 border-red-200"}`}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    {isValid ? <CheckCircle size={18} className="text-green-600" /> : <XCircle size={18} className="text-red-500" />}
                    <span className={`font-medium text-sm ${isValid ? "text-green-700" : "text-red-700"}`}>
                      Ежемесячный платёж
                    </span>
                  </div>
                  <span className={`text-2xl font-bold ${isValid ? "text-green-700" : "text-red-700"}`}>
                    {fmt(monthlyPayment)}
                  </span>
                </div>
                {!isValid && (
                  <p className="text-xs text-red-500 mt-2">⚠ Минимум 30 000 ₸/мес — уменьшите срок</p>
                )}
              </div>

              <button
                onClick={downloadPdf}
                disabled={!isValid}
                className="w-full py-3 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed text-white font-medium rounded-xl flex items-center justify-center gap-2 transition-all shadow-sm"
              >
                📄 Скачать график PDF
              </button>

              <p className="text-center text-xs text-gray-400">
                Взнос {pct}% → рассрочка до {maxMonths} мес. → мин. 30 000 ₸/мес
              </p>
            </>
          )}
        </div>
      )}
    </div>
  );
}
// ====================================================================

interface Debtor {
  id: number; full_name: string; iin: string;
  phone?: string; phone_primary?: string;
  phone2?: string; phone_secondary?: string;
  email?: string; organization?: string;
  work_phone?: string; employer_phone?: string; address?: string;
  total_debt?: number; contracts_count?: number; added_date?: string;
}
interface Contract {
  id: number; contract_number: string; original_creditor: string; creditor?: string;
  total_debt: number; principal_debt?: number; interest_debt?: number; penalty_debt?: number;
  debt_amount?: number; status: string; overdue_date?: string; product_type?: string;
}
interface Promise_ {
  id: number; promise_date: string; amount: number; comment?: string; status: string;
  created_at: string; manager_name?: string;
}
interface Payment {
  id: number; amount: number; payment_date: string; source: string;
  comment?: string; receipt_path?: string; manager_name?: string;
}
interface Call {
  id: number; call_date: string; duration?: number; result?: string;
  comment?: string; manager_name?: string;
}
interface Activity {
  id: number; action: string; entity_type: string; description?: string;
  actor_name?: string; created_at: string; changes?: any;
}
interface DebtorTask {
  id: number; title: string; description?: string; status: string;
  priority: string; due_date?: string; created_at: string;
}

const STATUS_LABELS: Record<string, string> = {
  active: "Активный",
  closed: "Закрытый",
  court: "Судебный",
  litigation: "Судебный",
  bankrupt: "Банкрот",
  bankruptcy: "Банкрот",
  restructured: "На графике",
  graph: "На графике",
  on_schedule: "На графике",
  written_off: "Списан",
  new: "Новый",
  overdue: "Просроченный",
};
const STATUS_COLORS: Record<string, string> = {
  active: "bg-emerald-100 text-emerald-700 border-emerald-200",
  closed: "bg-gray-100 text-gray-600 border-gray-200",
  court: "bg-red-100 text-red-700 border-red-200",
  litigation: "bg-red-100 text-red-700 border-red-200",
  bankrupt: "bg-purple-100 text-purple-700 border-purple-200",
  bankruptcy: "bg-purple-100 text-purple-700 border-purple-200",
  restructured: "bg-blue-100 text-blue-700 border-blue-200",
  graph: "bg-blue-100 text-blue-700 border-blue-200",
  on_schedule: "bg-blue-100 text-blue-700 border-blue-200",
  written_off: "bg-gray-100 text-gray-500 border-gray-200",
  new: "bg-yellow-100 text-yellow-700 border-yellow-200",
  overdue: "bg-orange-100 text-orange-700 border-orange-200",
};

export default function DebtorDetailPage() {
  const { id } = useParams();
  const router = useRouter();
  const [debtor, setDebtor] = useState<Debtor | null>(null);
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [promises, setPromises] = useState<Promise_[]>([]);
  const [payments, setPayments] = useState<Payment[]>([]);
  const [calls, setCalls] = useState<Call[]>([]);
  const [activity, setActivity] = useState<Activity[]>([]);
  const [debtorTasks, setDebtorTasks] = useState<DebtorTask[]>([]);
  const [tab, setTab] = useState<"contracts"|"promises"|"payments"|"calls"|"history"|"tasks">("contracts");
  const [loading, setLoading] = useState(true);
  const [showContractForm, setShowContractForm] = useState(false);
  const [showPromiseForm, setShowPromiseForm] = useState(false);
  const [showPaymentForm, setShowPaymentForm] = useState(false);
  const [showCallForm, setShowCallForm] = useState(false);
  const [selectedContractId, setSelectedContractId] = useState<number | null>(null);

  useEffect(() => { loadData(); }, [id]);

  const loadData = async () => {
    try {
      setLoading(true);
      const [dRes, cRes, aRes, tRes] = await Promise.all([
        apiClient.get(`/debtors/${id}`),
        apiClient.get(`/contracts/by-debtor/${id}`),
        apiClient.get(`/activity-logs/by-debtor/${id}`).catch(() => ({ data: [] })),
        apiClient.get(`/tasks/by-debtor/${id}`).catch(() => ({ data: [] })),
      ]);
      setDebtor(dRes.data);
      setContracts(cRes.data || []);
      setActivity(aRes.data || []);
      setDebtorTasks(tRes.data || []);
      if (cRes.data?.length > 0) {
        setSelectedContractId(cRes.data[0].id);
        await loadContractData(cRes.data[0].id);
      }
    } catch (e) { console.error(e); } finally { setLoading(false); }
  };

  const loadContractData = async (contractId: number) => {
    try {
      const [prRes, pyRes, caRes] = await Promise.all([
        apiClient.get(`/promises/contract/${contractId}`),
        apiClient.get(`/payments/contract/${contractId}`),
        apiClient.get(`/calls/contract/${contractId}`),
      ]);
      setPromises(prRes.data || []);
      setPayments(pyRes.data || []);
      setCalls(caRes.data || []);
    } catch (e) { console.error(e); }
  };

  const totalDebt = contracts.reduce((s, c) => s + (Number(c.total_debt) || Number(c.debt_amount) || 0), 0);
  const totalPaid = payments.reduce((s, p) => s + (Number(p.amount) || 0), 0);

  const viewReceipt = async (paymentId: number) => {
    try {
      const token = document.cookie.match(/access_token=([^;]+)/)?.[1];
      const res = await fetch(`/api/v1/payments/${paymentId}/receipt/view`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) window.open(URL.createObjectURL(await res.blob()));
    } catch (e) { console.error(e); }
  };

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="animate-spin rounded-full h-10 w-10 border-4 border-blue-600 border-t-transparent" />
    </div>
  );
  if (!debtor) return <div className="p-6 text-red-500">Должник не найден</div>;

  const whatsappUrl = (phone: string) => `https://wa.me/${phone.replace(/\D/g, "")}`;
  const debtStatus = totalDebt > 1000000 ? "high" : totalDebt > 300000 ? "medium" : "low";
  const debtColor = debtStatus === "high" ? "text-red-600" : debtStatus === "medium" ? "text-orange-500" : "text-yellow-600";
  const debtBg = debtStatus === "high" ? "from-red-50 to-rose-50 border-red-100" : debtStatus === "medium" ? "from-orange-50 to-amber-50 border-orange-100" : "from-yellow-50 to-amber-50 border-yellow-100";

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-5">
      {/* Back + Header */}
      <div className="flex items-start justify-between">
        <div>
          <button onClick={() => router.back()}
            className="flex items-center gap-1.5 text-sm text-gray-400 hover:text-gray-600 mb-3 transition-colors">
            ← Назад к списку
          </button>
          <h1 className="text-2xl font-bold text-gray-900 tracking-tight">{debtor.full_name}</h1>
          <div className="flex items-center gap-3 mt-1">
            <span className="text-sm text-gray-400 font-mono">ИИН: {debtor.iin}</span>
            {contracts[0] && (
              <span className={`text-xs px-2.5 py-1 rounded-full border font-medium ${STATUS_COLORS[contracts[0].status] || "bg-gray-100 text-gray-600 border-gray-200"}`}>
                {STATUS_LABELS[contracts[0].status] || contracts[0].status}
              </span>
            )}
          </div>
        </div>
        <button onClick={() => router.push(`/debtors/${id}/edit`)}
          className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-200 rounded-xl text-sm text-gray-600 hover:bg-gray-50 hover:border-gray-300 transition-all shadow-sm">
          ✏️ Редактировать
        </button>
      </div>

      {/* Info Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Contacts */}
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-8 h-8 bg-blue-50 rounded-lg flex items-center justify-center">
              <User size={15} className="text-blue-600" />
            </div>
            <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Контакты</h3>
          </div>
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-500 flex items-center gap-1.5"><Phone size={13} />Телефон</span>
              {(debtor.phone_primary || debtor.phone) ? (
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-gray-800">{debtor.phone_primary || debtor.phone}</span>
                  <a
                    href={`https://api.whatsapp.com/send/?phone=${(debtor.phone_primary || debtor.phone || "").replace(/\D/g, "")}&text&type=phone_number&app_absent=0`}
                    target="_blank" rel="noreferrer"
                    className="w-8 h-8 bg-green-500 hover:bg-green-600 rounded-full flex items-center justify-center transition-colors shadow-sm"
                    title="WhatsApp">
                    <svg viewBox="0 0 32 32" width="16" height="16" fill="white" xmlns="http://www.w3.org/2000/svg"><path d="M16 0C7.164 0 0 7.163 0 16c0 2.833.738 5.494 2.027 7.802L0 32l8.418-2.004A15.928 15.928 0 0 0 16 32c8.836 0 16-7.163 16-16S24.836 0 16 0zm8.322 22.293c-.344.969-2.012 1.856-2.754 1.906-.742.05-1.444.375-4.875-1.031-4.088-1.688-6.688-5.844-6.888-6.113-.199-.268-1.625-2.162-1.625-4.125s1.025-2.931 1.393-3.331c.368-.4.8-.5 1.068-.5.268 0 .537.003.772.014.248.012.58-.094.907.693.344.818 1.169 2.788 1.269 2.988.1.2.168.437.031.706-.137.268-.206.437-.406.675-.2.237-.421.53-.6.712-.2.2-.408.418-.175.818.231.4 1.031 1.7 2.212 2.756 1.519 1.35 2.8 1.769 3.2 1.969.4.2.631.168.862-.1.231-.268.994-1.156 1.262-1.556.268-.4.537-.331.906-.2.369.131 2.338 1.1 2.738 1.3.4.2.662.3.762.469.1.168.1.968-.244 1.937z"/></svg>
                  </a>
                </div>
              ) : <span className="text-sm text-gray-300">—</span>}
            </div>
            {(debtor.phone_secondary || debtor.phone2) && (
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-500">Доп. телефон</span>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-gray-800">{debtor.phone_secondary || debtor.phone2}</span>
                  <a href={`https://api.whatsapp.com/send/?phone=${(debtor.phone_secondary || debtor.phone2 || "").replace(/\D/g, "")}&text&type=phone_number&app_absent=0`}
                    target="_blank" rel="noreferrer"
                    className="w-8 h-8 bg-green-500 hover:bg-green-600 rounded-full flex items-center justify-center transition-colors shadow-sm"
                    title="WhatsApp">
                    <svg viewBox="0 0 32 32" width="16" height="16" fill="white" xmlns="http://www.w3.org/2000/svg"><path d="M16 0C7.164 0 0 7.163 0 16c0 2.833.738 5.494 2.027 7.802L0 32l8.418-2.004A15.928 15.928 0 0 0 16 32c8.836 0 16-7.163 16-16S24.836 0 16 0zm8.322 22.293c-.344.969-2.012 1.856-2.754 1.906-.742.05-1.444.375-4.875-1.031-4.088-1.688-6.688-5.844-6.888-6.113-.199-.268-1.625-2.162-1.625-4.125s1.025-2.931 1.393-3.331c.368-.4.8-.5 1.068-.5.268 0 .537.003.772.014.248.012.58-.094.907.693.344.818 1.169 2.788 1.269 2.988.1.2.168.437.031.706-.137.268-.206.437-.406.675-.2.237-.421.53-.6.712-.2.2-.408.418-.175.818.231.4 1.031 1.7 2.212 2.756 1.519 1.35 2.8 1.769 3.2 1.969.4.2.631.168.862-.1.231-.268.994-1.156 1.262-1.556.268-.4.537-.331.906-.2.369.131 2.338 1.1 2.738 1.3.4.2.662.3.762.469.1.168.1.968-.244 1.937z"/></svg>
                  </a>
                </div>
              </div>
            )}
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-500">Email</span>
              <span className="text-sm text-gray-700">{debtor.email || <span className="text-gray-300">—</span>}</span>
            </div>
          </div>
        </div>

        {/* Work */}
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-8 h-8 bg-purple-50 rounded-lg flex items-center justify-center">
              <Briefcase size={15} className="text-purple-600" />
            </div>
            <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Место работы</h3>
          </div>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-sm text-gray-500">Организация</span>
              <span className="text-sm font-medium text-gray-800 text-right max-w-[160px]">{debtor.organization || <span className="text-gray-300">—</span>}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-500">Тел. работы</span>
              <span className="text-sm text-gray-700">{debtor.employer_phone || debtor.work_phone || <span className="text-gray-300">—</span>}</span>
            </div>
            <div className="flex justify-between gap-4">
              <span className="text-sm text-gray-500 flex items-center gap-1"><MapPin size={12} />Адрес</span>
              <span className="text-xs text-gray-600 text-right leading-relaxed">{debtor.address || <span className="text-gray-300">—</span>}</span>
            </div>
          </div>
        </div>

        {/* Debt Card */}
        <div className={`bg-gradient-to-br ${debtBg} rounded-2xl border shadow-sm p-5`}>
          <div className="flex items-center gap-2 mb-3">
            <div className="w-8 h-8 bg-white/70 rounded-lg flex items-center justify-center">
              <TrendingDown size={15} className={debtColor} />
            </div>
            <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Долг</h3>
          </div>
          <div className={`text-3xl font-bold mb-1 ${debtColor}`}>
            {isNaN(totalDebt) ? "0" : Math.round(totalDebt).toLocaleString("ru-KZ")} ₸
          </div>
          <div className="text-sm text-gray-500 mb-3">{contracts.length} договор(а)</div>

          {totalPaid > 0 && (
            <div className="flex items-center gap-2 bg-white/60 rounded-lg px-3 py-2 mb-2">
              <CheckCircle size={14} className="text-green-600" />
              <span className="text-sm text-green-700 font-medium">
                Оплачено: {Math.round(totalPaid).toLocaleString("ru-KZ")} ₸
              </span>
            </div>
          )}

          {contracts[0]?.overdue_date && (
            <div className="flex items-center gap-2 bg-white/60 rounded-lg px-3 py-2">
              <Clock size={14} className="text-gray-500" />
              <span className="text-xs text-gray-500">Просрочка: {contracts[0].overdue_date}</span>
            </div>
          )}

          {debtor.added_date && (
            <p className="text-xs text-gray-400 mt-2">Добавлен: {debtor.added_date}</p>
          )}
        </div>
      </div>

      {/* Restructuring Calculator */}
      {contracts.length > 0 && <RestructuringCalc totalDebt={totalDebt} debtorName={debtor.full_name} debtorIin={debtor.iin} contractNumber={contracts[0]?.contract_number} />}

      {/* Tabs */}
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
        {/* Tabs */}
        <div className="flex items-center border-b border-gray-100 px-2 overflow-x-auto">
          {[
            { key: "contracts", label: "Договоры", count: contracts.length },
            { key: "promises", label: "Обещания", count: promises.length },
            { key: "payments", label: "Платежи", count: payments.length },
            { key: "calls", label: "Звонки", count: calls.length },
            { key: "tasks", label: "Задачи", count: debtorTasks.length },
            { key: "history", label: "История", count: activity.length },
          ].map(t => (
            <button key={t.key} onClick={() => setTab(t.key as any)}
              className={`shrink-0 px-4 py-4 text-sm font-medium transition-all flex items-center gap-2 border-b-2 -mb-px ${
                tab === t.key ? "border-blue-600 text-blue-600" : "border-transparent text-gray-500 hover:text-gray-700"
              }`}>
              {t.label}
              {t.count > 0 && (
                <span className={`text-xs px-1.5 py-0.5 rounded-full ${tab === t.key ? "bg-blue-100 text-blue-600" : "bg-gray-100 text-gray-500"}`}>
                  {t.count}
                </span>
              )}
            </button>
          ))}
          <div className="ml-auto shrink-0 px-4">
            {tab === "contracts" && (
              <button onClick={() => setShowContractForm(true)}
                className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs rounded-lg transition-colors whitespace-nowrap">
                + Договор
              </button>
            )}
            {tab === "promises" && selectedContractId && (
              <button onClick={() => setShowPromiseForm(true)}
                className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs rounded-lg transition-colors whitespace-nowrap">
                + Обещание
              </button>
            )}
            {tab === "payments" && selectedContractId && (
              <button onClick={() => setShowPaymentForm(true)}
                className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs rounded-lg transition-colors whitespace-nowrap">
                + Платёж
              </button>
            )}
            {tab === "calls" && selectedContractId && (
              <button onClick={() => setShowCallForm(true)}
                className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs rounded-lg transition-colors whitespace-nowrap">
                + Звонок
              </button>
            )}
          </div>
        </div>

        <div className="p-5">
          {/* Contracts */}
          {tab === "contracts" && (
            <div className="space-y-3">
              {contracts.map(c => (
                <div key={c.id} onClick={() => { setSelectedContractId(c.id); loadContractData(c.id); }}
                  className={`p-4 rounded-xl border-2 cursor-pointer transition-all ${selectedContractId === c.id ? "border-blue-300 bg-blue-50" : "border-gray-100 hover:border-gray-200 bg-gray-50"}`}>
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="font-mono text-sm font-semibold text-gray-800">{c.contract_number}</p>
                      <p className="text-sm text-gray-500 mt-0.5">{c.original_creditor || c.creditor}</p>
                      {c.product_type && <p className="text-xs text-gray-400 mt-0.5">{c.product_type}</p>}
                    </div>
                    <div className="text-right">
                      <p className="text-lg font-bold text-gray-800">
                        {Math.round(Number(c.total_debt) || Number(c.debt_amount) || 0).toLocaleString("ru-KZ")} ₸
                      </p>
                      <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${STATUS_COLORS[c.status] || "bg-gray-100 text-gray-600 border-gray-200"}`}>
                        {STATUS_LABELS[c.status] || c.status}
                      </span>
                    </div>
                  </div>
                  {(c.principal_debt || c.interest_debt || c.penalty_debt) ? (
                    <div className="flex gap-4 mt-3 pt-3 border-t border-gray-200">
                      <div className="text-xs">
                        <span className="text-gray-400">Осн. долг </span>
                        <span className="font-medium">{Math.round(Number(c.principal_debt)||0).toLocaleString("ru-KZ")} ₸</span>
                      </div>
                      {(c.interest_debt||0) > 0 && (
                        <div className="text-xs">
                          <span className="text-gray-400">%% </span>
                          <span className="font-medium">{Math.round(Number(c.interest_debt)||0).toLocaleString("ru-KZ")} ₸</span>
                        </div>
                      )}
                      {(c.penalty_debt||0) > 0 && (
                        <div className="text-xs">
                          <span className="text-gray-400">Штраф </span>
                          <span className="font-medium">{Math.round(Number(c.penalty_debt)||0).toLocaleString("ru-KZ")} ₸</span>
                        </div>
                      )}
                    </div>
                  ) : null}
                  {c.overdue_date && (
                    <p className="text-xs text-gray-400 mt-2 flex items-center gap-1">
                      <Clock size={11} /> Просрочка с {c.overdue_date}
                    </p>
                  )}
                </div>
              ))}
              {contracts.length === 0 && (
                <div className="text-center py-12 text-gray-400">
                  <CreditCard size={40} className="mx-auto mb-3 opacity-30" />
                  <p>Нет договоров</p>
                </div>
              )}
            </div>
          )}

          {/* Promises */}
          {tab === "promises" && (
            <div className="space-y-2">
              {promises.map(p => (
                <div key={p.id} className="flex items-center justify-between p-4 bg-gray-50 rounded-xl hover:bg-gray-100 transition-colors">
                  <div className="flex items-center gap-3">
                    <div className={`w-9 h-9 rounded-full flex items-center justify-center text-white text-xs font-bold ${p.status === "kept" ? "bg-green-500" : p.status === "broken" ? "bg-red-400" : "bg-amber-400"}`}>
                      {p.status === "kept" ? "✓" : p.status === "broken" ? "✗" : "?"}
                    </div>
                    <div>
                      <p className="font-semibold text-gray-800">{p.amount?.toLocaleString("ru-KZ")} ₸</p>
                      <p className="text-xs text-gray-400">{p.promise_date} · {p.manager_name || "—"}</p>
                    </div>
                  </div>
                  {p.comment && <p className="text-sm text-gray-500 max-w-[200px] truncate">{p.comment}</p>}
                </div>
              ))}
              {promises.length === 0 && <div className="text-center py-12 text-gray-400"><AlertCircle size={40} className="mx-auto mb-3 opacity-30" /><p>Нет обещаний</p></div>}
            </div>
          )}

          {/* Payments */}
          {tab === "payments" && (
            <div className="space-y-2">
              {payments.map(p => (
                <div key={p.id} className="flex items-center justify-between p-4 bg-gray-50 rounded-xl hover:bg-gray-100 transition-colors">
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 bg-green-100 rounded-full flex items-center justify-center">
                      <span className="text-green-600 font-bold text-sm">₸</span>
                    </div>
                    <div>
                      <p className="font-semibold text-green-700">+{p.amount?.toLocaleString("ru-KZ")} ₸</p>
                      <p className="text-xs text-gray-400">{p.payment_date} · {p.source === "cash" ? "Наличные" : p.source === "bank" ? "Банк" : p.source} · {p.manager_name || "—"}</p>
                    </div>
                  </div>
                  {p.receipt_path && (
                    <button onClick={() => viewReceipt(p.id)} className="text-xs text-blue-600 hover:underline bg-blue-50 px-2 py-1 rounded-lg">📄 Чек</button>
                  )}
                </div>
              ))}
              {payments.length === 0 && <div className="text-center py-12 text-gray-400"><CheckCircle size={40} className="mx-auto mb-3 opacity-30" /><p>Нет платежей</p></div>}
            </div>
          )}

          {/* Calls */}
          {tab === "calls" && (
            <div className="space-y-2">
              {calls.map(c => (
                <div key={c.id} className="flex items-center justify-between p-4 bg-gray-50 rounded-xl hover:bg-gray-100 transition-colors">
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 bg-blue-100 rounded-full flex items-center justify-center">
                      <Phone size={15} className="text-blue-600" />
                    </div>
                    <div>
                      <p className="font-medium text-gray-800">{c.result || "Звонок"}</p>
                      <p className="text-xs text-gray-400">{new Date(c.call_date).toLocaleString("ru-KZ")} {c.duration ? `· ${c.duration}с` : ""} · {c.manager_name || "—"}</p>
                    </div>
                  </div>
                  {c.comment && <p className="text-sm text-gray-500 max-w-[180px] truncate">{c.comment}</p>}
                </div>
              ))}
              {calls.length === 0 && <div className="text-center py-12 text-gray-400"><Phone size={40} className="mx-auto mb-3 opacity-30" /><p>Нет звонков</p></div>}
            </div>
          )}

          {/* Tasks tab */}
          {tab === "tasks" && (
            <div className="space-y-2">
              {debtorTasks.map(t => (
                <div key={t.id} className={`p-4 bg-gray-50 rounded-xl border-l-4 ${
                  t.priority === "urgent" ? "border-red-500" :
                  t.priority === "high" ? "border-orange-500" : "border-blue-400"
                }`}>
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1">
                      <p className={`font-semibold text-gray-800 ${t.status === "done" ? "line-through opacity-60" : ""}`}>{t.title}</p>
                      {t.description && <p className="text-sm text-gray-600 mt-1">{t.description}</p>}
                      <div className="flex items-center gap-3 mt-2 text-xs text-gray-400">
                        <span className={`px-2 py-0.5 rounded-full ${
                          t.status === "done" ? "bg-green-100 text-green-700" :
                          t.status === "in_progress" ? "bg-blue-100 text-blue-700" : "bg-gray-200"
                        }`}>{t.status}</span>
                        {t.due_date && <span>📅 до {new Date(t.due_date).toLocaleDateString("ru-KZ")}</span>}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
              {debtorTasks.length === 0 && <div className="text-center py-12 text-gray-400"><ListChecks size={40} className="mx-auto mb-3 opacity-30" /><p>Нет задач</p></div>}
            </div>
          )}

          {/* History tab */}
          {tab === "history" && (
            <div className="space-y-2">
              {activity.map(a => (
                <div key={a.id} className="flex gap-3 p-3 bg-gray-50 rounded-xl">
                  <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center shrink-0">
                    <History size={14} className="text-blue-600" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-gray-800">
                      <span className="font-medium">{a.actor_name || "Система"}</span>
                      {" • "}
                      <span className="text-gray-500">{a.action} {a.entity_type}</span>
                    </p>
                    {a.description && <p className="text-xs text-gray-500 mt-0.5">{a.description}</p>}
                    <p className="text-xs text-gray-400 mt-0.5">{new Date(a.created_at).toLocaleString("ru-KZ")}</p>
                  </div>
                </div>
              ))}
              {activity.length === 0 && <div className="text-center py-12 text-gray-400"><History size={40} className="mx-auto mb-3 opacity-30" /><p>История пуста</p></div>}
            </div>
          )}
        </div>
      </div>

      {/* Modals */}
      {showContractForm && (
        <Modal title="Новый договор" onClose={() => setShowContractForm(false)}>
          <ContractForm debtorId={Number(id)} onCancel={() => setShowContractForm(false)} onSuccess={() => { setShowContractForm(false); loadData(); }} />
        </Modal>
      )}
      {showPromiseForm && selectedContractId && (
        <Modal title="Новое обещание" onClose={() => setShowPromiseForm(false)}>
          <PromiseForm contractId={selectedContractId} onCancel={() => setShowPromiseForm(false)} onSuccess={() => { setShowPromiseForm(false); loadContractData(selectedContractId); }} />
        </Modal>
      )}
      {showPaymentForm && selectedContractId && (
        <Modal title="Новый платёж" onClose={() => setShowPaymentForm(false)}>
          <PaymentForm contractId={selectedContractId} onCancel={() => setShowPaymentForm(false)} onSuccess={() => { setShowPaymentForm(false); loadContractData(selectedContractId); }} />
        </Modal>
      )}
      {showCallForm && selectedContractId && (
        <Modal title="Новый звонок" onClose={() => setShowCallForm(false)}>
          <CallLogForm contractId={selectedContractId} onCancel={() => setShowCallForm(false)} onSuccess={() => { setShowCallForm(false); loadContractData(selectedContractId); }} />
        </Modal>
      )}
    </div>
  );
}

function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: React.ReactNode }) {
  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/50 backdrop-blur-sm p-4 overflow-y-auto" onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-hidden flex flex-col" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 sticky top-0 bg-white">
          <h2 className="text-lg font-semibold text-gray-800">{title}</h2>
          <button onClick={onClose} className="w-8 h-8 rounded-lg hover:bg-gray-100 flex items-center justify-center text-gray-400 hover:text-gray-600 transition-colors text-xl">
            ✕
          </button>
        </div>
        <div className="p-6 overflow-y-auto">{children}</div>
      </div>
    </div>
  );
}
