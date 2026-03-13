/**
 * Landing page — public entry point.
 * Redirects authenticated users to the dashboard.
 */
import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "ICanRun — Тренировки для триатлета",
};

const features = [
  {
    title: "Умный календарь",
    desc: "Планируйте неделю за минуты: drag-and-drop, цветовые статусы и контроль загрузки в одном окне.",
    icon: "🗓️",
  },
  {
    title: "Планы по Joe Friel",
    desc: "Готовые сценарии периодизации и адаптация под ваш текущий уровень и ближайшие старты.",
    icon: "🎯",
  },
  {
    title: "Аналитика прогресса",
    desc: "Наглядные графики объёма, интенсивности и соблюдения плана, чтобы расти стабильно.",
    icon: "📈",
  },
  {
    title: "Garmin Connect",
    desc: "Автоматический импорт тренировок без ручного ввода и потери данных.",
    icon: "⌚",
  },
  {
    title: "Подготовка к стартам",
    desc: "Добавляйте соревнования и получайте персонализированный taper перед главной гонкой.",
    icon: "🏁",
  },
  {
    title: "5 спортивных дисциплин",
    desc: "Бег, плавание, велосипед, силовые и триатлон в единой системе.",
    icon: "🚴",
  },
];

const plans = [
  {
    name: "Пробный",
    price: "Бесплатно",
    period: "30 дней",
    features: [
      "Все функции без ограничений",
      "Тренировочные планы",
      "Интеграция с Garmin",
      "Полная аналитика",
    ],
    cta: "Начать бесплатно",
    highlight: false,
    label: "Лучший старт",
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
    label: "Для дисциплины",
  },
  {
    name: "Pro",
    price: "599 ₽",
    period: "в месяц",
    features: [
      "Все функции Basic",
      "Планы по Friel",
      "Расширенная аналитика",
      "Приоритетная поддержка",
    ],
    cta: "Выбрать Pro",
    highlight: true,
    label: "Выбор триатлетов",
  },
];

