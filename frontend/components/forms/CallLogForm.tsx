"use client";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { callLogService } from "@/services/api";
import toast from "react-hot-toast";

interface Props { contractId: number; onSuccess: () => void; onCancel: () => void; }

export default function CallLogForm({ contractId, onSuccess, onCancel }: Props) {
  const [loading, setLoading] = useState(false);
  const { register, handleSubmit, formState: { errors } } = useForm<any>({
    defaultValues: { result: "reached", called_at: new Date().toISOString().slice(0, 16) },
  });

  const onSubmit = async (data: any) => {
    setLoading(true);
    try {
      await callLogService.create({ contract_id: contractId, called_at: new Date(data.called_at).toISOString(), phone_number: data.phone_number, result: data.result, duration_seconds: data.duration_seconds ? Number(data.duration_seconds) : undefined, notes: data.notes });
      toast.success("Звонок добавлен");
      onSuccess();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? "Ошибка");
    } finally { setLoading(false); }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">Дата и время *</label>
        <input type="datetime-local" {...register("called_at", { required: true })} className="input" />
      </div>
      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">Номер телефона *</label>
        <input {...register("phone_number", { required: true })} className="input" placeholder="+7 700 000 0000" />
        {errors.phone_number && <p className="mt-1 text-xs text-red-500">Обязательное поле</p>}
      </div>
      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">Результат *</label>
        <select {...register("result")} className="input">
          <option value="reached">Дозвонились</option>
          <option value="not_reached">Не дозвонились</option>
          <option value="busy">Занято</option>
          <option value="wrong_number">Неверный номер</option>
          <option value="refused">Отказ</option>
        </select>
      </div>
      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">Длительность (сек)</label>
        <input type="number" {...register("duration_seconds")} className="input" placeholder="60" />
      </div>
      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">Примечание</label>
        <textarea {...register("notes")} className="input resize-none" rows={2} />
      </div>
      <div className="flex justify-end gap-3">
        <button type="button" onClick={onCancel} className="btn-secondary">Отмена</button>
        <button type="submit" className="btn-primary" disabled={loading}>{loading ? "..." : "Сохранить"}</button>
      </div>
    </form>
  );
}
