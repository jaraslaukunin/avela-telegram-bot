import { useEffect, useState } from "react";
import { NavLink, Route, Routes } from "react-router-dom";

import { ApiError, NotInTelegramError, restoreOrLogin } from "./api/client";
import { CalendarIcon, HomeIcon, SettingsIcon, UserIcon } from "./components/Icon";
import { LocaleProvider, useT } from "./i18n/context";
import AdminAppointmentsScreen from "./screens/admin/AdminAppointmentsScreen";
import AdminAdminsScreen from "./screens/admin/AdminAdminsScreen";
import AdminBranchesScreen from "./screens/admin/AdminBranchesScreen";
import AdminDoctorsScreen from "./screens/admin/AdminDoctorsScreen";
import AdminHomeScreen from "./screens/admin/AdminHomeScreen";
import AdminScheduleScreen from "./screens/admin/AdminScheduleScreen";
import AdminServicesScreen from "./screens/admin/AdminServicesScreen";
import { useAdminScope } from "./screens/admin/useAdminScope";
import BookingScreen from "./screens/BookingScreen";
import HomeScreen from "./screens/HomeScreen";
import LandingScreen from "./screens/LandingScreen";
import MyAppointmentsScreen from "./screens/MyAppointmentsScreen";
import PatientsScreen from "./screens/PatientsScreen";
import ProfileScreen from "./screens/ProfileScreen";
import RescheduleScreen from "./screens/RescheduleScreen";
import { currentColorScheme, waitForTelegramWebApp } from "./telegram";

type AuthState = "loading" | "ready" | "error";

export default function App() {
  return (
    <LocaleProvider>
      <AppInner />
    </LocaleProvider>
  );
}

function AppInner() {
  const t = useT();
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
    return <ScreenMessage title="Avela" text={t("common.loading")} />;
  }

  if (authState === "error") {
    if (notInTelegram) {
      return (
        <div className="app">
          <main className="app__content">
            <LandingScreen />
          </main>
        </div>
      );
    }

    return (
      <div className="screen screen--centered">
        <img alt="Avela" className="logo-img logo-img--small" src="/logo.svg" />
        <h1 className="logo">Avela</h1>
        <p className="muted">{authError}</p>
        <button
          className="button button--primary button--big"
          onClick={() => setAttempt((value) => value + 1)}
          type="button"
        >
          {t("common.retry")}
        </button>
      </div>
    );
  }

  return (
    <div className="app">
      <main className="app__content">
        <Routes>
          <Route path="/" element={<HomeScreen />} />
          <Route path="/booking" element={<BookingScreen />} />
          <Route path="/appointments" element={<MyAppointmentsScreen />} />
          <Route path="/appointments/reschedule" element={<RescheduleScreen />} />
          <Route path="/patients" element={<PatientsScreen />} />
          <Route path="/profile" element={<ProfileScreen />} />

          <Route
            path="/admin"
            element={isAdmin ? <AdminHomeScreen /> : <NoAccessScreen />}
          />
          <Route
            path="/admin/admins"
            element={isAdmin ? <AdminAdminsScreen /> : <NoAccessScreen />}
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
            path="/admin/services"
            element={isAdmin ? <AdminServicesScreen /> : <NoAccessScreen />}
          />
          <Route
            path="/admin/branches"
            element={isAdmin ? <AdminBranchesScreen /> : <NoAccessScreen />}
          />
          <Route
            path="/admin/schedule"
            element={isAdmin ? <AdminScheduleScreen /> : <NoAccessScreen />}
          />
        </Routes>
      </main>

      <nav className="tabbar">
        <NavLink className={tabClass} end to="/">
          <HomeIcon />
          <span>{t("app.title")}</span>
        </NavLink>
        <NavLink className={tabClass} to="/appointments">
          <CalendarIcon />
          <span>{t("appointments.title")}</span>
        </NavLink>
        <NavLink className={tabClass} to="/profile">
          <UserIcon />
          <span>{t("profile.title")}</span>
        </NavLink>
        {isAdmin ? (
          <NavLink className={tabClass} to="/admin">
            <SettingsIcon />
            <span>{t("admin.tab")}</span>
          </NavLink>
        ) : null}
      </nav>
    </div>
  );
}

function tabClass({ isActive }: { isActive: boolean }): string {
  return isActive ? "tabbar__item tabbar__item--active" : "tabbar__item";
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
  return (
    <div className="screen screen--centered">
      <img alt={title} className="logo-img logo-img--small" src="/logo.svg?v=1" />
      <h1 className="logo">{title}</h1>
      <p className="muted">{text}</p>
    </div>
  );
}
