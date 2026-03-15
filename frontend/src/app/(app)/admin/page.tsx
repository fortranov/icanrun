"use client";

/**
 * Admin page — accessible only to users with admin role.
 *
 * Sections:
 *   1. User Management — list all users, change role/subscription
 *   2. App Settings — Google OAuth toggle + full email/SMTP settings
 */
import { useState, useEffect, useRef } from "react";
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
  // Email confirmation settings
  email_confirmation_enabled: boolean;
  smtp_host: string;
  smtp_port: number;
  smtp_user: string;
  smtp_from_email: string;
  smtp_from_name: string;
  confirmation_token_hours: number;
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
// Toggle switch helper
// ---------------------------------------------------------------------------

function Toggle({
  checked,
  onChange,
  disabled,
}: {
  checked: boolean;
  onChange: () => void;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onChange}
      disabled={disabled}
      className={cn(
        "relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none disabled:opacity-50",
        checked ? "bg-blue-600" : "bg-gray-200"
      )}
    >
      <span
        className={cn(
          "inline-block h-4 w-4 transform rounded-full bg-white shadow-sm transition-transform",
          checked ? "translate-x-6" : "translate-x-1"
        )}
      />
    </button>
  );
}

// ---------------------------------------------------------------------------
// Input field helper
// ---------------------------------------------------------------------------

function SettingField({
  label,
  children,
  hint,
}: {
  label: string;
  children: React.ReactNode;
  hint?: string;
}) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
      {children}
      {hint && <p className="mt-1 text-xs text-gray-400">{hint}</p>}
    </div>
  );
}

const inputClass =
  "w-full border border-gray-200 rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white";

// ---------------------------------------------------------------------------
// App Settings Component
// ---------------------------------------------------------------------------

