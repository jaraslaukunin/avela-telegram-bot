import { Link } from "react-router-dom";

import { useT } from "../i18n/context";

export default function HomeScreen() {
  const t = useT();

  return (
    <div className="screen">
      <header className="hero">
        <img alt="Avela" className="logo-img" src="/logo.svg" />
        <h1 className="logo">Avela</h1>
        <p className="hero__tagline">{t("app.tagline")}</p>
      </header>

      <nav className="home-actions">
        <Link className="button button--primary button--big" to="/booking">
          {t("home.book")}
        </Link>
        <Link className="button button--secondary button--big" to="/appointments">
          {t("home.myAppointments")}
        </Link>
      </nav>

      <p className="muted home-note">{t("booking.noSlots")}</p>
    </div>
  );
}
