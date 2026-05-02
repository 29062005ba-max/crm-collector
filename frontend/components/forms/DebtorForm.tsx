"use client";
import { useForm } from "react-hook-form";
import { debtorService } from "@/services/api";
import type { Debtor } from "@/types/api";
import toast from "react-hot-toast";
import { useState } from "react";

interface Props {
  debtor?: Debtor;
  onSuccess: () => void;
  onCancel: () => void;
}

type FormData = {
  iin: string; full_name: string; birth_date?: string;
  phone_primary?: string; phone_secondary?: string;
  email?: string; address?: string; employer?: string;
  employer_phone?: string; notes?: string;
};

export default function DebtorForm({ debtor, onSuccess, onCancel }: Props) {
  const [loading, setLoading] = useState(false);
  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({
    defaultValues: debtor ? {
      iin: debtor.iin, full_name: debtor.full_name,
      birth_date: debtor.birth_date ?? undefined,
      phone_primary: debtor.phone_primary ?? undefined,
      phone_secondary: debtor.phone_secondary ?? undefined,
      email: debtor.email ?? undefined,
      address: debtor.address ?? undefined,
      employer: debtor.employer ?? undefined,
      employer_phone: debtor.employer_phone ?? undefined,
      notes: debtor.notes ?? undefined,
    } : {},
  });

  const onSubmit = async (data: FormData) => {
    setLoading(true);
    try {
      if (debtor) {
        await debtorService.update(debtor.id, data);
        toast.success("Должник обновлён");
      } else {
        await debtorService.create(data);
        toast.success("Должник создан");
      }
      onSuccess();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? "Ошибка");
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">ИИН *</label>
          <input {...register("iin", { required: true, minLength: 12, maxLength: 12 })} className="input" placeholder="123456789012" disabled={!!debtor} />
          {errors.iin && <p className="mt-1 text-xs text-red-500">12 цифр</p>}
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">ФИО *</label>
          <input {...register("full_name", { required: true })} className="input" placeholder="Иванов Иван Иванович" />
          {errors.full_name && <p className="mt-1 text-xs text-red-500">Обязательное поле</p>}
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Дата рождения</label>
          <input type="date" {...register("birth_date")} className="input" />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Телефон</label>
          <input {...register("phone_primary")} className="input" placeholder="+7 700 000 0000" />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Доп. телефон</label>
          <input {...register("phone_secondary")} className="input" />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Email</label>
          <input type="email" {...register("email")} className="input" />
        </div>
        <div className="col-span-2">
          <label className="mb-1 block text-sm font-medium text-gray-700">Адрес</label>
          <input {...register("address")} className="input" />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Место работы</label>
          <input {...register("employer")} className="input" />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Тел. работы</label>
          <input {...register("employer_phone")} className="input" />
        </div>
        <div className="col-span-2">
          <label className="mb-1 block text-sm font-medium text-gray-700">Примечание</label>
          <textarea {...register("notes")} className="input resize-none" rows={2} />
        </div>
      </div>
      <div className="flex justify-end gap-3 pt-2">
        <button type="button" onClick={onCancel} className="btn-secondary">Отмена</button>
        <button type="submit" className="btn-primary" disabled={loading}>
          {loading ? "Сохранение..." : debtor ? "Обновить" : "Создать"}
        </button>
      </div>
    </form>
  );
}
