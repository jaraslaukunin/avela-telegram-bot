import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "../../api/client";
import { formatDate, formatDateTime, formatTime } from "../../format";
import { useT } from "../../i18n/context";

export default function AdminAppointmentsScreen() {
  const t = useT();
  const queryClient = useQueryClient();
  const [branchId, setBranchId] = useState("");
  const [error, setError] = useState("");
  const [reschedulingId, setReschedulingId] = useState<string | null>(null);
  const [newSlotId, setNewSlotId] = useState("");

  const branches = useQuery({
    queryKey: ["admin-branches"],
    queryFn: () => api.adminBranches(),
    staleTime: 5 * 60_000,
  });

  const appointments = useQuery({
    queryKey: ["admin-appointments", branchId],
    queryFn: () => api.adminAppointments(branchId || undefined),
    staleTime: 10_000,
  });

  const cancel = useMutation({
    mutationFn: (appointmentId: string) => api.adminCancelAppointment(appointmentId),
    onSuccess: async () => {
      setError("");
      await queryClient.invalidateQueries({ queryKey: ["admin-appointments"] });
    },
    onError: (mutationError: unknown) =>
      setError(mutationError instanceof Error ? mutationError.message : t("common.error")),
  });

  const reschedulingAppointment = appointments.data?.find(
    (appointment) => appointment.id === reschedulingId,
  );

  const rescheduleSlots = useQuery({
    queryKey: [
      "admin-reschedule-slots",
      reschedulingAppointment?.doctor_id,
      reschedulingAppointment?.service_id,
    ],
    queryFn: () =>
      api.availableSlots({
        serviceId: reschedulingAppointment?.service_id ?? "",
        doctorId: reschedulingAppointment?.doctor_id,
      }),
    enabled: Boolean(reschedulingAppointment),
    staleTime: 10_000,
  });

  const reschedule = useMutation({
    mutationFn: () => api.adminRescheduleAppointment(reschedulingId ?? "", newSlotId),
    onSuccess: async () => {
      setError("");
      setReschedulingId(null);
      setNewSlotId("");
      await queryClient.invalidateQueries({ queryKey: ["admin-appointments"] });
    },
    onError: (mutationError: unknown) =>
      setError(mutationError instanceof Error ? mutationError.message : t("common.error")),
  });

  const multipleBranches = (branches.data?.length ?? 0) > 1;

  return (
    <div className="screen">
      <h2>{t("admin.appointments")}</h2>

      {multipleBranches ? (
        <section className="section">
          <h3 className="section__title">{t("admin.chooseBranch")}</h3>
          <div className="section__body">
            <button
              className={branchId === "" ? "choice choice--active" : "choice"}
              onClick={() => setBranchId("")}
              type="button"
            >
              {t("admin.allBranches")}
            </button>
            {branches.data?.map((branch) => (
              <button
                key={branch.id}
                className={branch.id === branchId ? "choice choice--active" : "choice"}
                onClick={() => setBranchId(branch.id)}
                type="button"
              >
                {branch.name}
              </button>
            ))}
          </div>
        </section>
      ) : null}

      {appointments.isLoading ? <p className="muted">{t("common.loading")}</p> : null}
      {appointments.data && appointments.data.length === 0 ? (
        <p className="muted">{t("admin.noAppointments")}</p>
      ) : null}
      {error ? <p className="error">{error}</p> : null}

      {appointments.data?.map((appointment) => (
        <article className="card" key={appointment.id}>
          <h3 className="card__title">{appointment.patient_name}</h3>
          <p className="card__meta">
            {appointment.doctor_name} · {appointment.branch_name}
          </p>
          <p className="card__time">
            {formatDateTime(appointment.starts_at, appointment.branch_timezone)}
          </p>

          {appointment.status !== "active" ? (
            <p className="muted">
              {appointment.status}
              {appointment.cancelled_by ? ` (${appointment.cancelled_by})` : ""}
            </p>
          ) : null}

          {appointment.status === "active" ? (
            <>
              <div className="card__actions">
                <button
                  className="button button--danger"
                  disabled={cancel.isPending}
                  onClick={() => cancel.mutate(appointment.id)}
                  type="button"
                >
                  {t("admin.cancelAppointment")}
                </button>
                <button
                  className="button button--secondary"
                  onClick={() => {
                    setReschedulingId(
                      reschedulingId === appointment.id ? null : appointment.id,
                    );
                    setNewSlotId("");
                  }}
                  type="button"
                >
                  {t("admin.reschedule")}
                </button>
              </div>

              {reschedulingId === appointment.id ? (
                <>
                  <p className="muted">{t("admin.chooseNewSlot")}</p>
                  <div className="slots slots--scroll">
                    {rescheduleSlots.data?.map((value) => (
                      <button
                        key={value.id}
                        className={value.id === newSlotId ? "slot slot--active" : "slot"}
                        onClick={() => setNewSlotId(value.id)}
                        type="button"
                      >
                        <span className="slot__date">{formatDate(value.starts_at)}</span>
                        <span className="slot__time">{formatTime(value.starts_at)}</span>
                      </button>
                    ))}
                  </div>
                  {rescheduleSlots.data && rescheduleSlots.data.length === 0 ? (
                    <p className="muted">{t("booking.noSlots")}</p>
                  ) : null}
                  <button
                    className="button button--primary"
                    disabled={!newSlotId || reschedule.isPending}
                    onClick={() => reschedule.mutate()}
                    type="button"
                  >
                    {reschedule.isPending ? t("common.loading") : t("admin.confirmReschedule")}
                  </button>
                </>
              ) : null}
            </>
          ) : null}
        </article>
      ))}
    </div>
  );
}
