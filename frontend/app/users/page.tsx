"use client";
import { useEffect, useState } from "react";
import AppShell from "@/components/layout/AppShell";
import { Badge, Modal, PageHeader, Table, Spinner } from "@/components/ui";
import { userService } from "@/services/api";
import { formatDate, ROLE_LABELS } from "@/lib/utils";
import type { User } from "@/types/api";
import { Plus } from "lucide-react";
import toast from "react-hot-toast";
import UserForm from "@/components/forms/UserForm";

export default function UsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [editUser, setEditUser] = useState<User | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      setUsers(await userService.list());
    } catch {
      toast.error("Ошибка загрузки пользователей");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const handleDeactivate = async (user: User) => {
    if (!confirm(`Деактивировать пользователя ${user.full_name}?`)) return;
    try {
      await userService.update(user.id, { is_active: false });
      toast.success("Пользователь деактивирован");
      load();
    } catch {
      toast.error("Ошибка");
    }
  };

  const columns = [
    { key: "full_name", header: "ФИО" },
    { key: "email", header: "Email", className: "text-sm text-gray-500" },
    {
      key: "role",
      header: "Роль",
      render: (r: User) => <Badge status={r.role} label={ROLE_LABELS[r.role] ?? r.role} />,
    },
    {
      key: "is_active",
      header: "Статус",
      render: (r: User) => <Badge status={r.is_active ? "active" : "closed"} label={r.is_active ? "Активный" : "Неактивный"} />,
    },
    { key: "created_at", header: "Добавлен", render: (r: User) => formatDate(r.created_at) },
    {
      key: "actions",
      header: "",
      render: (r: User) => (
        <div className="flex gap-2" onClick={(e) => e.stopPropagation()}>
          <button className="btn-secondary py-1 px-2 text-xs" onClick={() => setEditUser(r)}>
            Изменить
          </button>
          {r.is_active && (
            <button className="btn-danger py-1 px-2 text-xs" onClick={() => handleDeactivate(r)}>
              Откл.
            </button>
          )}
        </div>
      ),
    },
  ];

  return (
    <AppShell>
      <PageHeader
        title="Пользователи"
        subtitle="Управление учётными записями"
        actions={
          <button className="btn-primary" onClick={() => setShowCreate(true)}>
            <Plus size={16} /> Добавить
          </button>
        }
      />

      <div className="card overflow-hidden">
        {loading ? (
          <div className="flex justify-center py-16"><Spinner size="lg" /></div>
        ) : (
          <Table columns={columns} data={users} emptyMessage="Нет пользователей" />
        )}
      </div>

      <Modal open={showCreate} onClose={() => setShowCreate(false)} title="Новый пользователь">
        <UserForm onSuccess={() => { setShowCreate(false); load(); }} onCancel={() => setShowCreate(false)} />
      </Modal>

      <Modal open={!!editUser} onClose={() => setEditUser(null)} title="Редактировать пользователя">
        {editUser && (
          <UserForm user={editUser} onSuccess={() => { setEditUser(null); load(); }} onCancel={() => setEditUser(null)} />
        )}
      </Modal>
    </AppShell>
  );
}
