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

/**
 * Возраст на сегодня по дате рождения (ISO-строка).
 * null, если дата неизвестна или некорректна.
 */
export function ageFromBirth(birthDate: string | null): number | null {
  if (!birthDate) {
    return null;
  }

  const birth = new Date(birthDate);
  if (Number.isNaN(birth.getTime())) {
    return null;
  }

  const today = new Date();
  let age = today.getFullYear() - birth.getFullYear();
  const monthDiff = today.getMonth() - birth.getMonth();
  if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birth.getDate())) {
    age -= 1;
  }
  return age;
}

/**
 * Цена приёма. Backend отдаёт numeric строкой (Decimal) — не теряем точность
 * и не показываем «120.00000000001» после умножений.
 */
export function formatPrice(value: string | null | undefined): string {
  if (!value) {
    return "—";
  }

  const amount = Number(value);
  if (Number.isNaN(amount)) {
    return value;
  }

  const text = Number.isInteger(amount) ? String(amount) : amount.toFixed(2);
  return `${text} р.`;
}
