"use client";
import { ReactNode } from "react";
import clsx from "clsx";
import { X } from "lucide-react";

// ── Stat Card (iOS-style with gradient and large rounded) ──────────────
interface StatCardProps {
  label: string;
  value: string | number;
  sub?: string;
  color?: "blue" | "green" | "red" | "yellow" | "purple" | "orange";
  icon?: ReactNode;
}
export function StatCard({ label, value, sub, color = "blue", icon }: StatCardProps) {
  const colors = {
    blue:   "bg-primary-50 text-primary-600",
    green:  "bg-success-50 text-success-600",
    red:    "bg-danger-50 text-danger-600",
    yellow: "bg-warning-50 text-warning-600",
    purple: "bg-purple-50 text-purple-600",
    orange: "bg-orange-50 text-orange-600",
  };
  const cardBg = {
    blue:   "kpi-card-blue",
    green:  "kpi-card-green",
    red:    "kpi-card-red",
    yellow: "kpi-card-orange",
    purple: "kpi-card-purple",
    orange: "kpi-card-orange",
  };
  return (
    <div className={cardBg[color]}>
      <div className="flex items-center justify-between">
        <p className="text-sm font-semibold text-gray-500">{label}</p>
        {icon && (
          <span className={clsx("rounded-2xl p-2.5 text-lg", colors[color])}>{icon}</span>
        )}
      </div>
      <p className="mt-3 text-3xl font-bold tracking-tight text-gray-900">{value}</p>
      {sub && <p className="mt-1.5 text-xs font-medium text-gray-500">{sub}</p>}
    </div>
  );
}

// ── Table (no harsh borders, soft hover) ───────────────────────────────
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
    <div className="overflow-x-auto rounded-3xl">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-gray-50/60">
            {columns.map((col, i) => (
              <th
                key={col.key}
                className={clsx(
                  "px-5 py-3.5 text-left text-xs font-semibold uppercase tracking-wider text-gray-500",
                  i === 0 && "rounded-tl-3xl",
                  i === columns.length - 1 && "rounded-tr-3xl",
                  col.className
                )}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {loading ? (
            <tr>
              <td colSpan={columns.length} className="py-16 text-center">
                <Spinner />
              </td>
            </tr>
          ) : data.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="py-16 text-center text-gray-400 font-medium">
                {emptyMessage}
              </td>
            </tr>
          ) : (
            data.map((row) => (
              <tr
                key={row.id}
                onClick={() => onRowClick?.(row)}
                className={clsx(
                  "table-row",
                  onRowClick && "cursor-pointer"
                )}
              >
                {columns.map((col) => (
                  <td key={col.key} className={clsx("px-5 py-4 text-gray-700", col.className)}>
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

// ── Pagination (pill-style buttons) ────────────────────────────────────
interface PaginationProps {
  page: number;
  pages: number;
  total: number;
  onPage: (p: number) => void;
}
export function Pagination({ page, pages, total, onPage }: PaginationProps) {
  if (pages <= 1) return null;
  return (
    <div className="flex items-center justify-between border-t border-gray-100 px-5 py-4">
      <p className="text-sm font-medium text-gray-500">Всего: {total}</p>
      <div className="flex items-center gap-2">
        <button
          className="flex h-9 w-9 items-center justify-center rounded-full border border-gray-200 bg-white text-gray-600 shadow-soft transition-all hover:bg-gray-50 hover:-translate-y-0.5 disabled:opacity-40 disabled:translate-y-0"
          disabled={page <= 1}
          onClick={() => onPage(page - 1)}
        >
          ←
        </button>
        <span className="px-3 text-sm font-semibold text-gray-700">
          {page} / {pages}
        </span>
        <button
          className="flex h-9 w-9 items-center justify-center rounded-full border border-gray-200 bg-white text-gray-600 shadow-soft transition-all hover:bg-gray-50 hover:-translate-y-0.5 disabled:opacity-40 disabled:translate-y-0"
          disabled={page >= pages}
          onClick={() => onPage(page + 1)}
        >
          →
        </button>
      </div>
    </div>
  );
}

// ── Modal (with backdrop blur and spring animation) ────────────────────
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
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 animate-fade-in">
      <div
        className="absolute inset-0 bg-gray-900/40 backdrop-blur-sm"
        onClick={onClose}
      />
      <div className={clsx(
        "relative w-full rounded-3xl bg-white shadow-modal animate-scale-in",
        sizes[size]
      )}>
        <div className="flex items-center justify-between border-b border-gray-100 px-6 py-5">
          <h3 className="text-lg font-bold tracking-tight text-gray-900">{title}</h3>
          <button
            onClick={onClose}
            className="flex h-9 w-9 items-center justify-center rounded-full text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-700"
          >
            <X size={18} />
          </button>
        </div>
        <div className="p-6">{children}</div>
      </div>
    </div>
  );
}

// ── Badge (pastel iOS tones) ───────────────────────────────────────────
const badgeVariants: Record<string, string> = {
  active: "badge-active",
  done: "badge-done",
  overdue: "badge-overdue",
  cancelled: "badge-default",
  closed: "badge-default",
  litigation: "inline-flex items-center rounded-full bg-purple-50 px-3 py-1 text-xs font-semibold text-purple-600",
  written_off: "badge-default",
  hot: "badge-hot",
  fulfilled: "badge-active",
};
export function Badge({ status, label }: { status: string; label: string }) {
  return <span className={badgeVariants[status] ?? "badge-default"}>{label}</span>;
}

// ── Spinner (smoother) ─────────────────────────────────────────────────
export function Spinner({ size = "md" }: { size?: "sm" | "md" | "lg" }) {
  const s = { sm: "h-4 w-4", md: "h-6 w-6", lg: "h-10 w-10" };
  return (
    <div className={clsx(
      "animate-spin rounded-full border-[2.5px] border-gray-200 border-t-primary-500 mx-auto",
      s[size]
    )} />
  );
}

// ── Page Header (large iOS-style title) ────────────────────────────────
export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: string; actions?: ReactNode }) {
  return (
    <div className="mb-8 flex items-start justify-between gap-4 animate-slide-up">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-gray-900">{title}</h1>
        {subtitle && <p className="mt-1.5 text-sm font-medium text-gray-500">{subtitle}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}
