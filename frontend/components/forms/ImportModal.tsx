"use client";
import { useState, useRef } from "react";
import { Modal } from "@/components/ui";
import { importService } from "@/services/api";
import toast from "react-hot-toast";
import { Upload, FileSpreadsheet, CheckCircle, AlertCircle } from "lucide-react";

interface Props { open: boolean; onClose: () => void; }

interface ImportResult {
  total_rows: number; success_rows: number; error_rows: number;
  status: string; errors?: { row: number; error: string }[];
}

export default function ImportModal({ open, onClose }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ImportResult | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = (f: File) => {
    if (!f.name.match(/\.(xlsx|xls)$/)) { toast.error("Только .xlsx / .xls файлы"); return; }
    setFile(f);
    setResult(null);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const f = e.dataTransfer.files[0];
    if (f) handleFile(f);
  };

  const handleImport = async () => {
    if (!file) return;
    setLoading(true);
    try {
      const res = await importService.importExcel(file);
      setResult(res);
      if (res.error_rows === 0) toast.success(`Импортировано ${res.success_rows} записей`);
      else toast.success(`Импорт завершён: ${res.success_rows} ок, ${res.error_rows} ошибок`);
    } catch (e: any) {
      toast.error("Ошибка при импорте");
    } finally { setLoading(false); }
  };

  const handleClose = () => { setFile(null); setResult(null); onClose(); };

  return (
    <Modal open={open} onClose={handleClose} title="Импорт должников из Excel" size="md">
      <div className="space-y-4">
        {!result ? (
          <>
            <div
              onDrop={handleDrop}
              onDragOver={(e) => e.preventDefault()}
              onClick={() => inputRef.current?.click()}
              className="flex cursor-pointer flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed border-gray-300 p-8 transition hover:border-primary-400 hover:bg-blue-50"
            >
              <FileSpreadsheet size={40} className="text-gray-400" />
              {file ? (
                <p className="text-sm font-medium text-primary-700">{file.name}</p>
              ) : (
                <>
                  <p className="text-sm font-medium text-gray-700">Перетащите файл или нажмите для выбора</p>
                  <p className="text-xs text-gray-400">Поддерживаемые форматы: .xlsx, .xls</p>
                </>
              )}
            </div>
            <input ref={inputRef} type="file" accept=".xlsx,.xls" className="hidden" onChange={(e) => { if (e.target.files?.[0]) handleFile(e.target.files[0]); }} />

            <div className="rounded-lg bg-gray-50 p-3 text-xs text-gray-600">
              <p className="mb-1 font-semibold">Ожидаемые колонки:</p>
              <p className="font-mono">iin, full_name, phone, address, employer, contract_number, creditor, product_type, principal_debt, interest_debt, penalty_debt, total_debt</p>
            </div>

            <div className="flex justify-end gap-3">
              <button onClick={handleClose} className="btn-secondary">Отмена</button>
              <button onClick={handleImport} disabled={!file || loading} className="btn-primary">
                <Upload size={16} />
                {loading ? "Импорт..." : "Импортировать"}
              </button>
            </div>
          </>
        ) : (
          <div className="space-y-4">
            <div className="grid grid-cols-3 gap-3">
              <div className="rounded-lg bg-gray-50 p-3 text-center">
                <p className="text-2xl font-bold text-gray-900">{result.total_rows}</p>
                <p className="text-xs text-gray-500">Всего строк</p>
              </div>
              <div className="rounded-lg bg-green-50 p-3 text-center">
                <p className="text-2xl font-bold text-green-700">{result.success_rows}</p>
                <p className="text-xs text-green-600">Успешно</p>
              </div>
              <div className="rounded-lg bg-red-50 p-3 text-center">
                <p className="text-2xl font-bold text-red-700">{result.error_rows}</p>
                <p className="text-xs text-red-600">Ошибки</p>
              </div>
            </div>

            {result.errors && result.errors.length > 0 && (
              <div className="max-h-48 overflow-y-auto rounded-lg border border-red-200 bg-red-50 p-3">
                <p className="mb-2 text-xs font-semibold text-red-700">Ошибки:</p>
                {result.errors.slice(0, 20).map((err, i) => (
                  <p key={i} className="text-xs text-red-600">Строка {err.row}: {err.error}</p>
                ))}
              </div>
            )}

            <div className="flex justify-end">
              <button onClick={handleClose} className="btn-primary">Закрыть</button>
            </div>
          </div>
        )}
      </div>
    </Modal>
  );
}