export default function LandingPage() {
  return (
    <main className="min-h-screen bg-slate-950 text-white overflow-hidden">
      <div className="relative isolate">
        <div className="pointer-events-none absolute inset-x-0 -top-32 h-[28rem] bg-[radial-gradient(circle_at_top,_rgba(59,130,246,0.45),_transparent_65%)]" />
        <div className="pointer-events-none absolute right-[-9rem] top-48 h-72 w-72 rounded-full bg-cyan-400/20 blur-3xl" />

        <nav className="max-w-7xl mx-auto px-4 sm:px-6 py-4 sm:py-5">
          <div className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur-md px-4 sm:px-6 py-3 flex items-center justify-between gap-3">
            <span className="text-2xl font-black tracking-tight text-blue-400">ICanRun</span>
            <div className="flex items-center gap-2 sm:gap-3">
              <Link
                href="/login"
                className="text-sm sm:text-base text-slate-200 hover:text-white px-3 py-2 rounded-lg transition-colors"
              >
                Войти
              </Link>
              <Link
                href="/register"
                className="text-sm sm:text-base bg-gradient-to-r from-blue-500 to-cyan-400 text-slate-950 font-semibold px-3 sm:px-5 py-2 rounded-xl hover:brightness-110 transition"
              >
                Старт
              </Link>
            </div>
          </div>
        </nav>

        <section className="max-w-7xl mx-auto px-4 sm:px-6 pt-8 sm:pt-14 pb-20 sm:pb-24">
          <div className="grid lg:grid-cols-2 gap-8 sm:gap-12 items-center">
            <div>
              <p className="inline-flex items-center rounded-full border border-cyan-300/30 bg-cyan-300/10 px-4 py-1.5 text-xs sm:text-sm text-cyan-100 mb-5">
                🚀 Тренируйся системно и без перегруза
              </p>
              <h1 className="text-4xl sm:text-5xl lg:text-6xl font-black leading-[1.05] tracking-tight mb-5">
                Планируй тренировки.
                <span className="block text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-cyan-300">
                  Достигай пика к старту.
                </span>
              </h1>
              <p className="text-base sm:text-xl text-slate-300 max-w-xl mb-8">
                Современная платформа для бега, плавания, велосипеда и триатлона.
                Получайте персональный план, анализируйте прогресс и двигайтесь к
                целям быстрее.
              </p>

              <div className="flex flex-col sm:flex-row gap-3 sm:gap-4">
                <Link
                  href="/register"
                  className="text-center bg-gradient-to-r from-blue-500 to-cyan-400 text-slate-950 px-6 py-3.5 rounded-xl text-base sm:text-lg font-bold hover:brightness-110 transition"
                >
                  Попробовать 30 дней бесплатно
                </Link>
                <Link
                  href="#features"
                  className="text-center text-slate-100 px-6 py-3.5 rounded-xl text-base sm:text-lg border border-white/20 bg-white/5 hover:bg-white/10 transition"
                >
                  Узнать больше
                </Link>
              </div>
            </div>

            <div className="rounded-3xl border border-white/10 bg-gradient-to-b from-white/10 to-white/5 p-5 sm:p-7 backdrop-blur-md shadow-2xl shadow-blue-900/30">
              <p className="text-slate-300 text-sm mb-5">Сегодняшний статус</p>
              <div className="grid grid-cols-2 gap-3 sm:gap-4 mb-4">
                {[
                  ["5", "тренировок / неделя"],
                  ["89%", "выполнение плана"],
                  ["+22%", "прирост объёма"],
                  ["42", "дня до старта"],
                ].map(([value, label]) => (
                  <div key={label} className="rounded-2xl bg-slate-900/80 border border-white/10 p-4">
                    <p className="text-2xl sm:text-3xl font-extrabold text-cyan-300">{value}</p>
                    <p className="text-xs sm:text-sm text-slate-400 mt-1">{label}</p>
                  </div>
                ))}
              </div>
              <div className="rounded-2xl bg-blue-500/20 border border-blue-300/30 p-4">
                <p className="text-sm text-blue-100">Рекомендация недели</p>
                <p className="text-base sm:text-lg font-semibold mt-1">
                  Добавить 1 восстановительную тренировку в плавании.
                </p>
              </div>
            </div>
          </div>
        </section>
      </div>

      <section id="features" className="py-16 sm:py-20 bg-white/[0.02] border-y border-white/10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <h2 className="text-3xl sm:text-4xl font-bold text-center mb-3">Всё, что нужно триатлету</h2>
          <p className="text-slate-300 text-center mb-10 sm:mb-12 max-w-2xl mx-auto">
            Насыщенный интерфейс, быстрые сценарии работы и глубокая аналитика в мобильном формате.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
            {features.map((feature) => (
              <article
                key={feature.title}
                className="rounded-2xl border border-white/10 bg-slate-900/60 p-5 sm:p-6 hover:border-cyan-300/40 transition"
              >
                <p className="text-2xl mb-3">{feature.icon}</p>
                <h3 className="text-lg font-semibold mb-2">{feature.title}</h3>
                <p className="text-slate-300 text-sm sm:text-base">{feature.desc}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section id="pricing" className="py-16 sm:py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <h2 className="text-3xl sm:text-4xl font-bold text-center mb-3">Тарифы</h2>
          <p className="text-slate-300 text-center mb-10 sm:mb-12">Начните бесплатно, переходите на нужный уровень в любой момент.</p>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-6 max-w-5xl mx-auto">
            {plans.map((plan) => (
              <div
                key={plan.name}
                className={`rounded-3xl p-6 sm:p-7 border ${
                  plan.highlight
                    ? "border-cyan-300/50 bg-gradient-to-b from-blue-500/30 to-cyan-400/15 shadow-2xl shadow-cyan-900/30"
                    : "border-white/10 bg-slate-900/70"
                }`}
              >
                <p className="text-xs uppercase tracking-wider text-cyan-200 mb-3">{plan.label}</p>
                <h3 className="text-2xl font-bold">{plan.name}</h3>
                <div className="mt-3 mb-5">
                  <span className="text-4xl font-black">{plan.price}</span>
                  <span className="text-slate-300 ml-2">{plan.period}</span>
                </div>
                <ul className="space-y-2.5 mb-7 text-sm sm:text-base">
                  {plan.features.map((f) => (
                    <li key={f} className="flex items-start gap-2 text-slate-200">
                      <span className="text-cyan-300 mt-0.5">✓</span>
                      <span>{f}</span>
                    </li>
                  ))}
                </ul>
                <Link
                  href="/register"
                  className={`block text-center py-3 rounded-xl font-semibold transition ${
                    plan.highlight
                      ? "bg-white text-slate-900 hover:bg-slate-100"
                      : "bg-white/10 hover:bg-white/20"
                  }`}
                >
                  {plan.cta}
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      <footer className="border-t border-white/10 py-10 sm:py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 text-center text-slate-400">
          <p className="text-2xl font-black text-white mb-2">ICanRun</p>
          <p className="mb-3">Платформа для тренировок триатлетов</p>
          <p className="text-sm">2026 ICanRun. Все права защищены.</p>
        </div>
      </footer>
    </main>
  );
}
