import { useT } from "../i18n/context";

/**
 * Лендинг для тех, кто открыл avela.jaraslau.dev не из Telegram.
 *
 * Mini App работает только внутри клиента Telegram (там передаётся initData),
 * поэтому для случайного посетителя из браузера показываем аккуратную
 * страницу-визитку вместо «Откройте через Telegram».
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
        <a className="button button--primary button--big landing__cta" href="https://t.me/avela_med_bot">
          {t("landing.openInTelegram")}
        </a>
      </header>

      <section className="section">
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
