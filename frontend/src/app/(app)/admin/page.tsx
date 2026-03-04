"use client";

/**
 * Admin page — accessible only to users with admin role.
 *
 * Sections:
 *   1. User Management — list all users, change role/subscription
 *   2. App Settings — toggle Google OAuth enabled/disabled
 */
import { useState } from "react";
import { useAuthStore } from "@/stores/authStore";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { adminApi } from "@/lib/api";
import { cn, formatDate } from "@/lib/utils";
import type { User, Subscription, SubscriptionPlan, UserRole } from "@/types";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface AdminUser extends User {
  subscription?: Subscription | null;
}

interface AppSettings {
  google_oauth_enabled: boolean;
  google_client_id: string;
  google_client_secret: string;
  maintenance_mode: boolean;
  registration_open: boolean;
}

// ---------------------------------------------------------------------------
// Plan badge
// ---------------------------------------------------------------------------

const PLAN_COLORS: Record<string, string> = {
  trial: "bg-blue-100 text-blue-700",
  basic: "bg-gray-100 text-gray-700",
  pro:   "bg-amber-100 text-amber-700",
};

const PLAN_LABELS: Record<string, string> = {
  trial: "Trial",
  basic: "Basic",
  pro:   "Pro",
};

const ROLE_COLORS: Record<string, string> = {
  admin: "bg-red-100 text-red-700",
  user:  "bg-gray-100 text-gray-600",
};

// ---------------------------------------------------------------------------
// User Management Component
// ---------------------------------------------------------------------------

