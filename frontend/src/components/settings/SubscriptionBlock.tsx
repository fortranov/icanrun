/**
 * SubscriptionBlock — shows current subscription plan and upgrade options.
 *
 * Displays:
 *  - Current plan badge (Trial/Basic/Pro)
 *  - Days remaining for Trial
 *  - Feature comparison table
 *  - Upgrade buttons (placeholder — YooKassa integration in next iteration)
 */
"use client";

import { cn } from "@/lib/utils";
import { useSubscription } from "@/hooks/useSubscription";

const PLAN_LABELS: Record<string, string> = {
  trial: "Пробный период",
  basic: "Базовый",
  pro:   "Pro",
};

const PLAN_COLORS: Record<string, string> = {
  trial: "bg-blue-100 text-blue-700 border-blue-200",
  basic: "bg-gray-100 text-gray-700 border-gray-200",
  pro:   "bg-amber-100 text-amber-700 border-amber-200",
};

interface FeatureRow {
  label: string;
  trial: boolean;
  basic: boolean;
  pro: boolean;
}

const FEATURES: FeatureRow[] = [
  { label: "Добавление тренировок",    trial: true,  basic: true,  pro: true  },
  { label: "Подключение Garmin",       trial: true,  basic: true,  pro: true  },
  { label: "Планы тренировок (Friel)", trial: true,  basic: false, pro: true  },
  { label: "Расширенная аналитика",    trial: true,  basic: true,  pro: true  },
  { label: "Приоритетная поддержка",   trial: false, basic: false, pro: true  },
];

function Check({ enabled }: { enabled: boolean }) {
  if (enabled) {
    return (
      <svg viewBox="0 0 20 20" className="w-5 h-5 text-green-500 mx-auto" fill="currentColor">
        <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" />
      </svg>
    );
  }
  return (
    <svg viewBox="0 0 20 20" className="w-5 h-5 text-gray-300 mx-auto" fill="currentColor">
      <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" />
    </svg>
  );
}

export function SubscriptionBlock() {
  const { plan, subscription, daysRemaining, isTrial, isExpired } = useSubscription();

  const activePlan = plan ?? "trial";
  const label = PLAN_LABELS[activePlan] ?? activePlan;
  const colorClass = PLAN_COLORS[activePlan] ?? PLAN_COLORS.trial;

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      {/* Header */}
      <div className="px-6 py-5 border-b border-gray-100">
        <h2 className="text-lg font-semibold text-gray-900 mb-3">Подписка</h2>

        <div className="flex items-center gap-3 flex-wrap">
          <span className={cn("px-3 py-1 rounded-full text-sm font-semibold border", colorClass)}>
            {label}
          </span>

          {isTrial && daysRemaining !== null && (
            <span className={cn(
              "text-sm",
              daysRemaining <= 7 ? "text-red-600 font-medium" : "text-gray-500"
            )}>
              {daysRemaining > 0
                ? `Осталось ${daysRemaining} ${pluralDays(daysRemaining)}`
                : "Истёк"}
            </span>
          )}

          {isExpired && (
            <span className="text-sm text-red-600 font-medium">
              Подписка истекла
            </span>
          )}
        </div>

        {subscription?.expires_at && (
          <p className="text-xs text-gray-400 mt-2">
            Действует до:{" "}
            {new Date(subscription.expires_at).toLocaleDateString("ru-RU", {
              day: "numeric",
              month: "long",
              year: "numeric",
            })}
          </p>
        )}
      </div>

      {/* Feature comparison table */}
      <div className="px-6 py-5">
        <p className="text-sm font-medium text-gray-700 mb-3">Возможности планов</p>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-xs text-gray-500">
                <th className="text-left py-2 pr-4 font-medium">Функция</th>
                <th className="text-center py-2 px-3 font-medium w-20">Пробный</th>
                <th className="text-center py-2 px-3 font-medium w-20">Базовый</th>
                <th className="text-center py-2 px-3 font-medium w-20">Pro</th>
              </tr>
            </thead>
            <tbody>
              {FEATURES.map((feature) => (
                <tr key={feature.label} className="border-t border-gray-50">
                  <td className="py-2 pr-4 text-gray-700">{feature.label}</td>
                  <td className="py-2 px-3"><Check enabled={feature.trial} /></td>
                  <td className="py-2 px-3"><Check enabled={feature.basic} /></td>
                  <td className="py-2 px-3"><Check enabled={feature.pro} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Upgrade buttons */}
      {activePlan !== "pro" && (
        <div className="px-6 py-4 bg-gray-50 border-t border-gray-100">
          <div className="flex gap-3 flex-wrap">
            {activePlan !== "basic" && (
              <button
                type="button"
                className="px-4 py-2 border border-gray-300 text-sm font-medium text-gray-700 rounded-lg hover:bg-white transition-colors"
                onClick={() => alert("Интеграция YooKassa — в разработке")}
              >
                Базовый — 299 ₽/мес
              </button>
            )}
            <button
              type="button"
              className="px-4 py-2 bg-amber-500 text-white text-sm font-medium rounded-lg hover:bg-amber-600 transition-colors"
              onClick={() => alert("Интеграция YooKassa — в разработке")}
            >
              Pro — 599 ₽/мес
            </button>
          </div>
          <p className="text-xs text-gray-400 mt-2">
            Оплата через YooKassa. Можно отменить в любой момент.
          </p>
        </div>
      )}
    </div>
  );
}

function pluralDays(n: number): string {
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod10 === 1 && mod100 !== 11) return "день";
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) return "дня";
  return "дней";
}
