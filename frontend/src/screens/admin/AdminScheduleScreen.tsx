import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { api } from "../../api/client";
import { DoctorCalendar } from "../../components/DoctorCalendar";
import { useT } from "../../i18n/context";
import { useAdminScope } from "./useAdminScope";

const WEEKDAYS = [0, 1, 2, 3, 4, 5, 6];

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

function plusDaysIso(days: number): string {
  const date = new Date();
  date.setDate(date.getDate() + days);
  return date.toISOString().slice(0, 10);
}

export default function AdminScheduleScreen() {
  const t = useT();
  const queryClient = useQueryClient();
  const scope = useAdminScope();

  const [branchId, setBranchId] = useState("");
  const [doctorId, setDoctorId] = useState("");
  const [serviceId, setServiceId] = useState("");
  const [weekday, setWeekday] = useState(0);
  const [startTime, setStartTime] = useState("09:00");
  const [endTime, setEndTime] = useState("12:00");
  const [validFrom, setValidFrom] = useState(todayIso());
  const [validUntil, setValidUntil] = useState("");
  const [generateFrom, setGenerateFrom] = useState(todayIso());
  const [generateTo, setGenerateTo] = useState(plusDaysIso(14));
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const networkId =
    scope.data && !scope.data.can_access_all ? scope.data.network_ids[0] : undefined;

  const branches = useQuery({
    queryKey: ["admin-branches"],
    queryFn: () => api.adminBranches(),
    staleTime: 5 * 60_000,
  });

  const services = useQuery({
    queryKey: ["admin-services", networkId],
    queryFn: () => api.adminServices(networkId),
    enabled: Boolean(scope.data),
    staleTime: 5 * 60_000,
  });

  const doctors = useQuery({
    queryKey: ["admin-doctors", branchId],
    queryFn: () => api.adminDoctors(branchId),
    enabled: Boolean(branchId),
    staleTime: 10_000,
  });

  const templates = useQuery({
    queryKey: ["admin-templates", doctorId],
    queryFn: () => api.adminScheduleTemplates(doctorId),
    enabled: Boolean(doctorId),
    staleTime: 10_000,
  });

  useEffect(() => {
    if (!branchId && branches.data && branches.data.length === 1) {
      setBranchId(branches.data[0].id);
    }
  }, [branchId, branches.data]);

  useEffect(() => {
    if (!serviceId && services.data && services.data.length > 0) {
      setServiceId(services.data[0].id);
    }
  }, [serviceId, services.data]);

  const createTemplate = useMutation({
    mutationFn: () =>
      api.adminCreateTemplate(doctorId, {
        service_id: serviceId,
        weekday,
        start_time: `${startTime}:00`,
        end_time: `${endTime}:00`,
        valid_from: validFrom,
        valid_until: validUntil || null,
      }),
    onSuccess: async () => {
      setError("");
      setMessage(t("admin.templateCreated"));
      await queryClient.invalidateQueries({ queryKey: ["admin-templates"] });
    },
    onError: (mutationError: unknown) =>
      setError(mutationError instanceof Error ? mutationError.message : t("common.error")),
  });

  const generateSlots = useMutation({
    mutationFn: (templateId: string) =>
      api.adminGenerateSlots(templateId, generateFrom, generateTo),
    onSuccess: (result) => {
      setError("");
      setMessage(`${t("admin.generated")}: ${result.created} (${t("admin.skipped")}: ${result.skipped})`);
    },
    onError: (mutationError: unknown) =>
      setError(mutationError instanceof Error ? mutationError.message : t("common.error")),
  });

  const selectedDoctor = doctors.data?.find((doctor) => doctor.id === doctorId);

  return (
    <div className="screen">
      <h2>{t("admin.schedule")}</h2>

      <section className="section">
        <h3 className="section__title">{t("admin.chooseBranch")}</h3>
        <div className="section__body">
          {branches.data?.map((branch) => (
            <button
              key={branch.id}
              className={branch.id === branchId ? "choice choice--active" : "choice"}
              onClick={() => {
                setBranchId(branch.id);
                setDoctorId("");
              }}
              type="button"
            >
              {branch.name}
            </button>
          ))}
        </div>
      </section>

      {branchId ? (
        <section className="section">
          <h3 className="section__title">{t("admin.chooseDoctor")}</h3>
          <div className="section__body">
            {doctors.data?.length ? null : <p className="muted">{t("admin.noDoctors")}</p>}
            {doctors.data?.map((doctor) => (
              <button
                key={doctor.id}
                className={doctor.id === doctorId ? "choice choice--active" : "choice"}
                onClick={() => setDoctorId(doctor.id)}
                type="button"
              >
                {doctor.full_name}
              </button>
            ))}
          </div>
        </section>
      ) : null}

      {doctorId ? <DoctorCalendar doctorId={doctorId} /> : null}

      {error ? <p className="error">{error}</p> : null}
      {message ? <p className="success">{message}</p> : null}

      {doctorId ? (
        <section className="section">
          <h3 className="section__title">{t("admin.createTemplate")}</h3>

          <label className="field">
            {t("admin.services")}
            <select
              className="input"
              onChange={(event) => setServiceId(event.target.value)}
              value={serviceId}
            >
              {services.data?.map((service) => (
                <option key={service.id} value={service.id}>
                  {service.name}
                </option>
              ))}
            </select>
          </label>

          <label className="field">
            {t("admin.weekday")}
            <select
              className="input"
              onChange={(event) => setWeekday(Number(event.target.value))}
              value={weekday}
            >
              {WEEKDAYS.map((day) => (
                <option key={day} value={day}>
                  {t(`weekday.${day}`)}
                </option>
              ))}
            </select>
          </label>

          <label className="field">
            {t("admin.timeFrom")}
            <input
              className="input"
              onChange={(event) => setStartTime(event.target.value)}
              type="time"
              value={startTime}
            />
          </label>

          <label className="field">
            {t("admin.timeTo")}
            <input
              className="input"
              onChange={(event) => setEndTime(event.target.value)}
              type="time"
              value={endTime}
            />
          </label>

          <label className="field">
            {t("admin.validFrom")}
            <input
              className="input"
              onChange={(event) => setValidFrom(event.target.value)}
              type="date"
              value={validFrom}
            />
          </label>

          <label className="field">
            {t("admin.validUntil")}
            <input
              className="input"
              onChange={(event) => setValidUntil(event.target.value)}
              type="date"
              value={validUntil}
            />
          </label>

          <button
            className="button button--primary"
            disabled={!serviceId || createTemplate.isPending}
            onClick={() => createTemplate.mutate()}
            type="button"
          >
            {createTemplate.isPending ? t("common.saving") : t("admin.createTemplate")}
          </button>
        </section>
      ) : null}

      {doctorId ? (
        <section className="section">
          <h3 className="section__title">{t("admin.templates")}</h3>

          <div className="section__body">
            <label className="field">
              {t("admin.generateFrom")}
              <input
                className="input"
                onChange={(event) => setGenerateFrom(event.target.value)}
                type="date"
                value={generateFrom}
              />
            </label>
            <label className="field">
              {t("admin.generateTo")}
              <input
                className="input"
                onChange={(event) => setGenerateTo(event.target.value)}
                type="date"
                value={generateTo}
              />
            </label>
          </div>

          {templates.isLoading ? <p className="muted">{t("common.loading")}</p> : null}
          {templates.data && templates.data.length === 0 ? (
            <p className="muted">{t("admin.noTemplates")}</p>
          ) : null}

          {templates.data?.map((template) => (
            <article className="card" key={template.id}>
              <h3 className="card__title">
                {t(`weekday.${template.weekday}`)} · {template.start_time.slice(0, 5)}—
                {template.end_time.slice(0, 5)}
              </h3>
              <p className="card__meta">
                {services.data?.find((service) => service.id === template.service_id)?.name ?? ""}
              </p>
              <p className="card__meta">
                {t("admin.validFrom")} {template.valid_from}
                {template.valid_until ? ` ${t("admin.validUntil")} ${template.valid_until}` : ""}
              </p>
              <div className="card__actions">
                <button
                  className="button button--secondary"
                  disabled={generateSlots.isPending}
                  onClick={() => generateSlots.mutate(template.id)}
                  type="button"
                >
                  {generateSlots.isPending ? t("common.loading") : t("admin.generateSlots")}
                </button>
              </div>
            </article>
          ))}

          {selectedDoctor ? <p className="muted">{selectedDoctor.full_name}</p> : null}
        </section>
      ) : null}
    </div>
  );
}
