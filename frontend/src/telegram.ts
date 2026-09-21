/**
 * Типизированный доступ к Telegram WebApp.
 *
 * SDK Telegram инжектит window.Telegram.WebApp в Mini App — отдельная
 * npm-зависимость не нужна, а типы держим локально, чтобы контролировать
 * ровно то, что используем.
 */

export interface TelegramWebAppUser {
  id: number;
  first_name?: string;
  last_name?: string;
  username?: string;
  language_code?: string;
}

export interface TelegramWebApp {
  initData: string;
  initDataUnsafe?: { user?: TelegramWebAppUser };
  colorScheme?: "light" | "dark";
  ready(): void;
  expand(): void;
  onEvent(event: string, handler: () => void): void;
  offEvent(event: string, handler: () => void): void;
  HapticFeedback?: { impactOccurred(style: "light" | "medium" | "heavy"): void };
}

declare global {
  interface Window {
    Telegram?: { WebApp?: TelegramWebApp };
  }
}

export function getTelegramWebApp(): TelegramWebApp | null {
  return window.Telegram?.WebApp ?? null;
}

export function getInitData(): string {
  return getTelegramWebApp()?.initData ?? "";
}

/**
 * Ждёт появления window.Telegram.
 *
 * Скрипт telegram-web-app.js грузится отдельным тегом, и на части клиентов
 * объект появляется чуть позже нашего бандла — без ожидания получаем
 * пустую initData и ложное «откройте через Telegram».
 */
export async function waitForTelegramWebApp(timeoutMs = 3000): Promise<boolean> {
  if (getTelegramWebApp()) {
    return true;
  }

  const startedAt = Date.now();
  while (Date.now() - startedAt < timeoutMs) {
    await new Promise((resolve) => setTimeout(resolve, 100));
    if (getTelegramWebApp()) {
      return true;
    }
  }
  return false;
}

export function getTelegramLanguage(): string | undefined {
  return getTelegramWebApp()?.initDataUnsafe?.user?.language_code;
}

/** Цветовая схема Telegram (светлая/тёмная тема клиента). */
export function currentColorScheme(): "light" | "dark" {
  const scheme = getTelegramWebApp()?.colorScheme;
  if (scheme === "dark") {
    return "dark";
  }
  if (scheme === "light") {
    return "light";
  }
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

/** Разворачивает Mini App на весь экран и сообщает Telegram, что UI готов. */
export function initTelegramUi(): void {
  const app = getTelegramWebApp();
  if (!app) {
    return;
  }
  app.ready();
  app.expand();
}

export function hapticImpact(): void {
  getTelegramWebApp()?.HapticFeedback?.impactOccurred("light");
}
