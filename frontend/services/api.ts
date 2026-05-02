import { apiClient } from "@/lib/api-client";
import type {
  Debtor,
  Contract,
  Promise as DebtPromise,
  Payment,
  CallLog,
  DashboardSummary,
  PaginatedResponse,
  User,
} from "@/types/api";

// --- Debtors ---
export const debtorService = {
  async list(params: { search?: string; is_active?: boolean; page?: number; page_size?: number }) {
    const { data } = await apiClient.get<PaginatedResponse<Debtor>>("/debtors/", { params });
    return data;
  },
  async get(id: number) {
    const { data } = await apiClient.get<Debtor>(`/debtors/${id}`);
    return data;
  },
  async create(payload: Partial<Debtor>) {
    const { data } = await apiClient.post<Debtor>("/debtors/", payload);
    return data;
  },
  async update(id: number, payload: Partial<Debtor>) {
    const { data } = await apiClient.patch<Debtor>(`/debtors/${id}`, payload);
    return data;
  },
  async delete(id: number) {
    await apiClient.delete(`/debtors/${id}`);
  },
};

// --- Contracts ---
export const contractService = {
  async getByDebtor(debtorId: number) {
    const { data } = await apiClient.get<Contract[]>(`/contracts/by-debtor/${debtorId}`);
    return data;
  },
  async get(id: number) {
    const { data } = await apiClient.get<Contract>(`/contracts/${id}`);
    return data;
  },
  async create(payload: Partial<Contract>) {
    const { data } = await apiClient.post<Contract>("/contracts/", payload);
    return data;
  },
  async update(id: number, payload: Partial<Contract>) {
    const { data } = await apiClient.patch<Contract>(`/contracts/${id}`, payload);
    return data;
  },
};

// --- Promises ---
export const promiseService = {
  async listByContract(contractId: number) {
    const { data } = await apiClient.get<DebtPromise[]>(`/promises/contract/${contractId}`);
    return data;
  },
  async create(payload: { contract_id: number; promise_date: string; amount: number; notes?: string }) {
    const { data } = await apiClient.post<DebtPromise>("/promises/", payload);
    return data;
  },
  async update(id: number, payload: Partial<DebtPromise>) {
    const { data } = await apiClient.patch<DebtPromise>(`/promises/${id}`, payload);
    return data;
  },
  async processOverdue() {
    const { data } = await apiClient.post("/promises/process-overdue");
    return data;
  },
};

// --- Payments ---
export const paymentService = {
  async listByContract(contractId: number) {
    const { data } = await apiClient.get<Payment[]>(`/payments/contract/${contractId}`);
    return data;
  },
  async create(payload: { contract_id: number; amount: number; payment_date: string; source: string; reference?: string; notes?: string }) {
    const { data } = await apiClient.post<Payment>("/payments/", payload);
    return data;
  },
};

// --- Call Logs ---
export const callLogService = {
  async listByContract(contractId: number) {
    const { data } = await apiClient.get<CallLog[]>(`/calls/contract/${contractId}`);
    return data;
  },
  async create(payload: { contract_id: number; called_at: string; phone_number: string; result: string; duration_seconds?: number; notes?: string }) {
    const { data } = await apiClient.post<CallLog>("/calls/", payload);
    return data;
  },
};

// --- Dashboard ---
export const dashboardService = {
  async getSummary() {
    const { data } = await apiClient.get<DashboardSummary>("/dashboard/summary");
    return data;
  },
  async getPaymentsByDay(days = 30) {
    const { data } = await apiClient.get<{ date: string; amount: number }[]>("/dashboard/payments-by-day", { params: { days } });
    return data;
  },
  async getTopManagers() {
    const { data } = await apiClient.get<{ manager: string; payments_count: number; total_collected: number }[]>("/dashboard/top-managers");
    return data;
  },
};

// --- Users ---
export const userService = {
  async list() {
    const { data } = await apiClient.get<User[]>("/users/");
    return data;
  },
  async create(payload: { email: string; full_name: string; password: string; role: string; phone?: string }) {
    const { data } = await apiClient.post<User>("/users/", payload);
    return data;
  },
  async update(id: number, payload: Partial<User> & { password?: string }) {
    const { data } = await apiClient.patch<User>(`/users/${id}`, payload);
    return data;
  },
  async delete(id: number) {
    await apiClient.delete(`/users/${id}`);
  },
};

// --- Import ---
export const importService = {
  async importExcel(file: File) {
    const form = new FormData();
    form.append("file", file);
    const { data } = await apiClient.post("/import/excel", form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return data;
  },
};

// --- Management ---
export const managementService = {
  async autoAssign() {
    const { data } = await apiClient.post("/management/auto-assign");
    return data;
  },
  async getManagerLoads() {
    const { data } = await apiClient.get("/management/manager-loads");
    return data;
  },
  async getKpi(dateFrom?: string, dateTo?: string) {
    const { data } = await apiClient.get("/management/kpi", {
      params: { date_from: dateFrom, date_to: dateTo },
    });
    return data;
  },
  async updateContractStatus(contractId: number, status: string, comment?: string) {
    const { data } = await apiClient.patch(`/management/contracts/${contractId}/status`, null, {
      params: { status, comment: comment || "" },
    });
    return data;
  },
};
