"use client";
import { ReactNode, Fragment } from "react";
import clsx from "clsx";
import { X } from "lucide-react";

// ── Stat Card ─────────────────────────────────────────────
interface StatCardProps {
  label: string;
  value: string | number;
  sub?: string;
  color?: "blue" | "green" | "red" | "yellow";
  icon?: ReactNode;
}
export function StatCard({ label, value, sub, color = "blue", icon }: StatCardProps) {
  const colors = {
    blue: "bg-blue-50 text-blue-700",
    green: "bg-green-50 text-green-700",
    red: "bg-red-50 text-red-700",
    yellow: "bg-yellow-50 text-yellow-700",
  };
  return (
    <div className="card p-5">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-gray-500">{label}</p>
        {icon && (
          <span className={clsx("rounded-lg p-2 text-lg", colors[color])}>{icon}</span>
        )}
      </div>
      <p className="mt-2 text-2xl font-bold text-gray-900">{value}</p>
      {sub && <p className="mt-1 text-xs text-gray-500">{sub}</p>}
    </div>
  );
}

// ── Table ─────────────────────────────────────────────────
interface Column<T> {
  key: string;
  header: string;
  render?: (row: T) => ReactNode;
  className?: string;
}
interface TableProps<T> {
  columns: Column<T>[];
  data: T[];
  onRowClick?: (row: T) => void;
  loading?: boolean;
  emptyMessage?: string;
}
export function Table<T extends { id: number }>({
  columns, data, onRowClick, loading, emptyMessage = "Нет данных",
}: TableProps<T>) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200 bg-gray-50">
            {columns.map((col) => (
              <th
                key={col.key}
                className={clsx("px-4 py-3 text-left font-medium text-gray-600", col.className)}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {loading ? (
            <tr>
              <td colSpan={columns.length} className="py-12 text-center">
                <Spinner />
              </td>
            </tr>
          ) : data.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="py-12 text-center text-gray-400">
                {emptyMessage}
              </td>
            </tr>
          ) : (
            data.map((row) => (
              <tr
                key={row.id}
                onClick={() => onRowClick?.(row)}
                className={clsx(
                  "transition-colors",
                  onRowClick && "cursor-pointer hover:bg-blue-50"
                )}
              >
                {columns.map((col) => (
                  <td key={col.key} className={clsx("px-4 py-3 text-gray-700", col.className)}>
                    {col.render ? col.render(row) : (row as any)[col.key] ?? "—"}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}

// ── Pagination ─────────────────────────────────────────────
interface PaginationProps {
  page: number;
  pages: number;
  total: number;
  onPage: (p: number) => void;
}
export function Pagination({ page, pages, total, onPage }: PaginationProps) {
  if (pages <= 1) return null;
  return (
    <div className="flex items-center justify-between border-t border-gray-200 px-4 py-3">
      <p className="text-sm text-gray-500">Всего: {total}</p>
      <div className="flex gap-1">
        <button className="btn-secondary px-3 py-1 text-xs" disabled={page <= 1} onClick={() => onPage(page - 1)}>
          ←
        </button>
        <span className="flex items-center px-3 text-sm text-gray-600">
          {page} / {pages}
        </span>
        <button className="btn-secondary px-3 py-1 text-xs" disabled={page >= pages} onClick={() => onPage(page + 1)}>
          →
        </button>
      </div>
    </div>
  );
}

// ── Modal ─────────────────────────────────────────────────
interface ModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  size?: "sm" | "md" | "lg";
}
export function Modal({ open, onClose, title, children, size = "md" }: ModalProps) {
  if (!open) return null;
  const sizes = { sm: "max-w-sm", md: "max-w-lg", lg: "max-w-2xl" };
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className={clsx("relative w-full rounded-xl bg-white shadow-xl", sizes[size])}>
        <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
          <h3 className="text-base font-semibold text-gray-900">{title}</h3>
          <button onClick={onClose} className="rounded-lg p-1 hover:bg-gray-100">
            <X size={18} />
          </button>
        </div>
        <div className="p-6">{children}</div>
      </div>
    </div>
  );
}

// ── Badge ─────────────────────────────────────────────────
const badgeVariants: Record<string, string> = {
  active: "badge-active",
  done: "badge-done",
  overdue: "badge-overdue",
  cancelled: "badge-default",
  closed: "badge-default",
  litigation: "bg-purple-100 text-purple-800 inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
  written_off: "badge-default",
};
export function Badge({ status, label }: { status: string; label: string }) {
  return <span className={badgeVariants[status] ?? "badge-default"}>{label}</span>;
}

// ── Spinner ────────────────────────────────────────────────
export function Spinner({ size = "md" }: { size?: "sm" | "md" | "lg" }) {
  const s = { sm: "h-4 w-4", md: "h-6 w-6", lg: "h-10 w-10" };
  return (
    <div className={clsx("animate-spin rounded-full border-2 border-primary-500 border-t-transparent mx-auto", s[size])} />
  );
}

// ── Page Header ────────────────────────────────────────────
export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: string; actions?: ReactNode }) {
  return (
    <div className="mb-6 flex items-start justify-between gap-4">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-gray-500">{subtitle}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}
