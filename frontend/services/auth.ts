import { apiClient } from "@/lib/api-client";
import Cookies from "js-cookie";
import type { LoginResponse, User } from "@/types/api";

export const authService = {
  async login(email: string, password: string): Promise<LoginResponse> {
    const { data } = await apiClient.post<LoginResponse>("/auth/login", { email, password });
    Cookies.set("access_token", data.access_token, { expires: 1 });
    Cookies.set("refresh_token", data.refresh_token, { expires: 7 });
    return data;
  },

  logout() {
    Cookies.remove("access_token");
    Cookies.remove("refresh_token");
    window.location.href = "/login";
  },

  async getMe(): Promise<User> {
    const { data } = await apiClient.get<User>("/users/me");
    return data;
  },

  isAuthenticated(): boolean {
    return !!Cookies.get("access_token");
  },
};
