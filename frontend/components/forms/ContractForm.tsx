"use client";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { contractService, promiseService, paymentService, callLogService } from "@/services/api";
import toast from "react-hot-toast";

// ── ContractForm ──────────────────────────────────────────
interface ContractFormProps { debtorId: number; onSuccess: () => void; onCancel: () => void; }

export function ContractFormInner({ debtorId, onSuccess, onCancel }: ContractFormProps) {
  const [loading, setLoading] = useState(false);
  const { register, handleSubmit, formState: { errors } } = useForm<any>();

  const onSubmit = async (data: any) => {
    setLoading(true);
    try {
      await contractService.create({
        ...data,
        debtor_id: debtorId,
        principal_debt: Number(data.principal_debt),
        interest_debt: Number(data.interest_debt || 0),
        penalty_debt: Number(data.penalty_debt || 0),
        total_debt: Number(data.total_debt),
      });
      toast.success("Договор создан");
      onSuccess();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? "Ошибка");
    } finally { setLoading(false); }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div className="col-span-2">
          <label className="mb-1 block text-sm font-medium text-gray-700">Номер договора *</label>
          <input {...register("contract_number", { required: true })} className="input" />
          {errors.contract_number && <p className="mt-1 text-xs text-red-500">Обязательное поле</p>}
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Первоначальный кредитор *</label>
          <input {...register("original_creditor", { required: true })} className="input" />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Тип продукта</label>
          <input {...register("product_type")} className="input" placeholder="Потреб. кредит" />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Основной долг *</label>
          <input type="number" step="0.01" {...register("principal_debt", { required: true })} className="input" />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Проценты</label>
          <input type="number" step="0.01" {...register("interest_debt")} className="input" defaultValue={0} />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Пени</label>
          <input type="number" step="0.01" {...register("penalty_debt")} className="input" defaultValue={0} />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Итого долг *</label>
          <input type="number" step="0.01" {...register("total_debt", { required: true })} className="input" />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Дата выдачи</label>
          <input type="date" {...register("issue_date")} className="input" />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Дата просрочки</label>
          <input type="date" {...register("overdue_date")} className="input" />
        </div>
      </div>
      <div className="flex justify-end gap-3 pt-2">
        <button type="button" onClick={onCancel} className="btn-secondary">Отмена</button>
        <button type="submit" className="btn-primary" disabled={loading}>
          {loading ? "Создание..." : "Создать"}
        </button>
      </div>
    </form>
  );
}

export default ContractFormInner;
