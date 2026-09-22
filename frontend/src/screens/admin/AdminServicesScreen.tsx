import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { api } from "../../api/client";
import { useT } from "../../i18n/context";
import { useAdminScope } from "./useAdminScope";

/** Услуги сети: список и создание (услуга обязательна для врача). */
export default function AdminServicesScreen() {
  const t = useT();
  const queryClient = useQueryClient();
  const scope = useAdminScope();

  const [name, setName] = useState("");
  const [duration, setDuration] = useState(30);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const branches = useQuery({
    queryKey: ["admin-branches"],
    queryFn: () => api.adminBranches(),
    enabled: Boolean(scope.data),
    staleTime: 5 * 60_000,
  });

  // Админ сети/филиала работает в своей сети; администратор Avela — в сети
  // первого доступного филиала (выбор сети появится отдельным шагом).
  const networkId =
    scope.data && !scope.data.can_access_all
      ? scope.data.network_ids[0]
      : branches.data?.[0]?.network_id;

  const services = useQuery({
    queryKey: ["admin-services", networkId],
    queryFn: () => api.adminServices(networkId),
    enabled: Boolean(scope.data),
    staleTime: 30_000,
  });

  useEffect(() => {
    if (!name) {
      setMessage("");
    }
  }, [name]);

  const createService = useMutation({
    mutationFn: () =>
      api.adminCreateService(networkId ?? "", {
        name: name.trim(),
        duration_minutes: duration,
      }),
    onSuccess: async () => {
      setError("");
      setMessage(t("admin.created"));
      setName("");
      setDuration(30);
      await queryClient.invalidateQueries({ queryKey: ["admin-services"] });
    },
    onError: (mutationError: unknown) =>
      setError(mutationError instanceof Error ? mutationError.message : t("common.error")),
  });

  return (
    <div className="screen">
      <h2>{t("admin.services")}</h2>

      {error ? <p className="error">{error}</p> : null}
      {message ? <p className="success">{message}</p> : null}

      <section className="card">
        <h3 className="section__title">{t("admin.createService")}</h3>
        <input
          className="input"
          onChange={(event) => setName(event.target.value)}
          placeholder={t("admin.serviceName")}
          value={name}
        />
        <label className="field">
          {t("admin.duration")}
          <input
            className="input"
            min={5}
            max={240}
            onChange={(event) => setDuration(Number(event.target.value))}
            type="number"
            value={duration}
          />
        </label>
        <button
          className="button button--primary"
          disabled={!name.trim() || !networkId || createService.isPending}
          onClick={() => createService.mutate()}
          type="button"
        >
          {createService.isPending ? t("common.saving") : t("admin.createService")}
        </button>
      </section>

      {services.isLoading ? <p className="muted">{t("common.loading")}</p> : null}
      {services.data && services.data.length === 0 ? (
        <p className="muted">{t("admin.noServices")}</p>
      ) : null}

      {services.data?.map((service) => (
        <article className="card" key={service.id}>
          <h3 className="card__title">{service.name}</h3>
          <p className="card__meta">
            {service.duration_minutes} {t("admin.minutes")}
          </p>
        </article>
      ))}
    </div>
  );
}
