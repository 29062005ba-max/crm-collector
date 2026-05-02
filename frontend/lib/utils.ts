export function formatMoney(amount: number, currency = "KZT"): string {
  return new Intl.NumberFormat("ru-KZ", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(amount);
}

export function formatDate(dateStr?: string | null): string {
  if (!dateStr) return "—";
  return new Date(dateStr).toLocaleDateString("ru-KZ", {
    day: "2-digit", month: "2-digit", year: "numeric",
  });
}

export function formatDateTime(dateStr?: string | null): string {
  if (!dateStr) return "—";
  return new Date(dateStr).toLocaleString("ru-KZ", {
    day: "2-digit", month: "2-digit", year: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

export const CONTRACT_STATUS_LABELS: Record<string, string> = {
  active: "Досудебный",
  litigation: "Судебный",
  closed: "Закрыт",
  written_off: "Списан",
};

export const CONTRACT_STATUS_COLORS: Record<string, string> = {
  active: "bg-blue-100 text-blue-800",
  litigation: "bg-red-100 text-red-800",
  closed: "bg-green-100 text-green-800",
  written_off: "bg-gray-100 text-gray-600",
};

export const PROMISE_STATUS_LABELS: Record<string, string> = {
  active: "Активное",
  done: "Выполнено",
  overdue: "Просрочено",
  cancelled: "Отменено",
};

export const CALL_RESULT_LABELS: Record<string, string> = {
  reached: "Дозвонились",
  not_reached: "Не дозвонились",
  busy: "Занято",
  wrong_number: "Неверный номер",
  refused: "Отказ",
};

export const ROLE_LABELS: Record<string, string> = {
  admin: "Администратор",
  head: "Руководитель",
  manager: "Менеджер",
  ADMIN: "Администратор",
  HEAD: "Руководитель",
  MANAGER: "Менеджер",
};
