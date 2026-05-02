"use client";
import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard, Users, CalendarCheck,
  CreditCard, LogOut, BarChart2, UserCheck, Phone, Trello, ListChecks, Activity,
  PhoneCall, Flame, Headphones, Sun, Crown, FolderArchive, ChevronDown, ChevronRight,
} from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import clsx from "clsx";

type NavItem = {
  href: string;
  label: string;
  icon: any;
  roles?: string[];
};

type ArchiveGroup = {
  type: "group";
  key: string;
  label: string;
  icon: any;
  roles: string[];
  items: NavItem[];
};

type SidebarItem = NavItem | ArchiveGroup;

// === MANAGER navigation ===
const MANAGER_NAV: SidebarItem[] = [
  { href: "/my-day", label: "План на день", icon: Sun },
  { href: "/call-queue", label: "Автодозвон", icon: PhoneCall },
  { href: "/priority", label: "Приоритет", icon: Flame },
  { href: "/debtors", label: "Должники", icon: Users },
  { href: "/tasks", label: "Задачи", icon: ListChecks },
  { href: "/promises", label: "Обещания", icon: CalendarCheck },
  {
    type: "group",
    key: "archive",
    label: "Архив",
    icon: FolderArchive,
    roles: ["MANAGER"],
    items: [
      { href: "/payments", label: "Платежи", icon: CreditCard },
      { href: "/calls", label: "История звонков", icon: Phone },
      { href: "/kanban", label: "Канбан", icon: Trello },
    ],
  },
];

// === HEAD / ADMIN navigation ===
const HEAD_NAV: SidebarItem[] = [
  { href: "/dashboard", label: "Дашборд", icon: LayoutDashboard },
  { href: "/control-panel", label: "Контрольная панель", icon: Crown },
  { href: "/debtors", label: "Должники", icon: Users },
  { href: "/priority", label: "Приоритет", icon: Flame },
  { href: "/kanban", label: "Канбан", icon: Trello },
  { href: "/my-day", label: "План на день", icon: Sun },
  { href: "/call-queue/admin", label: "Управление обзвоном", icon: Headphones },
  { href: "/tasks", label: "Задачи", icon: ListChecks },
  { href: "/promises", label: "Обещания", icon: CalendarCheck },
  { href: "/users", label: "Пользователи", icon: UserCheck },
  { href: "/kpi", label: "Отчёты", icon: BarChart2 },
  { href: "/admin/jobs", label: "Background Jobs", icon: Activity, roles: ["ADMIN"] },
];

function isGroup(item: SidebarItem): item is ArchiveGroup {
  return (item as ArchiveGroup).type === "group";
}

export default function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const userRole = (user?.role || "").toUpperCase();

  // Архив: открыт/свёрнут — сохраняется в localStorage
  const [archiveOpen, setArchiveOpen] = useState(false);

  useEffect(() => {
    const saved = typeof window !== "undefined" ? localStorage.getItem("sidebar.archive.open") : null;
    if (saved !== null) setArchiveOpen(saved === "true");
  }, []);

  const toggleArchive = () => {
    setArchiveOpen((prev) => {
      const next = !prev;
      try { localStorage.setItem("sidebar.archive.open", String(next)); } catch {}
      return next;
    });
  };

  // Выбираем nav в зависимости от роли
  const isManager = userRole === "MANAGER";
  const baseNav = isManager ? MANAGER_NAV : HEAD_NAV;

  // Фильтруем по дополнительным roles (для admin-only пунктов)
  const allowed = baseNav.filter((item) => {
    if (isGroup(item)) return item.roles.includes(userRole);
    return !item.roles || item.roles.includes(userRole);
  });

  // Активность подпункта в группе → подсветить и саму группу
  const archivePath = isManager
    ? (allowed.find(isGroup)?.items.some((i) => pathname.startsWith(i.href)) ?? false)
    : false;

  // Авто-раскрыть Архив, если пользователь сейчас на странице из Архива
  useEffect(() => {
    if (archivePath && !archiveOpen) setArchiveOpen(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [archivePath]);

  return (
    <aside className="fixed inset-y-0 left-0 z-40 flex w-64 flex-col border-r border-gray-200 bg-white lg:static">
      <div className="flex h-16 items-center border-b border-gray-200 px-6">
        <span className="text-lg font-bold text-primary-700">CRM Collector</span>
      </div>

      <nav className="flex flex-1 flex-col gap-1 overflow-y-auto p-4">
        {allowed.map((item) => {
          if (isGroup(item)) {
            const Icon = item.icon;
            const isAnyChildActive = item.items.some((i) => pathname.startsWith(i.href));
            return (
              <div key={item.key} className="flex flex-col">
                <button
                  onClick={toggleArchive}
                  className={clsx(
                    "flex items-center justify-between rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                    isAnyChildActive
                      ? "bg-primary-50 text-primary-700"
                      : "text-gray-600 hover:bg-gray-100 hover:text-gray-900"
                  )}
                >
                  <span className="flex items-center gap-3">
                    <Icon size={18} />
                    {item.label}
                  </span>
                  {archiveOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                </button>
                {archiveOpen && (
                  <div className="mt-1 ml-3 flex flex-col gap-1 border-l border-gray-200 pl-3">
                    {item.items.map(({ href, label, icon: SubIcon }) => {
                      const isActive = pathname.startsWith(href);
                      return (
                        <Link
                          key={href}
                          href={href}
                          className={clsx(
                            "flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors",
                            isActive
                              ? "bg-primary-600 text-white"
                              : "text-gray-600 hover:bg-gray-100 hover:text-gray-900"
                          )}
                        >
                          <SubIcon size={15} />
                          {label}
                        </Link>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          }
          const { href, label, icon: Icon } = item;
          const isActive = href === "/call-queue"
            ? pathname === "/call-queue"
            : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={clsx(
                "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                isActive
                  ? "bg-primary-600 text-white"
                  : "text-gray-600 hover:bg-gray-100 hover:text-gray-900"
              )}
            >
              <Icon size={18} />
              {label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-gray-200 p-4">
        <div className="mb-3 flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-primary-100 text-sm font-bold text-primary-700">
            {user?.full_name?.[0] ?? "?"}
          </div>
          <div className="min-w-0">
            <p className="truncate text-sm font-medium">{user?.full_name}</p>
            <p className="truncate text-xs text-gray-500">{user?.email}</p>
          </div>
        </div>
        <button
          onClick={logout}
          className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-red-600 hover:bg-red-50 transition-colors"
        >
          <LogOut size={16} />
          Выйти
        </button>
      </div>
    </aside>
  );
}
