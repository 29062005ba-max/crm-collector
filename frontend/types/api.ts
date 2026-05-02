export type UserRole = "admin" | "head" | "manager";

export interface User {
  id: number;
  email: string;
  full_name: string;
  phone?: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}

export interface Debtor {
  id: number;
  iin: string;
  full_name: string;
  birth_date?: string;
  phone_primary?: string;
  phone_secondary?: string;
  email?: string;
  address?: string;
  employer?: string;
  employer_phone?: string;
  notes?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export type ContractStatus = "active" | "closed" | "litigation" | "written_off";

export interface Contract {
  id: number;
  debtor_id: number;
  contract_number: string;
  original_creditor: string;
  product_type?: string;
  principal_debt: number;
  interest_debt: number;
  penalty_debt: number;
  total_debt: number;
  currency: string;
  issue_date?: string;
  overdue_date?: string;
  purchase_date?: string;
  status: ContractStatus;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export type PromiseStatus = "active" | "done" | "overdue" | "cancelled";

export interface Promise {
  id: number;
  contract_id: number;
  promise_date: string;
  amount: number;
  status: PromiseStatus;
  notes?: string;
  created_by_id: number;
  created_at: string;
}

export type PaymentSource = "bank" | "cash" | "card" | "court";

export interface Payment {
  id: number;
  contract_id: number;
  amount: number;
  payment_date: string;
  source: PaymentSource;
  reference?: string;
  notes?: string;
  registered_by_id: number;
  created_at: string;
}

export type CallResult = "reached" | "not_reached" | "busy" | "wrong_number" | "refused";

export interface CallLog {
  id: number;
  contract_id: number;
  manager_id: number;
  called_at: string;
  phone_number: string;
  result: CallResult;
  duration_seconds?: number;
  notes?: string;
  created_at: string;
}

export interface DashboardSummary {
  total_debtors: number;
  active_contracts: number;
  total_debt: number;
  payments_this_month: number;
  payments_count_this_month: number;
  active_promises: number;
  overdue_promises: number;
  calls_today: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}
