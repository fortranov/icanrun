/**
 * Top navigation menu.
 * Shows main nav links, admin link (if admin), user name, and logout button.
 */
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { useAuthStore } from "@/stores/authStore";
import { authApi } from "@/lib/api";
import { cn } from "@/lib/utils";

const NAV_LINKS = [
  { href: "/dashboard", label: "Главная" },
  { href: "/results", label: "Результаты" },
  { href: "/settings", label: "Настройки" },
];

export function TopMenu() {
  const pathname = usePathname();
  const { user, logout } = useAuthStore();
  const [menuOpen, setMenuOpen] = useState(false);

  const handleLogout = async () => {
    try {
      await authApi.logout();
    } catch {
      // Ignore logout errors — clear local state regardless
    }
    logout();
  };

  return (
    <header className="bg-white border-b border-gray-200 sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 flex items-center justify-between h-14">
        {/* Logo + main nav */}
        <div className="flex items-center gap-6">
          <Link href="/dashboard" className="text-xl font-bold text-blue-600">
            ICanRun
          </Link>
          {/* Desktop nav */}
          <nav className="hidden md:flex items-center gap-1">
            {NAV_LINKS.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className={cn(
                  "px-3 py-1.5 rounded-md text-sm font-medium transition-colors",
                  pathname.startsWith(link.href)
                    ? "bg-blue-50 text-blue-700"
                    : "text-gray-600 hover:text-gray-900 hover:bg-gray-50"
                )}
              >
                {link.label}
              </Link>
            ))}
          </nav>
        </div>

        {/* Right side */}
        <div className="flex items-center gap-3">
          {/* Admin link */}
          {user?.role === "admin" && (
            <Link
              href="/admin"
              className={cn(
                "hidden md:block px-3 py-1.5 rounded-md text-sm font-medium transition-colors",
                pathname.startsWith("/admin")
                  ? "bg-blue-50 text-blue-700"
                  : "text-gray-600 hover:text-gray-900 hover:bg-gray-50"
              )}
            >
              Администрирование
            </Link>
          )}

          {/* User name */}
          {user && (
            <span className="hidden md:block text-sm text-gray-700">
              {user.name}
            </span>
          )}

          {/* Logout button */}
          <button
            onClick={handleLogout}
            className="hidden md:block text-sm text-gray-500 hover:text-red-600 transition-colors"
          >
            Выйти
          </button>

          {/* Mobile hamburger */}
          <button
            className="md:hidden p-1.5 rounded-md text-gray-600 hover:bg-gray-100"
            onClick={() => setMenuOpen(!menuOpen)}
            aria-label="Меню"
          >
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              {menuOpen ? (
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              ) : (
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 6h16M4 12h16M4 18h16"
                />
              )}
            </svg>
          </button>
        </div>
      </div>

      {/* Mobile menu dropdown */}
      {menuOpen && (
        <div className="md:hidden border-t border-gray-100 bg-white px-4 py-3 space-y-1">
          {NAV_LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              onClick={() => setMenuOpen(false)}
              className={cn(
                "block px-3 py-2 rounded-md text-sm font-medium transition-colors",
                pathname.startsWith(link.href)
                  ? "bg-blue-50 text-blue-700"
                  : "text-gray-600 hover:bg-gray-50"
              )}
            >
              {link.label}
            </Link>
          ))}
          {user?.role === "admin" && (
            <Link
              href="/admin"
              onClick={() => setMenuOpen(false)}
              className="block px-3 py-2 rounded-md text-sm font-medium text-gray-600 hover:bg-gray-50"
            >
              Администрирование
            </Link>
          )}
          <div className="pt-2 border-t border-gray-100 mt-2">
            <span className="block px-3 py-1 text-sm text-gray-500">
              {user?.name}
            </span>
            <button
              onClick={handleLogout}
              className="block w-full text-left px-3 py-2 rounded-md text-sm text-red-600 hover:bg-red-50"
            >
              Выйти
            </button>
          </div>
        </div>
      )}
    </header>
  );
}
