import { BellIcon, PinIcon, SearchIcon } from "../components/Icon";
import { useT } from "../i18n/context";

/**
 * Одностраничный лендинг для посетителей вне Telegram.
 *
 * Mini App работает только внутри клиента Telegram (там передаётся initData),
 * поэтому случайный посетитель из браузера видит визитку с тремя
 * преимуществами и кнопкой «Открыть в Telegram».
 */
export default function LandingScreen() {
  const t = useT();

  return (
    <div className="landing">
      <header className="landing__hero">
        <img alt="Avela" className="logo-img" src="/logo.svg?v=1" />
        <h1 className="landing__logo">Avela</h1>
        <p className="landing__tagline">{t("landing.tagline")}</p>
        <p className="muted">{t("landing.subtitle")}</p>
        <a
          className="button button--primary button--big landing__cta"
          href="https://t.me/avela_med_bot"
        >
          {t("landing.openInTelegram")}
        </a>
        <a className="button button--secondary button--big" href="/statuspage/">
          {t("landing.status")}
        </a>
      </header>

      <section className="landing__features">
        <article className="card landing__feature">
          <span className="landing__feature-icon">
            <SearchIcon />
          </span>
          <div>
            <h3>{t("landing.feature1Title")}</h3>
            <p className="muted">{t("landing.feature1Text")}</p>
          </div>
        </article>

        <article className="card landing__feature">
          <span className="landing__feature-icon">
            <PinIcon />
          </span>
          <div>
            <h3>{t("landing.feature2Title")}</h3>
            <p className="muted">{t("landing.feature2Text")}</p>
          </div>
        </article>

        <article className="card landing__feature">
          <span className="landing__feature-icon">
            <BellIcon />
          </span>
          <div>
            <h3>{t("landing.feature3Title")}</h3>
            <p className="muted">{t("landing.feature3Text")}</p>
          </div>
        </article>
      </section>

      <section className="card">
        <h2 className="section__title">{t("landing.howTitle")}</h2>
        <ol className="landing__steps">
          <li>{t("landing.how1")}</li>
          <li>{t("landing.how2")}</li>
          <li>{t("landing.how3")}</li>
        </ol>
      </section>

      <p className="muted landing__note">{t("landing.notInTelegram")}</p>
    </div>
  );
}
