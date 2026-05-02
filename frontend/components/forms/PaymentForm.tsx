"use client";
import { useState, useRef } from "react";
import { useForm } from "react-hook-form";
import { paymentService } from "@/services/api";
import { apiClient } from "@/lib/api-client";
import toast from "react-hot-toast";
import { Upload, X, FileCheck } from "lucide-react";

interface Props { contractId: number; onSuccess: () => void; onCancel: () => void; }

export default function PaymentForm({ contractId, onSuccess, onCancel }: Props) {
  const [loading, setLoading] = useState(false);
  const [receipt, setReceipt] = useState<File | null>(null);
  const [receiptPreview, setReceiptPreview] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const { register, handleSubmit, formState: { errors } } = useForm<any>({
    defaultValues: { source: "cash", payment_date: new Date().toISOString().slice(0, 10) },
  });

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const allowed = ["image/jpeg", "image/png", "image/heic", "application/pdf"];
    if (!allowed.includes(file.type)) {
      toast.error("Разрешены только JPG, PNG, PDF");
      return;
    }
    setReceipt(file);
    if (file.type.startsWith("image/")) {
      setReceiptPreview(URL.createObjectURL(file));
    } else {
      setReceiptPreview(null);
    }
  };

  const onSubmit = async (data: any) => {
    setLoading(true);
    try {
      const payment = await paymentService.create({
        contract_id: contractId,
        amount: Number(data.amount),
        payment_date: data.payment_date,
        source: data.source,
        reference: data.reference,
        notes: data.notes,
      });

      // Upload receipt if selected
      if (receipt && (payment as any).id) {
        const form = new FormData();
        form.append("file", receipt);
        await apiClient.post(`/payments/${(payment as any).id}/receipt`, form, {
          headers: { "Content-Type": "multipart/form-data" },
        });
      }

      toast.success("Платёж добавлен" + (receipt ? " с чеком ✓" : ""));
      onSuccess();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? "Ошибка");
    } finally { setLoading(false); }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">Сумма *</label>
        <input type="number" step="0.01" {...register("amount", { required: true, min: 1 })} className="input" placeholder="0.00" />
        {errors.amount && <p className="mt-1 text-xs text-red-500">Укажите сумму</p>}
      </div>
      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">Дата платежа *</label>
        <input type="date" {...register("payment_date", { required: true })} className="input" />
      </div>
      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">Источник</label>
        <select {...register("source")} className="input">
          <option value="cash">Наличные</option>
          <option value="card">Внутреннее ПТ</option>
          <option value="bank">Банковский перевод</option>
          <option value="court">Судебный</option>
        </select>
      </div>
      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">Примечание</label>
        <textarea {...register("notes")} className="input resize-none" rows={2} />
      </div>

      {/* Receipt upload */}
      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">Чек / Квитанция</label>
        <input
          ref={fileRef}
          type="file"
          accept="image/jpeg,image/png,image/heic,application/pdf"
          className="hidden"
          onChange={handleFileChange}
        />
        {!receipt ? (
          <button
            type="button"
            onClick={() => fileRef.current?.click()}
            className="flex w-full items-center justify-center gap-2 rounded-lg border-2 border-dashed border-gray-300 py-4 text-sm text-gray-500 hover:border-blue-400 hover:text-blue-500 transition-colors"
          >
            <Upload size={16} />
            Нажмите чтобы прикрепить чек (JPG, PNG, PDF)
          </button>
        ) : (
          <div className="rounded-lg border border-green-200 bg-green-50 p-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm text-green-700">
                <FileCheck size={16} />
                <span className="font-medium">{receipt.name}</span>
                <span className="text-xs text-green-500">({(receipt.size / 1024).toFixed(0)} КБ)</span>
              </div>
              <button type="button" onClick={() => { setReceipt(null); setReceiptPreview(null); }} className="text-gray-400 hover:text-red-500">
                <X size={16} />
              </button>
            </div>
            {receiptPreview && (
              <img src={receiptPreview} alt="Чек" className="mt-2 max-h-32 rounded object-contain" />
            )}
          </div>
        )}
      </div>

      <div className="flex justify-end gap-3">
        <button type="button" onClick={onCancel} className="btn-secondary">Отмена</button>
        <button type="submit" className="btn-primary" disabled={loading}>
          {loading ? "Сохранение..." : "Добавить платёж"}
        </button>
      </div>
    </form>
  );
}