function AppSettingsBlock() {
  const queryClient = useQueryClient();
  const [settingsError, setSettingsError] = useState<string | null>(null);
  const [settingsSuccess, setSettingsSuccess] = useState(false);
  const [testEmailStatus, setTestEmailStatus] = useState<
    "idle" | "sending" | "ok" | "error"
  >("idle");

  // Local form state for editable fields
  const [form, setForm] = useState<Partial<AppSettings> & {
    smtp_password?: string;
    google_client_secret?: string;
  }>({});

  const { data: settings, isLoading } = useQuery<AppSettings>({
    queryKey: ["admin", "settings"],
    queryFn: async () => {
      const res = await adminApi.settings();
      return res.data as AppSettings;
    },
  });

  // Initialise form once when settings are first loaded
  const formInitialized = useRef(false);
  useEffect(() => {
    if (settings && !formInitialized.current) {
      formInitialized.current = true;
      setForm({
        google_oauth_enabled: settings.google_oauth_enabled,
        google_client_id: settings.google_client_id,
        google_client_secret: "",
        email_confirmation_enabled: settings.email_confirmation_enabled,
        smtp_host: settings.smtp_host,
        smtp_port: settings.smtp_port,
        smtp_user: settings.smtp_user,
        smtp_password: "",
        smtp_from_email: settings.smtp_from_email,
        smtp_from_name: settings.smtp_from_name,
        confirmation_token_hours: settings.confirmation_token_hours,
      });
    }
  }, [settings]);

  const { mutateAsync: saveSettings, isPending: isSaving } = useMutation({
    mutationFn: async (data: object) => {
      const res = await adminApi.updateSettings(data);
      return res.data as AppSettings;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "settings"] });
      setSettingsError(null);
      setSettingsSuccess(true);
      setTimeout(() => setSettingsSuccess(false), 3000);
      // Clear password fields after save
      setForm((prev) => ({ ...prev, smtp_password: "", google_client_secret: "" }));
    },
    onError: (err: unknown) => {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? "Ошибка при сохранении настроек";
      setSettingsError(msg);
    },
  });

  const handleSave = async () => {
    // Build payload — only send smtp_password / google_client_secret if non-empty
    const payload: Record<string, unknown> = {
      google_oauth_enabled: form.google_oauth_enabled,
      google_client_id: form.google_client_id ?? "",
      email_confirmation_enabled: form.email_confirmation_enabled,
      smtp_host: form.smtp_host ?? "",
      smtp_port: form.smtp_port ?? 587,
      smtp_user: form.smtp_user ?? "",
      smtp_from_email: form.smtp_from_email ?? "",
      smtp_from_name: form.smtp_from_name ?? "ICanRun",
      confirmation_token_hours: form.confirmation_token_hours ?? 24,
    };
    if (form.smtp_password) payload.smtp_password = form.smtp_password;
    if (form.google_client_secret) payload.google_client_secret = form.google_client_secret;
    await saveSettings(payload);
  };

  const handleTestEmail = async () => {
    setTestEmailStatus("sending");
    try {
      await adminApi.testEmail();
      setTestEmailStatus("ok");
      setTimeout(() => setTestEmailStatus("idle"), 4000);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? "Ошибка отправки";
      setSettingsError(msg);
      setTestEmailStatus("error");
      setTimeout(() => setTestEmailStatus("idle"), 4000);
    }
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

      <div className="px-6 py-5 space-y-6">
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

        {/* ---------------------------------------------------------------- */}
        {/* Google OAuth section                                              */}
        {/* ---------------------------------------------------------------- */}
        <div>
          <h3 className="text-sm font-semibold text-gray-700 mb-3">Google OAuth</h3>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-800">Включить Google OAuth</p>
                <p className="text-xs text-gray-500 mt-0.5">
                  Разрешить вход через Google аккаунт
                </p>
              </div>
              <Toggle
                checked={form.google_oauth_enabled ?? settings?.google_oauth_enabled ?? false}
                onChange={() =>
                  setForm((prev) => ({
                    ...prev,
                    google_oauth_enabled: !(prev.google_oauth_enabled ?? settings?.google_oauth_enabled),
                  }))
                }
                disabled={isSaving}
              />
            </div>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <SettingField label="Google Client ID">
                <input
                  type="text"
                  className={inputClass}
                  value={form.google_client_id ?? ""}
                  onChange={(e) => setForm((prev) => ({ ...prev, google_client_id: e.target.value }))}
                  placeholder="xxx.apps.googleusercontent.com"
                />
              </SettingField>
              <SettingField label="Google Client Secret" hint="Оставьте пустым, чтобы не менять">
                <input
                  type="password"
                  className={inputClass}
                  value={form.google_client_secret ?? ""}
                  onChange={(e) => setForm((prev) => ({ ...prev, google_client_secret: e.target.value }))}
                  placeholder="Новый секрет (необязательно)"
                />
              </SettingField>
            </div>
          </div>
        </div>

        <hr className="border-gray-100" />

        {/* ---------------------------------------------------------------- */}
        {/* Email confirmation section                                        */}
        {/* ---------------------------------------------------------------- */}
        <div>
          <h3 className="text-sm font-semibold text-gray-700 mb-3">
            Подтверждение email при регистрации
          </h3>
          <div className="space-y-4">
            {/* Toggle */}
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-800">
                  Требовать подтверждение email
                </p>
                <p className="text-xs text-gray-500 mt-0.5">
                  Новые пользователи получат письмо со ссылкой активации
                </p>
              </div>
              <Toggle
                checked={
                  form.email_confirmation_enabled ??
                  settings?.email_confirmation_enabled ??
                  false
                }
                onChange={() =>
                  setForm((prev) => ({
                    ...prev,
                    email_confirmation_enabled: !(
                      prev.email_confirmation_enabled ??
                      settings?.email_confirmation_enabled
                    ),
                  }))
                }
                disabled={isSaving}
              />
            </div>

            {/* Token TTL */}
            <SettingField
              label="Срок действия ссылки (часов)"
              hint="Сколько часов действительна ссылка подтверждения"
            >
              <input
                type="number"
                min={1}
                max={168}
                className={inputClass + " w-32"}
                value={form.confirmation_token_hours ?? 24}
                onChange={(e) =>
                  setForm((prev) => ({
                    ...prev,
                    confirmation_token_hours: parseInt(e.target.value, 10) || 24,
                  }))
                }
              />
            </SettingField>

            {/* SMTP settings */}
            <div className="rounded-lg border border-gray-100 bg-gray-50 p-4 space-y-4">
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                Настройки SMTP
              </p>

              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <SettingField label="SMTP хост">
                  <input
                    type="text"
                    className={inputClass}
                    value={form.smtp_host ?? ""}
                    onChange={(e) => setForm((prev) => ({ ...prev, smtp_host: e.target.value }))}
                    placeholder="smtp.gmail.com"
                  />
                </SettingField>
                <SettingField label="SMTP порт">
                  <input
                    type="number"
                    min={1}
                    max={65535}
                    className={inputClass}
                    value={form.smtp_port ?? 587}
                    onChange={(e) =>
                      setForm((prev) => ({
                        ...prev,
                        smtp_port: parseInt(e.target.value, 10) || 587,
                      }))
                    }
                    placeholder="587"
                  />
                </SettingField>
              </div>

              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <SettingField label="SMTP логин">
                  <input
                    type="text"
                    className={inputClass}
                    value={form.smtp_user ?? ""}
                    onChange={(e) => setForm((prev) => ({ ...prev, smtp_user: e.target.value }))}
                    placeholder="user@gmail.com"
                  />
                </SettingField>
                <SettingField label="SMTP пароль" hint="Оставьте пустым, чтобы не менять">
                  <input
                    type="password"
                    className={inputClass}
                    value={form.smtp_password ?? ""}
                    onChange={(e) => setForm((prev) => ({ ...prev, smtp_password: e.target.value }))}
                    placeholder="Новый пароль (необязательно)"
                  />
                </SettingField>
              </div>

              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <SettingField label="Email отправителя">
                  <input
                    type="email"
                    className={inputClass}
                    value={form.smtp_from_email ?? ""}
                    onChange={(e) => setForm((prev) => ({ ...prev, smtp_from_email: e.target.value }))}
                    placeholder="noreply@icanrun.app"
                  />
                </SettingField>
                <SettingField label="Имя отправителя">
                  <input
                    type="text"
                    className={inputClass}
                    value={form.smtp_from_name ?? "ICanRun"}
                    onChange={(e) => setForm((prev) => ({ ...prev, smtp_from_name: e.target.value }))}
                    placeholder="ICanRun"
                  />
                </SettingField>
              </div>
            </div>
          </div>
        </div>

        {/* ---------------------------------------------------------------- */}
        {/* Action buttons                                                    */}
        {/* ---------------------------------------------------------------- */}
        <div className="flex flex-wrap gap-3 pt-2">
          <button
            type="button"
            onClick={handleSave}
            disabled={isSaving}
            className={cn(
              "px-5 py-2 rounded-lg text-sm font-medium transition-colors",
              "bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
            )}
          >
            {isSaving ? "Сохранение..." : "Сохранить настройки"}
          </button>

          <button
            type="button"
            onClick={handleTestEmail}
            disabled={testEmailStatus === "sending" || isSaving}
            className={cn(
              "px-5 py-2 rounded-lg text-sm font-medium transition-colors border",
              testEmailStatus === "ok"
                ? "border-green-400 text-green-700 bg-green-50"
                : testEmailStatus === "error"
                ? "border-red-400 text-red-700 bg-red-50"
                : "border-gray-200 text-gray-600 hover:bg-gray-50 disabled:opacity-50"
            )}
          >
            {testEmailStatus === "sending"
              ? "Отправка..."
              : testEmailStatus === "ok"
              ? "Письмо отправлено"
              : testEmailStatus === "error"
              ? "Ошибка отправки"
              : "Проверить подключение"}
          </button>
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
