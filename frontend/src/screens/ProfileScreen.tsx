import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";

import { api } from "../api/client";
import { useLocale, useSetLocale, useT } from "../i18n/context";
import { locales, type Locale } from "../i18n";

const LANGUAGE_LABELS: Record<Locale, string> = {
  ru: "Рус",
  en: "Eng",
  "be-Latn": "Бел",
};

export default function ProfileScreen() {
  const t = useT();
  const locale = useLocale();
  const setLocale = useSetLocale();
  const [confirming, setConfirming] = useState(false);
  const [deleted, setDeleted] = useState(false);

  const me = useQuery({ queryKey: ["me"], queryFn: api.me });

  const remove = useMutation({
    mutationFn: api.deleteMe,
    onSuccess: () => setDeleted(true),
  });

  if (deleted) {
    return (
      <div className="screen screen--centered">
        <h2>{t("profile.deleted")}</h2>
        <p className="muted">{t("profile.deleteWarning")}</p>
      </div>
    );
  }

  return (
    <div className="screen">
      <h2>{t("profile.title")}</h2>

      {me.isLoading ? <p className="muted">{t("common.loading")}</p> : null}

      {me.data ? (
        <div className="card">
          <p className="card__meta">
            {t("profile.name")}: {me.data.first_name} {me.data.last_name}
          </p>
          <p className="card__meta">
            {t("profile.phone")}: {me.data.phone ?? "—"}
          </p>
        </div>
      ) : null}

      <Link className="button button--secondary button--big" to="/patients">
        {t("profile.patients")}
      </Link>

      <section className="card">
        <h3 className="section__title">{t("profile.language")}</h3>
        <div className="lang-switcher">
          {locales.map((value) => (
            <button
              key={value}
              className={
                value === locale
                  ? "lang-switcher__item lang-switcher__item--active"
                  : "lang-switcher__item"
              }
              onClick={() => setLocale(value)}
              type="button"
            >
              {LANGUAGE_LABELS[value]}
            </button>
          ))}
        </div>
      </section>

      <section className="section">
        <h3 className="section__title">{t("profile.deleteAccount")}</h3>
        {confirming ? (
          <>
            <p className="muted">{t("profile.deleteWarning")}</p>
            <div className="card__actions">
              <button
                className="button button--danger"
                disabled={remove.isPending}
                onClick={() => remove.mutate()}
                type="button"
              >
                {t("common.confirm")}
              </button>
              <button
                className="button button--secondary"
                onClick={() => setConfirming(false)}
                type="button"
              >
                {t("common.cancel")}
              </button>
            </div>
          </>
        ) : (
          <button
            className="button button--secondary"
            onClick={() => setConfirming(true)}
            type="button"
          >
            {t("profile.deleteAccount")}
          </button>
        )}
      </section>
    </div>
  );
}
