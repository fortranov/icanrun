/**
 * Protected app layout — wraps all authenticated pages.
 * Includes top navigation and auth guard.
 */
"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/stores/authStore";
import { TopMenu } from "@/components/layout/TopMenu";
import { getAccessToken, getRefreshToken } from "@/lib/api";
import { useCurrentUser } from "@/hooks/useAuth";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { hasHydrated, isAuthenticated } = useAuthStore();
  const router = useRouter();
  const currentUserQuery = useCurrentUser();
  const hasStoredSession =
    typeof window !== "undefined" && (!!getAccessToken() || !!getRefreshToken());
  const isCheckingSession =
    !hasHydrated || (hasStoredSession && currentUserQuery.isPending);

  useEffect(() => {
    if (!hasHydrated || isCheckingSession) return;
    if (!isAuthenticated && !hasStoredSession) {
      router.replace("/login");
    }
  }, [hasHydrated, hasStoredSession, isAuthenticated, isCheckingSession, router]);

  if (isCheckingSession || (!isAuthenticated && hasStoredSession)) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-gray-500">Загрузка...</div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <TopMenu />
      <main className="max-w-7xl mx-auto px-4 py-6">{children}</main>
    </div>
  );
}
