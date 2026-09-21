import { createContext, useContext, type ReactNode } from "react";

import { translate, type Locale } from "./index";

const LocaleContext = createContext<Locale>("ru");

export function LocaleProvider({
  locale,
  children,
}: {
  locale: Locale;
  children: ReactNode;
}) {
  return <LocaleContext.Provider value={locale}>{children}</LocaleContext.Provider>;
}

/** Возвращает функцию перевода для текущей локали. */
export function useT(): (key: string) => string {
  const locale = useContext(LocaleContext);
  return (key: string) => translate(locale, key);
}
