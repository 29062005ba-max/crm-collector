"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { authService } from "@/services/auth";
import { useAuth } from "@/lib/auth-context";
import toast from "react-hot-toast";
import { Crown, Mail, Lock } from "lucide-react";

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
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-gray-50 p-4">
      {/* Soft gradient blobs */}
      <div className="absolute -top-24 -left-24 h-96 w-96 rounded-full bg-gradient-to-br from-primary-200 to-primary-100 opacity-40 blur-3xl" />
      <div className="absolute -bottom-24 -right-24 h-96 w-96 rounded-full bg-gradient-to-br from-purple-200 to-pink-100 opacity-40 blur-3xl" />

      <div className="relative w-full max-w-md animate-scale-in">
        {/* Logo */}
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-3xl bg-gradient-to-br from-primary-500 to-primary-700 shadow-lifted">
            <Crown size={32} className="text-white" />
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-gray-900">CRM Collector</h1>
          <p className="mt-1.5 text-sm font-medium text-gray-500">Система управления взысканием</p>
        </div>

        {/* Card */}
        <div className="rounded-3xl bg-white p-8 shadow-modal">
          <h2 className="mb-6 text-xl font-bold tracking-tight text-gray-900">Вход в систему</h2>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div>
              <label className="mb-2 block text-sm font-semibold text-gray-700">Email</label>
              <div className="relative">
                <Mail size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" />
                <input
                  type="email"
                  {...register("email", { required: "Введите email" })}
                  className="input pl-11"
                  placeholder="admin@crm.local"
                  autoComplete="email"
                />
              </div>
              {errors.email && <p className="mt-1.5 text-xs font-medium text-danger-500">{errors.email.message}</p>}
            </div>

            <div>
              <label className="mb-2 block text-sm font-semibold text-gray-700">Пароль</label>
              <div className="relative">
                <Lock size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" />
                <input
                  type="password"
                  {...register("password", { required: "Введите пароль" })}
                  className="input pl-11"
                  placeholder="••••••••"
                  autoComplete="current-password"
                />
              </div>
              {errors.password && <p className="mt-1.5 text-xs font-medium text-danger-500">{errors.password.message}</p>}
            </div>

            <button type="submit" className="btn-primary w-full py-3 mt-2" disabled={loading}>
              {loading ? "Входим..." : "Войти"}
            </button>
          </form>

          <div className="mt-6 rounded-2xl bg-gray-50 px-4 py-3 text-center">
            <p className="text-xs font-medium text-gray-500">
              Демо-доступ:
            </p>
            <p className="mt-0.5 text-xs font-mono text-gray-700">
              admin@crm.local / Admin1234!
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
