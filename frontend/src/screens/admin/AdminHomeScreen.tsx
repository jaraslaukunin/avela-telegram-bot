import { Link } from "react-router-dom";

import { useT } from "../../i18n/context";

export default function AdminHomeScreen() {
  const t = useT();

  return (
    <div className="screen">
      <h2>{t("admin.title")}</h2>

      <nav className="home-actions">
        <Link className="button button--primary button--big" to="/admin/appointments">
          {t("admin.appointments")}
        </Link>
        <Link className="button button--secondary button--big" to="/admin/admins">
          {t("admin.admins")}
        </Link>
        <Link className="button button--secondary button--big" to="/admin/doctors">
          {t("admin.doctors")}
        </Link>
        <Link className="button button--secondary button--big" to="/admin/services">
          {t("admin.services")}
        </Link>
        <Link className="button button--secondary button--big" to="/admin/branches">
          {t("admin.branches")}
        </Link>
        <Link className="button button--secondary button--big" to="/admin/schedule">
          {t("admin.schedule")}
        </Link>
      </nav>
    </div>
  );
}
