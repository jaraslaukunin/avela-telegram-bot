import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { api } from "../api/client";
import type { AppointmentOut } from "../api/types";
import { formatDate, formatTime } from "../format";
import { useT } from "../i18n/context";

export default function RescheduleScreen() {
  const t = useT();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const location = useLocation();
  const appointment =
    (location.state as { appointment?: AppointmentOut } | null)?.appointment ?? null;

  const [slotId, setSlotId] = useState<string | null>(null);
  const [error, setError] = useState("");

  const slots = useQuery({
    queryKey: ["slots", appointment?.service_id, appointment?.doctor_id],
    queryFn: () =>
      api.availableSlots({
        serviceId: appointment?.service_id ?? "",
        doctorId: appointment?.doctor_id,
      }),
    enabled: Boolean(appointment),
    staleTime: 5_000,
  });

  const reschedule = useMutation({
    mutationFn: (newSlotId: string) => api.reschedule(appointment?.id ?? "", newSlotId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["appointments"] });
      navigate("/appointments");
    },
    onError: (mutationError: unknown) =>
      setError(mutationError instanceof Error ? mutationError.message : t("common.error")),
  });

  if (!appointment) {
    return (
      <div className="screen">
        <p className="muted">{t("common.error")}</p>
        <button className="button" onClick={() => navigate("/appointments")} type="button">
          {t("common.back")}
        </button>
      </div>
    );
  }

  return (
    <div className="screen">
      <h2>{t("appointments.reschedule")}</h2>
      <p className="muted">{appointment.service_name}</p>

      {slots.isLoading ? <p className="muted">{t("common.loading")}</p> : null}
      {slots.data && slots.data.length === 0 ? (
        <p className="muted">{t("booking.noSlots")}</p>
      ) : null}

      <div className="slots">
        {slots.data?.map((slot) => (
          <button
            key={slot.id}
            className={slot.id === slotId ? "slot slot--active" : "slot"}
            onClick={() => setSlotId(slot.id)}
            type="button"
          >
            <span className="slot__date">{formatDate(slot.starts_at)}</span>
            <span className="slot__time">{formatTime(slot.starts_at)}</span>
          </button>
        ))}
      </div>

      {error ? <p className="error">{error}</p> : null}

      <button
        className="button button--primary button--big"
        disabled={!slotId || reschedule.isPending}
        onClick={() => slotId && reschedule.mutate(slotId)}
        type="button"
      >
        {reschedule.isPending ? t("common.loading") : t("common.confirm")}
      </button>
    </div>
  );
}
