"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { authService } from "@/services/auth";
import { useAuth } from "@/lib/auth-context";
import toast from "react-hot-toast";

interface LoginForm {
  email: string;
  password: string;
}

export default function LoginPage() {
  const router = useRouter();
  const { setUser } = useAuth();
  const [loading, setLoading] = useState(false);
  const { register, handleSubmit, formState: { errors } } = useForm<LoginForm>();

  const onSubmit = async (data: LoginForm) => {
    setLoading(true);
    try {
      const res = await authService.login(data.email, data.password);
      setUser(res.user);
      toast.success(`Добро пожаловать, ${res.user.full_name}!`);
      // Smart redirect по роли:
      //   MANAGER → /my-day (план дня — главное место менеджера)
      //   HEAD/ADMIN → /control-panel (мониторинг команды)
      const role = (res.user.role || "").toUpperCase();
      const target = role === "MANAGER" ? "/my-day" : "/control-panel";
      router.replace(target);
    } catch (err: any) {
      toast.error(err?.response?.data?.detail ?? "Неверный email или пароль");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-primary-900 to-primary-700 p-4">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-white">CRM Collector</h1>
          <p className="mt-2 text-primary-200">Система управления взысканием</p>
        </div>

        <div className="card p-8">
          <h2 className="mb-6 text-xl font-semibold text-gray-900">Вход в систему</h2>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div>
              <label className="mb-1.5 block text-sm font-medium text-gray-700">Email</label>
              <input
                type="email"
                {...register("email", { required: "Введите email" })}
                className="input"
                placeholder="admin@crm.local"
                autoComplete="email"
              />
              {errors.email && <p className="mt-1 text-xs text-red-500">{errors.email.message}</p>}
            </div>

            <div>
              <label className="mb-1.5 block text-sm font-medium text-gray-700">Пароль</label>
              <input
                type="password"
                {...register("password", { required: "Введите пароль" })}
                className="input"
                placeholder="••••••••"
                autoComplete="current-password"
              />
              {errors.password && <p className="mt-1 text-xs text-red-500">{errors.password.message}</p>}
            </div>

            <button type="submit" className="btn-primary w-full py-2.5" disabled={loading}>
              {loading ? "Входим..." : "Войти"}
            </button>
          </form>

          <p className="mt-4 text-center text-xs text-gray-400">
            По умолчанию: admin@crm.local / Admin1234!
          </p>
        </div>
      </div>
    </div>
  );
}
