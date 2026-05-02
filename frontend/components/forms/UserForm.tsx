"use client";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { userService } from "@/services/api";
import type { User } from "@/types/api";
import toast from "react-hot-toast";

interface Props { user?: User; onSuccess: () => void; onCancel: () => void; }

type FormData = {
  email: string; full_name: string; password?: string;
  role: string; phone?: string;
};

export default function UserForm({ user, onSuccess, onCancel }: Props) {
  const [loading, setLoading] = useState(false);
  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({
    defaultValues: user
      ? { email: user.email, full_name: user.full_name, role: user.role, phone: user.phone ?? undefined }
      : { role: "MANAGER" },
  });

  const onSubmit = async (data: FormData) => {
    setLoading(true);
    try {
      if (user) {
        const payload: any = { full_name: data.full_name, role: data.role, phone: data.phone };
        if (data.password) payload.password = data.password;
        await userService.update(user.id, payload);
        toast.success("Пользователь обновлён");
      } else {
        if (!data.password) { toast.error("Укажите пароль"); setLoading(false); return; }
        await userService.create({
          email: data.email,
          full_name: data.full_name,
          password: data.password,
          role: data.role,
          phone: data.phone,
        });
        toast.success("Пользователь создан");
      }
      onSuccess();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? "Ошибка сервера");
    } finally { setLoading(false); }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">ФИО *</label>
        <input {...register("full_name", { required: true })} className="input" />
        {errors.full_name && <p className="mt-1 text-xs text-red-500">Обязательное поле</p>}
      </div>
      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">Email *</label>
        <input type="email" {...register("email", { required: true })} className="input" disabled={!!user} />
        {errors.email && <p className="mt-1 text-xs text-red-500">Обязательное поле</p>}
      </div>
      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">
          {user ? "Новый пароль (оставьте пустым — без изменений)" : "Пароль *"}
        </label>
        <input type="password" {...register("password")} className="input" placeholder="Минимум 6 символов" />
      </div>
      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">Роль *</label>
        <select {...register("role", { required: true })} className="input">
          <option value="MANAGER">Менеджер</option>
          <option value="HEAD">Руководитель</option>
          <option value="ADMIN">Администратор</option>
        </select>
      </div>
      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">Телефон</label>
        <input {...register("phone")} className="input" placeholder="+7 700 000 0000" />
      </div>
      <div className="flex justify-end gap-3 pt-2">
        <button type="button" onClick={onCancel} className="btn-secondary">Отмена</button>
        <button type="submit" className="btn-primary" disabled={loading}>
          {loading ? "Сохранение..." : user ? "Обновить" : "Создать"}
        </button>
      </div>
    </form>
  );
}