function UserManagement() {
  const queryClient = useQueryClient();
  const [editUserId, setEditUserId] = useState<number | null>(null);
  const [editRole, setEditRole] = useState<UserRole>("user");
  const [editPlan, setEditPlan] = useState<SubscriptionPlan | "">("");
  const [actionError, setActionError] = useState<string | null>(null);

  const { data: users, isLoading } = useQuery<AdminUser[]>({
    queryKey: ["admin", "users"],
    queryFn: async () => {
      const res = await adminApi.users();
      return res.data as AdminUser[];
    },
  });

  const { mutateAsync: updateUser, isPending: isUpdating } = useMutation({
    mutationFn: async ({ id, data }: { id: number; data: object }) => {
      const res = await adminApi.updateUser(id, data);
      return res.data as AdminUser;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
      setEditUserId(null);
      setActionError(null);
    },
    onError: (err: unknown) => {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? "Ошибка при обновлении пользователя";
      setActionError(msg);
    },
  });

  const startEdit = (user: AdminUser) => {
    setEditUserId(user.id);
    setEditRole(user.role);
    setEditPlan(user.subscription?.plan ?? "");
    setActionError(null);
  };

  const handleSave = async (userId: number) => {
    const payload: Record<string, unknown> = { role: editRole };
    if (editPlan) payload.subscription_plan = editPlan;
    await updateUser({ id: userId, data: payload });
  };

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-2">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-12 bg-gray-100 rounded" />
        ))}
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className="px-6 py-5 border-b border-gray-100">
        <h2 className="text-lg font-semibold text-gray-900">
          Пользователи
        </h2>
        <p className="text-sm text-gray-500 mt-0.5">
          Всего: {users?.length ?? 0}
        </p>
      </div>

      {actionError && (
        <div className="mx-6 mt-4 rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
          {actionError}
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-100 text-xs text-gray-500 uppercase tracking-wide">
              <th className="text-left px-6 py-3 font-medium">Пользователь</th>
              <th className="text-left px-6 py-3 font-medium">Роль</th>
              <th className="text-left px-6 py-3 font-medium">Подписка</th>
              <th className="text-left px-6 py-3 font-medium">Зарегистрирован</th>
              <th className="text-right px-6 py-3 font-medium">Действия</th>
            </tr>
          </thead>
          <tbody>
            {(users ?? []).map((user) => (
              <tr key={user.id} className="border-b border-gray-50 hover:bg-gray-50/50">
                <td className="px-6 py-3">
                  <div>
                    <p className="font-medium text-gray-900">{user.name}</p>
                    <p className="text-xs text-gray-400">{user.email}</p>
                  </div>
                </td>

                <td className="px-6 py-3">
                  {editUserId === user.id ? (
                    <select
                      value={editRole}
                      onChange={(e) => setEditRole(e.target.value as UserRole)}
                      className="text-xs border border-gray-300 rounded px-2 py-1 outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="user">User</option>
                      <option value="admin">Admin</option>
                    </select>
                  ) : (
                    <span className={cn("px-2 py-0.5 rounded text-xs font-medium", ROLE_COLORS[user.role])}>
                      {user.role}
                    </span>
                  )}
                </td>

                <td className="px-6 py-3">
                  {editUserId === user.id ? (
                    <select
                      value={editPlan}
                      onChange={(e) => setEditPlan(e.target.value as SubscriptionPlan)}
                      className="text-xs border border-gray-300 rounded px-2 py-1 outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="">-- не менять --</option>
                      <option value="trial">Trial</option>
                      <option value="basic">Basic</option>
                      <option value="pro">Pro</option>
                    </select>
                  ) : user.subscription ? (
                    <span className={cn("px-2 py-0.5 rounded text-xs font-medium", PLAN_COLORS[user.subscription.plan])}>
                      {PLAN_LABELS[user.subscription.plan]}
                    </span>
                  ) : (
                    <span className="text-gray-400 text-xs">Нет</span>
                  )}
                </td>

                <td className="px-6 py-3 text-gray-500 text-xs">
                  {formatDate(user.created_at.split("T")[0])}
                </td>

                <td className="px-6 py-3 text-right">
                  {editUserId === user.id ? (
                    <div className="flex gap-2 justify-end">
                      <button
                        type="button"
                        onClick={() => handleSave(user.id)}
                        disabled={isUpdating}
                        className="px-3 py-1 bg-blue-600 text-white text-xs font-medium rounded hover:bg-blue-700 disabled:opacity-50 transition-colors"
                      >
                        {isUpdating ? "..." : "Сохранить"}
                      </button>
                      <button
                        type="button"
                        onClick={() => setEditUserId(null)}
                        className="px-3 py-1 border border-gray-200 text-gray-600 text-xs rounded hover:bg-gray-100 transition-colors"
                      >
                        Отмена
                      </button>
                    </div>
                  ) : (
                    <button
                      type="button"
                      onClick={() => startEdit(user)}
                      className="px-3 py-1 border border-gray-200 text-gray-600 text-xs rounded hover:bg-gray-100 transition-colors"
                    >
                      Изменить
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// App Settings Component
// ---------------------------------------------------------------------------

function AppSettingsBlock() {
  const queryClient = useQueryClient();
  const [settingsError, setSettingsError] = useState<string | null>(null);
  const [settingsSuccess, setSettingsSuccess] = useState(false);

  const { data: settings, isLoading } = useQuery<AppSettings>({
    queryKey: ["admin", "settings"],
    queryFn: async () => {
      const res = await adminApi.settings();
      return res.data as AppSettings;
    },
  });

  const { mutateAsync: saveSettings, isPending: isSaving } = useMutation({
    mutationFn: async (data: Partial<AppSettings>) => {
      const res = await adminApi.updateSettings(data);
      return res.data as AppSettings;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "settings"] });
      setSettingsError(null);
      setSettingsSuccess(true);
      setTimeout(() => setSettingsSuccess(false), 3000);
    },
    onError: (err: unknown) => {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? "Ошибка при сохранении настроек";
      setSettingsError(msg);
    },
  });

  const handleToggleGoogleAuth = async () => {
    if (!settings) return;
    await saveSettings({
      google_oauth_enabled: !settings.google_oauth_enabled,
    });
  };

  if (isLoading) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-6 animate-pulse">
        <div className="h-4 bg-gray-100 rounded w-1/3 mb-4" />
        <div className="h-8 bg-gray-100 rounded" />
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className="px-6 py-5 border-b border-gray-100">
        <h2 className="text-lg font-semibold text-gray-900">
          Настройки приложения
        </h2>
      </div>

      <div className="px-6 py-5 space-y-4">
        {settingsError && (
          <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
            {settingsError}
          </div>
        )}
        {settingsSuccess && (
          <div className="rounded-lg bg-green-50 border border-green-200 px-4 py-3 text-sm text-green-700">
            Настройки сохранены
          </div>
        )}

        {/* Google OAuth toggle */}
        <div className="flex items-center justify-between py-3 border-b border-gray-100">
          <div>
            <p className="text-sm font-medium text-gray-800">Google OAuth</p>
            <p className="text-xs text-gray-500 mt-0.5">
              Разрешить вход через Google аккаунт
            </p>
          </div>
          <button
            type="button"
            onClick={handleToggleGoogleAuth}
            disabled={isSaving}
            className={cn(
              "relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none disabled:opacity-50",
              settings?.google_oauth_enabled ? "bg-blue-600" : "bg-gray-200"
            )}
          >
            <span
              className={cn(
                "inline-block h-4 w-4 transform rounded-full bg-white shadow-sm transition-transform",
                settings?.google_oauth_enabled ? "translate-x-6" : "translate-x-1"
              )}
            />
          </button>
        </div>

        {/* Maintenance mode info */}
        <div className="flex items-center justify-between py-3">
          <div>
            <p className="text-sm font-medium text-gray-800">Режим обслуживания</p>
            <p className="text-xs text-gray-500 mt-0.5">
              Отключает регистрацию и показывает заглушку новым пользователям
            </p>
          </div>
          <span className="text-xs text-gray-400 bg-gray-100 px-2 py-1 rounded">
            В разработке
          </span>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Admin Page
// ---------------------------------------------------------------------------

export default function AdminPage() {
  const user = useAuthStore((s) => s.user);
  const router = useRouter();

  // Redirect non-admins
  if (user && user.role !== "admin") {
    router.replace("/dashboard");
    return null;
  }

  return (
    <div className="space-y-6 max-w-5xl">
      <h1 className="text-2xl font-bold text-gray-900">Администрирование</h1>

      <UserManagement />
      <AppSettingsBlock />
    </div>
  );
}
