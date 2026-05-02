"use client";
import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import AppShell from "@/components/layout/AppShell";
import { Table, Pagination, PageHeader, Badge, Modal, Spinner } from "@/components/ui";
import { debtorService, userService } from "@/services/api";
import { formatDate, CONTRACT_STATUS_LABELS, CONTRACT_STATUS_COLORS } from "@/lib/utils";
import type { Debtor, PaginatedResponse } from "@/types/api";
import { Plus, Search, Upload, Download, Filter, X } from "lucide-react";
import toast from "react-hot-toast";
import DebtorForm from "@/components/forms/DebtorForm";
import ImportModal from "@/components/forms/ImportModal";
import { useAuth } from "@/lib/auth-context";
import { apiClient } from "@/lib/api-client";

export default function DebtorsPage() {
  const router = useRouter();
  const { user } = useAuth();
  const [result, setResult] = useState<PaginatedResponse<Debtor> | null>(null);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [showImport, setShowImport] = useState(false);
  const [showFilters, setShowFilters] = useState(false);
  const [managers, setManagers] = useState<any[]>([]);

  // Filters
  const [statusFilter, setStatusFilter] = useState("");
  const [managerFilter, setManagerFilter] = useState("");
  const [debtMin, setDebtMin] = useState("");
  const [debtMax, setDebtMax] = useState("");

  const isManager = user?.role?.toUpperCase() === "MANAGER";

  useEffect(() => {
    if (!isManager) {
      userService.list().then((data: any) => setManagers(data.items || data)).catch(() => {});
    }
  }, [isManager]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params: any = { page, page_size: 20 };
      if (search) params.search = search;
      if (statusFilter) params.contract_status = statusFilter;
      if (managerFilter) params.manager_id = parseInt(managerFilter);
      if (debtMin) params.debt_min = parseFloat(debtMin);
      if (debtMax) params.debt_max = parseFloat(debtMax);
      const data = await debtorService.list(params);
      setResult(data);
    } catch {
      toast.error("Ошибка загрузки");
    } finally {
      setLoading(false);
    }
  }, [search, page, statusFilter, managerFilter, debtMin, debtMax]);

  useEffect(() => { load(); }, [load]);

  const resetFilters = () => {
    setStatusFilter(""); setManagerFilter(""); setDebtMin(""); setDebtMax("");
    setPage(1);
  };

  const hasFilters = statusFilter || managerFilter || debtMin || debtMax;

  const handleExport = async () => {
    try {
      const params = new URLSearchParams();
      if (statusFilter) params.append("contract_status", statusFilter);
      if (managerFilter) params.append("manager_id", managerFilter);
      const token = localStorage.getItem("access_token");
      const resp = await fetch(`http://localhost:8000/api/v1/dashboard/export-debtors?${params}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a"); a.href = url; a.download = "debtors_export.xlsx"; a.click();
      toast.success("Экспорт скачан");
    } catch { toast.error("Ошибка экспорта"); }
  };

  const columns = [
    { key: "iin", header: "ИИН", className: "font-mono text-xs" },
    { key: "full_name", header: "ФИО" },
    { key: "phone_primary", header: "Телефон" },
    {
      key: "status",
      header: "Статус",
      render: (row: Debtor) => (
        <Badge status={row.is_active ? "active" : "closed"} label={row.is_active ? "Активный" : "Неактивный"} />
      ),
    },
    { key: "created_at", header: "Добавлен", render: (row: Debtor) => formatDate(row.created_at) },
  ];

  return (
    <AppShell>
      <PageHeader
        title={isManager ? "Мои должники" : "Должники"}
        subtitle={`Всего: ${result?.total ?? 0}`}
        actions={
          <div className="flex gap-2">
            {!isManager && (
              <>
                <button onClick={handleExport} className="btn-secondary flex items-center gap-1">
                  <Download size={15} /> Excel
                </button>
                <button onClick={() => setShowImport(true)} className="btn-secondary flex items-center gap-1">
                  <Upload size={15} /> Импорт
                </button>
                <button onClick={() => setShowCreate(true)} className="btn-primary flex items-center gap-1">
                  <Plus size={15} /> Добавить
                </button>
              </>
            )}
          </div>
        }
      />

      {/* Search + filter bar */}
      <div className="card mb-4 p-3">
        <div className="flex flex-wrap gap-2 items-center">
          <div className="relative flex-1 min-w-48">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              className="input pl-8 h-9 text-sm"
              placeholder="Поиск по ФИО, ИИН, телефону..."
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            />
          </div>

          <select className="input h-9 text-sm w-40" value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}>
            <option value="">Все статусы</option>
            <option value="active">Досудебный</option>
            <option value="litigation">Судебный</option>
            <option value="closed">Закрыт</option>
            <option value="written_off">Списан</option>
          </select>

          {!isManager && managers.length > 0 && (
            <select className="input h-9 text-sm w-44" value={managerFilter} onChange={(e) => { setManagerFilter(e.target.value); setPage(1); }}>
              <option value="">Все менеджеры</option>
              {managers.filter(m => ["MANAGER","HEAD"].includes((m.role||"").toUpperCase())).map(m => (
                <option key={m.id} value={m.id}>{m.full_name}</option>
              ))}
            </select>
          )}

          <input className="input h-9 text-sm w-32" type="number" placeholder="Долг от" value={debtMin} onChange={(e) => { setDebtMin(e.target.value); setPage(1); }} />
          <input className="input h-9 text-sm w-32" type="number" placeholder="Долг до" value={debtMax} onChange={(e) => { setDebtMax(e.target.value); setPage(1); }} />

          {hasFilters && (
            <button onClick={resetFilters} className="btn-secondary h-9 flex items-center gap-1 text-sm">
              <X size={14} /> Сброс
            </button>
          )}
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center py-16"><Spinner size="lg" /></div>
      ) : (
        <>
          <div className="card overflow-hidden">
            <Table
              columns={columns}
              data={result?.items ?? []}
              onRowClick={(row) => router.push(`/debtors/${row.id}`)}
              emptyMessage="Должники не найдены"
            />
          </div>
          {result && result.pages > 1 && (
            <div className="mt-4 flex justify-center">
              <Pagination page={page} pages={result.pages} total={result.total} onPage={setPage} />
            </div>
          )}
        </>
      )}

      {showCreate && (
        <Modal open={showCreate} title="Новый должник" onClose={() => setShowCreate(false)}>
          <DebtorForm onSuccess={() => { setShowCreate(false); load(); }} onCancel={() => setShowCreate(false)} />
        </Modal>
      )}
      {showImport && (
        <Modal open={showImport} title="Импорт должников из Excel" onClose={() => setShowImport(false)}>
          <ImportModal open={showImport} onClose={() => { setShowImport(false); load(); }} />
        </Modal>
      )}
    </AppShell>
  );
}
