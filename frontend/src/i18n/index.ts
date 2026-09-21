/**
 * Мини-i18n без внешних зависимостей: ru, en, be-Latn (лацінка).
 * Набор ключей обязателен для всех языков — это проверяет тест.
 */

export const locales = ["ru", "en", "be-Latn"] as const;
export type Locale = (typeof locales)[number];
export type Dictionary = Record<string, string>;

const ru: Dictionary = {
  "app.title": "Avela",
  "app.tagline": "Запись к врачу",
  "home.book": "Записаться",
  "home.myAppointments": "Мои записи",
  "home.profile": "Профиль",
  "booking.title": "Запись на приём",
  "booking.network": "Выберите клинику",
  "booking.branch": "Выберите филиал",
  "booking.service": "Что вас беспокоит? Выберите услугу",
  "booking.doctor": "Выберите врача",
  "booking.anyDoctor": "Любой свободный врач",
  "booking.slot": "Свободное время",
  "booking.noSlots": "Свободных слотов нет — попробуйте другого врача или дату",
  "booking.confirm": "Подтвердить запись",
  "booking.success": "Вы записаны! Уведомление придёт в чат с ботом",
  "appointments.title": "Мои записи",
  "appointments.empty": "Записей пока нет",
  "appointments.cancel": "Отменить",
  "appointments.reschedule": "Перенести",
  "appointments.cancelled": "Запись отменена",
  "appointments.deadlinePassed": "Отмена недоступна: до приёма меньше 2 часов",
  "appointments.startsAt": "Приём",
  "profile.title": "Профиль",
  "profile.name": "Имя",
  "profile.phone": "Телефон",
  "profile.deleteAccount": "Удалить аккаунт и данные",
  "profile.deleteWarning":
    "Активные записи будут отменены, персональные данные — удалены. Действие необратимо.",
  "profile.deleted": "Данные удалены",
  "common.loading": "Загрузка…",
  "common.error": "Что-то пошло не так",
  "common.retry": "Повторить",
  "common.back": "Назад",
  "common.cancel": "Отмена",
  "common.confirm": "Да, подтверждаю",
};

const en: Dictionary = {
  "app.title": "Avela",
  "app.tagline": "Book a doctor's appointment",
  "home.book": "Book",
  "home.myAppointments": "My appointments",
  "home.profile": "Profile",
  "booking.title": "Book an appointment",
  "booking.network": "Choose a clinic",
  "booking.branch": "Choose a branch",
  "booking.service": "What do you need? Choose a service",
  "booking.doctor": "Choose a doctor",
  "booking.anyDoctor": "Any available doctor",
  "booking.slot": "Available time",
  "booking.noSlots": "No free slots — try another doctor or date",
  "booking.confirm": "Confirm booking",
  "booking.success": "You are booked! A notification will arrive in the bot chat",
  "appointments.title": "My appointments",
  "appointments.empty": "No appointments yet",
  "appointments.cancel": "Cancel",
  "appointments.reschedule": "Reschedule",
  "appointments.cancelled": "Appointment cancelled",
  "appointments.deadlinePassed": "Cancellation is not available: less than 2 hours left",
  "appointments.startsAt": "Appointment",
  "profile.title": "Profile",
  "profile.name": "Name",
  "profile.phone": "Phone",
  "profile.deleteAccount": "Delete account and data",
  "profile.deleteWarning":
    "Active appointments will be cancelled and personal data deleted. This cannot be undone.",
  "profile.deleted": "Data deleted",
  "common.loading": "Loading…",
  "common.error": "Something went wrong",
  "common.retry": "Retry",
  "common.back": "Back",
  "common.cancel": "Cancel",
  "common.confirm": "Yes, confirm",
};

const beLatn: Dictionary = {
  "app.title": "Avela",
  "app.tagline": "Zapis da ŭrača",
  "home.book": "Zapisacca",
  "home.myAppointments": "Maje zapisy",
  "home.profile": "Profil",
  "booking.title": "Zapis na pryjom",
  "booking.network": "Abarocie kliniku",
  "booking.branch": "Abarocie filijal",
  "booking.service": "Što vas turbuje? Abarocie pasluhu",
  "booking.doctor": "Abarocie ŭrača",
  "booking.anyDoctor": "Luby volny ŭrač",
  "booking.slot": "Volny čas",
  "booking.noSlots": "Volnych slotaŭ niama — pasprabujcie inšaha ŭrača ci datu",
  "booking.confirm": "Padcvierdzić zapis",
  "booking.success": "Vy zapisany! Pavierka pryjdzie ŭ čat z botam",
  "appointments.title": "Maje zapisy",
  "appointments.empty": "Zapisaŭ pakul niama",
  "appointments.cancel": "Adkanavać",
  "appointments.reschedule": "Pieranieści",
  "appointments.cancelled": "Zapis adkanavany",
  "appointments.deadlinePassed": "Adkanavańnie niedastupna: da pryjomu mienš za 2 hadziny",
  "appointments.startsAt": "Pryjom",
  "profile.title": "Profil",
  "profile.name": "Imia",
  "profile.phone": "Telefon",
  "profile.deleteAccount": "Vydalić akaut i danych",
  "profile.deleteWarning":
    "Aktyŭnyja zapisy buduć adkanavany, asabistyja danych vydaleny. Dziejannie nieźvarotnaje.",
  "profile.deleted": "Danych vydaleny",
  "common.loading": "Zahruzka…",
  "common.error": "Štości pajšlo nia tak",
  "common.retry": "Paučaryć",
  "common.back": "Nazad",
  "common.cancel": "Admova",
  "common.confirm": "Tak, padcvierdžaju",
};

export const dictionaries: Record<Locale, Dictionary> = {
  ru,
  en,
  "be-Latn": beLatn,
};

/** Определяет язык по language_code из Telegram. */
export function detectLocale(languageCode?: string): Locale {
  const normalized = (languageCode ?? "").toLowerCase();
  if (normalized.startsWith("be")) {
    return "be-Latn";
  }
  if (normalized.startsWith("en")) {
    return "en";
  }
  return "ru";
}

/** Перевод по ключу с откатом на русский и сам ключ, если перевода нет. */
export function translate(locale: Locale, key: string): string {
  return dictionaries[locale][key] ?? dictionaries.ru[key] ?? key;
}
