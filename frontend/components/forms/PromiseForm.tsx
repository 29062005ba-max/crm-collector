"use client";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { promiseService } from "@/services/api";
import toast from "react-hot-toast";

interface Props { contractId: number; onSuccess: () => void; onCancel: () => void; }

export default function PromiseForm({ contractId, onSuccess, onCancel }: Props) {
  const [loading, setLoading] = useState(false);
  const { register, handleSubmit, formState: { errors } } = useForm<any>();

  const onSubmit = async (data: any) => {
    setLoading(true);
    try {
      await promiseService.create({ contract_id: contractId, promise_date: data.promise_date, amount: Number(data.amount), notes: data.notes });
      toast.success("Обещание добавлено");
      onSuccess();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? "Ошибка");
    } finally { setLoading(false); }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">Дата обещания *</label>
        <input type="date" {...register("promise_date", { required: true })} className="input" />
        {errors.promise_date && <p className="mt-1 text-xs text-red-500">Обязательное поле</p>}
      </div>
      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">Сумма *</label>
        <input type="number" step="0.01" {...register("amount", { required: true, min: 1 })} className="input" />
        {errors.amount && <p className="mt-1 text-xs text-red-500">Укажите сумму</p>}
      </div>
      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">Примечание</label>
        <textarea {...register("notes")} className="input resize-none" rows={2} />
      </div>
      <div className="flex justify-end gap-3">
        <button type="button" onClick={onCancel} className="btn-secondary">Отмена</button>
        <button type="submit" className="btn-primary" disabled={loading}>{loading ? "..." : "Добавить"}</button>
      </div>
    </form>
  );
}
