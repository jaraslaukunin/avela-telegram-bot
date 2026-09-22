import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { detectLocale, locales, translate, type Locale } from "./index";
import { getTelegramLanguage } from "../telegram";

const LOCALE_KEY = "avela_locale";

interface I18nContextValue {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (key: string) => string;
}

const I18nContext = createContext<I18nContextValue | null>(null);

function readStoredLocale(): Locale | null {
  try {
    const value = sessionStorage.getItem(LOCALE_KEY);
    if (value && (locales as readonly string[]).includes(value)) {
      return value as Locale;
    }
  } catch {
    // приватный режим / запрет storage — просто вернём null
  }
  return null;
}

export function LocaleProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(
    () => readStoredLocale() ?? detectLocale(getTelegramLanguage()),
  );

  const setLocale = useCallback((value: Locale) => {
    setLocaleState(value);
    try {
      sessionStorage.setItem(LOCALE_KEY, value);
    } catch {
      // storage недоступен — язык живёт только в памяти сессии
    }
  }, []);

  const t = useCallback((key: string) => translate(locale, key), [locale]);

  const value = useMemo(() => ({ locale, setLocale, t }), [locale, setLocale, t]);

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

/** Функция перевода для текущей локали. */
export function useT(): (key: string) => string {
  const context = useContext(I18nContext);
  return context ? context.t : (key: string) => key;
}

export function useLocale(): Locale {
  return useContext(I18nContext)?.locale ?? "ru";
}

export function useSetLocale(): (locale: Locale) => void {
  return useContext(I18nContext)?.setLocale ?? (() => undefined);
}
