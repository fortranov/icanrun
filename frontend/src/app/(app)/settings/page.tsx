/**
 * Settings page.
 *
 * Sections:
 *  1. Subscription Block — current plan, days remaining, upgrade options
 *  2. Training Plan Builder — Friel periodization plan generator
 *  3. Garmin Integration — connect/sync Garmin account
 */
"use client";

import { SubscriptionBlock } from "@/components/settings/SubscriptionBlock";
import { PlanBuilder } from "@/components/settings/PlanBuilder";
import { GarminConnect } from "@/components/settings/GarminConnect";

export default function SettingsPage() {
  return (
    <div className="max-w-2xl space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Настройки</h1>

      <SubscriptionBlock />
      <PlanBuilder />
      <GarminConnect />
    </div>
  );
}
