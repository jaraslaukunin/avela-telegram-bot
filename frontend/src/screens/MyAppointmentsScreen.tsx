import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { api } from "../api/client";
import { Loading } from "../components/Loading";
import { formatDateTime, isCancellable } from "../format";
import { useT } from "../i18n/context";

export default function MyAppointmentsScreen() {
  const t = useT();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const location = useLocation();
  const state = location.state as { booked?: boolean } | null;
  const [error, setError] = useState("");
  const [confirmingId, setConfirmingId] = useState<string | null>(null);

  const appointments = useQuery({
    queryKey: ["appointments"],
    queryFn: api.myAppointments,
  });

  const visibleAppointments = (appointments.data ?? []).filter((appointment) => {
    const endsAt = new Date(appointment.ends_at);

    return Number.isNaN(endsAt.getTime()) || endsAt >= new Date();
  });

  const cancel = useMutation({
    mutationFn: (appointmentId: string) => api.cancel(appointmentId),
    onSuccess: async () => {
      setError("");
      setConfirmingId(null);
      await queryClient.invalidateQueries({ queryKey: ["appointments"] });
    },
    onError: (mutationError: unknown) =>
      setError(mutationError instanceof Error ? mutationError.message : t("common.error")),
  });

  return (
    <div className="screen">
      <h2>{t("appointments.title")}</h2>

      {state?.booked ? <p className="success">{t("booking.success")}</p> : null}
      {error ? <p className="error">{error}</p> : null}
      {appointments.isLoading ? <Loading /> : null}

      {appointments.data && visibleAppointments.length === 0 ? (
        <p className="muted">{t("appointments.empty")}</p>
      ) : null}

      {visibleAppointments.map((appointment) => {
        const cancellable =
          appointment.status === "active" && isCancellable(appointment.cancellable_until);

        return (
          <article className="card" key={appointment.id}>
            <h3 className="card__title">{appointment.service_name}</h3>

            {appointment.patient_full_name ? (
              <p className="card__meta">
                {t("appointments.patient")}: <strong>{appointment.patient_full_name}</strong>
              </p>
            ) : null}

            <p className="card__meta">{appointment.doctor_name}</p>

            <p className="card__meta">
              {appointment.branch_name}
              {appointment.branch_address ? `, ${appointment.branch_address}` : ""}
            </p>

            <p className="card__time">
              {formatDateTime(appointment.starts_at, appointment.branch_timezone)}
            </p>

            {appointment.status !== "active" ? (
              <p className="muted">{appointment.status}</p>
            ) : null}

            {appointment.status === "active" ? (
              <div className="card__actions">
                {cancellable ? (
                  confirmingId === appointment.id ? (
                    <>
                      <p className="muted">{t("appointments.cancelConfirm")}</p>

                      <button
                        className="button button--danger"
                        disabled={cancel.isPending}
                        onClick={() => cancel.mutate(appointment.id)}
                        type="button"
                      >
                        {t("common.yesCancel")}
                      </button>

                      <button
                        className="button button--secondary"
                        disabled={cancel.isPending}
                        onClick={() => setConfirmingId(null)}
                        type="button"
                      >
                        {t("common.cancel")}
                      </button>
                    </>
                  ) : (
                    <>
                      <button
                        className="button button--danger"
                        onClick={() => setConfirmingId(appointment.id)}
                        type="button"
                      >
                        {t("appointments.cancel")}
                      </button>

                      <button
                        className="button button--secondary"
                        onClick={() =>
                          navigate("/appointments/reschedule", {
                            state: { appointment },
                          })
                        }
                        type="button"
                      >
                        {t("appointments.reschedule")}
                      </button>
                    </>
                  )
                ) : (
                  <p className="muted">
                    {t("appointments.deadlinePassed")}
                    {appointment.branch_phone ? ` — ${appointment.branch_phone}` : ""}
                  </p>
                )}
              </div>
            ) : null}
          </article>
        );
      })}
    </div>
  );
}