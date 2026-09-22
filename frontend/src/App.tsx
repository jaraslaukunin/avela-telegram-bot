import { useEffect, useState } from "react";
import { Link, Route, Routes } from "react-router-dom";

import { ApiError, NotInTelegramError, restoreOrLogin } from "./api/client";
import { detectLocale, translate, type Locale } from "./i18n";
import { LocaleProvider, useT } from "./i18n/context";
import AdminAppointmentsScreen from "./screens/admin/AdminAppointmentsScreen";
import AdminDoctorsScreen from "./screens/admin/AdminDoctorsScreen";
import AdminHomeScreen from "./screens/admin/AdminHomeScreen";
import AdminScheduleScreen from "./screens/admin/AdminScheduleScreen";
import { useAdminScope } from "./screens/admin/useAdminScope";
import BookingScreen from "./screens/BookingScreen";
import HomeScreen from "./screens/HomeScreen";
import LandingScreen from "./screens/LandingScreen";
import MyAppointmentsScreen from "./screens/MyAppointmentsScreen";
import ProfileScreen from "./screens/ProfileScreen";
import RescheduleScreen from "./screens/RescheduleScreen";
import { currentColorScheme, getTelegramLanguage, waitForTelegramWebApp } from "./telegram";

type AuthState = "loading" | "ready" | "error";

export default function App() {
  const [locale] = useState<Locale>(() => detectLocale(getTelegramLanguage()));
  const [authState, setAuthState] = useState<AuthState>("loading");
  const [authError, setAuthError] = useState<string>("");
  const [notInTelegram, setNotInTelegram] = useState(false);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    document.documentElement.dataset.theme = currentColorScheme();
  }, []);

  useEffect(() => {
    let cancelled = false;
    setAuthState("loading");

    const run = async () => {
      await waitForTelegramWebApp();
      return restoreOrLogin();
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
        if (error instanceof NotInTelegramError) {
          setNotInTelegram(true);
          setAuthState("error");
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

  const scope = useAdminScope({ enabled: authState === "ready" });
  const isAdmin = Boolean(scope.data && scope.data.role !== "patient");

  if (authState === "loading") {
    return (
      <LocaleProvider locale={locale}>
        <ScreenMessage title="Avela" text={translate(locale, "common.loading")} />
      </LocaleProvider>
    );
  }

  if (authState === "error") {
    if (notInTelegram) {
      return (
        <LocaleProvider locale={locale}>
          <div className="app">
            <main className="app__content">
              <LandingScreen />
            </main>
          </div>
        </LocaleProvider>
      );
    }

    return (
      <LocaleProvider locale={locale}>
        <div className="screen screen--centered">
          <h1 className="logo">Avela</h1>
          <p className="muted">{authError}</p>
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

            <Route
              path="/admin"
              element={isAdmin ? <AdminHomeScreen /> : <NoAccessScreen />}
            />
            <Route
              path="/admin/appointments"
              element={isAdmin ? <AdminAppointmentsScreen /> : <NoAccessScreen />}
            />
            <Route
              path="/admin/doctors"
              element={isAdmin ? <AdminDoctorsScreen /> : <NoAccessScreen />}
            />
            <Route
              path="/admin/schedule"
              element={isAdmin ? <AdminScheduleScreen /> : <NoAccessScreen />}
            />
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
          {isAdmin ? (
            <Link className="tabbar__item" to="/admin">
              {translate(locale, "admin.tab")}
            </Link>
          ) : null}
        </nav>
      </div>
    </LocaleProvider>
  );
}

function NoAccessScreen() {
  const t = useT();

  return (
    <div className="screen screen--centered">
      <h2>{t("admin.noAccess")}</h2>
      <p className="muted">{t("admin.noAccessHint")}</p>
    </div>
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
