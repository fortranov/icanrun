/**
 * Landing page — public entry point.
 * Redirects authenticated users to the dashboard.
 */
import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "ICanRun — Тренировки для триатлета",
};

export default function LandingPage() {
  return (
    <main className="min-h-screen bg-white">
      {/* Navigation */}
      <nav className="flex items-center justify-between px-6 py-4 border-b border-gray-100 max-w-7xl mx-auto">
        <div className="flex items-center gap-2">
          <span className="text-2xl font-bold text-blue-600">ICanRun</span>
        </div>
        <div className="flex items-center gap-4">
          <Link
            href="/login"
            className="text-gray-600 hover:text-gray-900 transition-colors"
          >
            Войти
          </Link>
          <Link
            href="/register"
            className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
          >
            Начать бесплатно
          </Link>
        </div>
      </nav>

      {/* Hero */}
      <section className="max-w-7xl mx-auto px-6 py-24 text-center">
        <h1 className="text-5xl font-bold text-gray-900 mb-6">
          Планируй тренировки.
          <br />
          <span className="text-blue-600">Достигай результатов.</span>
        </h1>
        <p className="text-xl text-gray-600 max-w-2xl mx-auto mb-10">
          Профессиональная платформа для планирования и анализа тренировок
          по бегу, плаванию, велосипеду и триатлону. Методология Joe Friel
          в вашем телефоне.
        </p>
        <div className="flex items-center justify-center gap-4">
          <Link
            href="/register"
            className="bg-blue-600 text-white px-8 py-3 rounded-lg text-lg font-medium hover:bg-blue-700 transition-colors"
          >
            Попробовать 30 дней бесплатно
          </Link>
          <Link
            href="#features"
            className="text-gray-600 hover:text-gray-900 px-8 py-3 rounded-lg text-lg border border-gray-200 hover:border-gray-300 transition-colors"
          >
            Узнать больше
          </Link>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="bg-gray-50 py-24">
        <div className="max-w-7xl mx-auto px-6">
          <h2 className="text-3xl font-bold text-center text-gray-900 mb-12">
            Всё что нужно триатлету
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {[
              {
                title: "Умный календарь",
                desc: "Drag-and-drop интерфейс для управления тренировками. Видите плановые и выполненные нагрузки в одном месте.",
              },
              {
                title: "Планы по Friel",
                desc: "Автоматическая генерация тренировочных планов на основе методологии Joe Friel с периодизацией 4-недельными циклами.",
              },
              {
                title: "Аналитика",
                desc: "Детальная статистика по видам спорта, объёмам нагрузок и выполнению планов в виде наглядных графиков.",
              },
              {
                title: "Garmin Connect",
                desc: "Автоматическая синхронизация тренировок из Garmin Connect. Никакого ручного ввода.",
              },
              {
                title: "Соревнования",
                desc: "Добавляйте целевые старты. Система автоматически строит подводку с правильным тейпером.",
              },
              {
                title: "5 видов спорта",
                desc: "Бег, плавание, велосипед, силовые тренировки и триатлон — всё в одном приложении.",
              },
            ].map((feature) => (
              <div
                key={feature.title}
                className="bg-white rounded-xl p-6 shadow-sm border border-gray-100"
              >
                <h3 className="text-lg font-semibold text-gray-900 mb-2">
                  {feature.title}
                </h3>
                <p className="text-gray-600">{feature.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="py-24">
        <div className="max-w-7xl mx-auto px-6">
          <h2 className="text-3xl font-bold text-center text-gray-900 mb-12">
            Тарифы
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-5xl mx-auto">
            {[
              {
                name: "Пробный",
                price: "Бесплатно",
                period: "30 дней",
                features: [
                  "Все функции без ограничений",
                  "Тренировочные планы",
                  "Интеграция с Garmin",
                  "Аналитика",
                ],
                cta: "Начать бесплатно",
                highlight: false,
              },
              {
                name: "Basic",
                price: "299 ₽",
                period: "в месяц",
                features: [
                  "Тренировки без ограничений",
                  "Интеграция с Garmin",
                  "Базовая аналитика",
                  "Без тренировочных планов",
                ],
                cta: "Выбрать Basic",
                highlight: false,
              },
              {
                name: "Pro",
                price: "599 ₽",
                period: "в месяц",
                features: [
                  "Все функции Basic",
                  "Тренировочные планы (Friel)",
                  "Расширенная аналитика",
                  "Приоритетная поддержка",
                ],
                cta: "Выбрать Pro",
                highlight: true,
              },
            ].map((plan) => (
              <div
                key={plan.name}
                className={`rounded-xl p-8 border ${
                  plan.highlight
                    ? "border-blue-500 bg-blue-50 shadow-lg"
                    : "border-gray-200 bg-white"
                }`}
              >
                <h3 className="text-xl font-bold text-gray-900">{plan.name}</h3>
                <div className="mt-4 mb-6">
                  <span className="text-3xl font-bold text-gray-900">
                    {plan.price}
                  </span>
                  <span className="text-gray-500 ml-2">{plan.period}</span>
                </div>
                <ul className="space-y-3 mb-8">
                  {plan.features.map((f) => (
                    <li key={f} className="flex items-center gap-2 text-gray-600">
                      <span className="text-green-500 font-bold">+</span>
                      {f}
                    </li>
                  ))}
                </ul>
                <Link
                  href="/register"
                  className={`block text-center py-2 px-4 rounded-lg font-medium transition-colors ${
                    plan.highlight
                      ? "bg-blue-600 text-white hover:bg-blue-700"
                      : "border border-gray-300 text-gray-700 hover:border-gray-400"
                  }`}
                >
                  {plan.cta}
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-900 text-gray-400 py-12">
        <div className="max-w-7xl mx-auto px-6 text-center">
          <p className="text-2xl font-bold text-white mb-2">ICanRun</p>
          <p className="mb-4">Платформа для тренировок триатлетов</p>
          <p className="text-sm">2026 ICanRun. Все права защищены.</p>
        </div>
      </footer>
    </main>
  );
}
