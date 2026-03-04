/**
 * Hook to access current user subscription and check feature permissions.
 */
"use client";

import { useAuthStore } from "@/stores/authStore";
import { canUseGarmin, canUsePlans } from "@/lib/utils";

export function useSubscription() {
  const subscription = useAuthStore((s) => s.subscription);

  const plan = subscription?.is_active ? subscription.plan : undefined;
  const isExpired = subscription
    ? !subscription.is_active ||
      (subscription.expires_at
        ? new Date(subscription.expires_at) < new Date()
        : false)
    : true;

  // Days remaining for trial
  let daysRemaining: number | null = null;
  if (subscription?.expires_at) {
    const ms = new Date(subscription.expires_at).getTime() - Date.now();
    daysRemaining = Math.max(0, Math.ceil(ms / (1000 * 60 * 60 * 24)));
  }

  return {
    subscription,
    plan,
    isExpired,
    daysRemaining,
    canUsePlans: canUsePlans(plan),
    canUseGarmin: canUseGarmin(plan),
    isTrial: plan === "trial",
    isBasic: plan === "basic",
    isPro: plan === "pro",
  };
}
