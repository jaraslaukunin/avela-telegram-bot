/** Форматирование дат для Mini App (в часовом поясе филиала). */

export function formatDateTime(iso: string, timeZone?: string): string {
  const date = new Date(iso);
  try {
    return date.toLocaleString("ru-RU", {
      timeZone,
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return date.toLocaleString("ru-RU");
  }
}

export function formatDate(iso: string, timeZone?: string): string {
  const date = new Date(iso);
  try {
    return date.toLocaleDateString("ru-RU", { timeZone, day: "2-digit", month: "long" });
  } catch {
    return date.toLocaleDateString("ru-RU");
  }
}

export function formatTime(iso: string, timeZone?: string): string {
  const date = new Date(iso);
  try {
    return date.toLocaleTimeString("ru-RU", { timeZone, hour: "2-digit", minute: "2-digit" });
  } catch {
    return date.toLocaleTimeString("ru-RU");
  }
}

/** Доступна ли самостоятельная отмена (до дедлайна в таймзоне филиала). */
export function isCancellable(cancellableUntil: string, now: Date = new Date()): boolean {
  return now.getTime() < new Date(cancellableUntil).getTime();
}
