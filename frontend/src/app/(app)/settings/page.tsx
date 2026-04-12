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
import { StravaConnect } from "@/components/settings/StravaConnect";
import { Suspense } from "react";

export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Настройки</h1>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
        {/* Column 1 */}
        <div className="space-y-6">
          <PlanBuilder />
          <GarminConnect />
          <Suspense fallback={null}>
            <StravaConnect />
          </Suspense>
        </div>

        {/* Column 2 */}
        <div>
          <SubscriptionBlock />
        </div>
      </div>
    </div>
  );
}
