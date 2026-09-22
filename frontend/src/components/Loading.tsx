import { useT } from "../i18n/context";

/** Индикатор загрузки: крутящийся логотип + подпись «Загрузка…». */
export default function Loading() {
  const t = useT();

  return (
    <div className="loading">
      <img alt="" className="logo-img logo-img--small spinner" src="/logo.svg?v=1" />
      <span className="muted">{t("common.loading")}</span>
    </div>
  );
}
