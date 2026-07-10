"use client";

import { FormEvent, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { authApi } from "@/lib/api";

function getErrorMessage(err: unknown): string {
  const detail = (err as { response?: { data?: { detail?: string } } })?.response
    ?.data?.detail;

  if (detail?.toLowerCase().includes("current password")) {
    return "Текущий пароль указан неверно";
  }

  return detail ?? "Не удалось изменить пароль";
}

export function PasswordChange() {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const { mutateAsync: changePassword, isPending } = useMutation({
    mutationFn: () => authApi.changePassword(currentPassword, newPassword),
    onSuccess: () => {
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setFormError(null);
      setSuccessMessage("Пароль успешно изменён");
    },
    onError: (err: unknown) => {
      setSuccessMessage(null);
      setFormError(getErrorMessage(err));
    },
  });

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);
    setSuccessMessage(null);

    if (newPassword.length < 8) {
      setFormError("Новый пароль должен содержать минимум 8 символов");
      return;
    }

    if (newPassword !== confirmPassword) {
      setFormError("Новый пароль и подтверждение не совпадают");
      return;
    }

    await changePassword();
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className="px-6 py-5 border-b border-gray-100">
        <h2 className="text-lg font-semibold text-gray-900">Пароль</h2>
        <p className="text-xs text-gray-500 mt-1">
          Измените пароль для входа в учётную запись ICanRun.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="px-6 py-5 space-y-4">
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">
            Текущий пароль
          </label>
          <input
            type="password"
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            autoComplete="current-password"
            required
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">
            Новый пароль
          </label>
          <input
            type="password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            autoComplete="new-password"
            minLength={8}
            maxLength={128}
            required
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
          <p className="text-xs text-gray-400 mt-1">Минимум 8 символов.</p>
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">
            Повторите новый пароль
          </label>
          <input
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            autoComplete="new-password"
            minLength={8}
            maxLength={128}
            required
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>

        {formError && (
          <div className="rounded-lg bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">
            {formError}
          </div>
        )}

        {successMessage && (
          <div className="rounded-lg bg-green-50 border border-green-200 px-3 py-2 text-sm text-green-700">
            {successMessage}
          </div>
        )}

        <button
          type="submit"
          disabled={isPending}
          className="w-full px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
        >
          {isPending ? "Сохраняем..." : "Изменить пароль"}
        </button>
      </form>
    </div>
  );
}
