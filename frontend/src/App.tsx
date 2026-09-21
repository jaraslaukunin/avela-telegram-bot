import { useEffect, useState } from "react";
import { Link, Route, Routes } from "react-router-dom";

import { ApiError, login } from "./api/client";
import { detectLocale, translate, type Locale } from "./i18n";
import { LocaleProvider, useT } from "./i18n/context";
import BookingScreen from "./screens/BookingScreen";
import HomeScreen from "./screens/HomeScreen";
import MyAppointmentsScreen from "./screens/MyAppointmentsScreen";
import ProfileScreen from "./screens/ProfileScreen";
import RescheduleScreen from "./screens/RescheduleScreen";
import { currentColorScheme, getTelegramLanguage, waitForTelegramWebApp } from "./telegram";

type AuthState = "loading" | "ready" | "error";

export default function App() {
  const [locale] = useState<Locale>(() => detectLocale(getTelegramLanguage()));
  const [authState, setAuthState] = useState<AuthState>("loading");
  const [authError, setAuthError] = useState<string>("");
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    document.documentElement.dataset.theme = currentColorScheme();
  }, []);

  useEffect(() => {
    let cancelled = false;
    setAuthState("loading");

    const run = async () => {
      await waitForTelegramWebApp();
      return login();
    };

    run()
      .then(() => {
        if (!cancelled) {
          setAuthState("ready");
        }
      })
      .catch((error: unknown) => {
        if (cancelled) {
          return;
        }
        setAuthError(
          error instanceof ApiError ? error.message : "Не удалось выполнить вход",
        );
        setAuthState("error");
      });

    return () => {
      cancelled = true;
    };
  }, [attempt]);

  if (authState === "loading") {
    return (
      <LocaleProvider locale={locale}>
        <ScreenMessage title="Avela" text={translate(locale, "common.loading")} />
      </LocaleProvider>
    );
  }

  if (authState === "error") {
    return (
      <LocaleProvider locale={locale}>
        <div className="screen screen--centered">
          <h1 className="logo">Avela</h1>
          <p className="muted">{authError}</p>
          <p className="muted">
            Приложение работает только внутри Telegram: откройте бота и нажмите
            кнопку приложения, либо «Повторить», если окно только что открылось.
          </p>
          <button
            className="button button--primary button--big"
            onClick={() => setAttempt((value) => value + 1)}
            type="button"
          >
            {translate(locale, "common.retry")}
          </button>
        </div>
      </LocaleProvider>
    );
  }

  return (
    <LocaleProvider locale={locale}>
      <div className="app">
        <main className="app__content">
          <Routes>
            <Route path="/" element={<HomeScreen />} />
            <Route path="/booking" element={<BookingScreen />} />
            <Route path="/appointments" element={<MyAppointmentsScreen />} />
            <Route path="/appointments/reschedule" element={<RescheduleScreen />} />
            <Route path="/profile" element={<ProfileScreen />} />
          </Routes>
        </main>
        <nav className="tabbar">
          <Link className="tabbar__item" to="/">
            {translate(locale, "app.title")}
          </Link>
          <Link className="tabbar__item" to="/appointments">
            {translate(locale, "appointments.title")}
          </Link>
          <Link className="tabbar__item" to="/profile">
            {translate(locale, "profile.title")}
          </Link>
        </nav>
      </div>
    </LocaleProvider>
  );
}

function ScreenMessage({ title, text }: { title: string; text: string }) {
  const t = useT();
  return (
    <div className="screen screen--centered">
      <h1 className="logo">{title}</h1>
      <p className="muted">{text || t("common.loading")}</p>
    </div>
  );
}
