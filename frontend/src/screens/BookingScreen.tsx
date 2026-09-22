import { useMutation, useQuery } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";

import { api } from "../api/client";
import { formatDate, formatTime } from "../format";
import { useT } from "../i18n/context";
import { hapticImpact } from "../telegram";

export default function BookingScreen() {
  const t = useT();
  const navigate = useNavigate();

  const [networkId, setNetworkId] = useState<string | null>(null);
  const [serviceId, setServiceId] = useState<string | null>(null);
  const [branchId, setBranchId] = useState<string | null>(null);
  const [doctorId, setDoctorId] = useState<string | null>(null);
  const [slotId, setSlotId] = useState<string | null>(null);
  const [error, setError] = useState<string>("");

  const networks = useQuery({
    queryKey: ["networks"],
    queryFn: api.networks,
    staleTime: 5 * 60_000,
  });
  const services = useQuery({
    queryKey: ["services", networkId],
    queryFn: () => api.services(networkId ?? ""),
    enabled: Boolean(networkId),
    staleTime: 5 * 60_000,
  });
  const branches = useQuery({
    queryKey: ["branches", networkId],
    queryFn: () => api.branches(networkId ?? ""),
    enabled: Boolean(networkId),
    staleTime: 5 * 60_000,
  });
  const doctors = useQuery({
    queryKey: ["doctors", branchId, serviceId],
    queryFn: () => api.doctors(branchId ?? "", serviceId ?? ""),
    enabled: Boolean(branchId && serviceId),
    staleTime: 5 * 60_000,
  });
  const slots = useQuery({
    queryKey: ["slots", serviceId, branchId, doctorId],
    queryFn: () =>
      api.availableSlots({
        serviceId: serviceId ?? "",
        branchId: branchId ?? undefined,
        doctorId: doctorId ?? undefined,
      }),
    enabled: Boolean(serviceId && branchId),
    // Слоты меняются с каждой записью — держим их «свежими» недолго.
    staleTime: 5_000,
  });

  const book = useMutation({
    mutationFn: (id: string) => api.book(id),
    onSuccess: () => {
      hapticImpact();
      navigate("/appointments", { state: { booked: true } });
    },
    onError: (mutationError: unknown) =>
      setError(mutationError instanceof Error ? mutationError.message : t("common.error")),
  });

  return (
    <div className="screen">
      <h2>{t("booking.title")}</h2>

      <Section title={t("booking.network")}>
        {networks.data?.map((network) => (
          <Choice
            key={network.id}
            active={network.id === networkId}
            label={network.name}
            onClick={() => {
              setNetworkId(network.id);
              setServiceId(null);
              setBranchId(null);
              setDoctorId(null);
              setSlotId(null);
            }}
          />
        ))}
      </Section>

      {networkId ? (
        <Section title={t("booking.service")}>
          {services.data?.map((service) => (
            <Choice
              key={service.id}
              active={service.id === serviceId}
              label={service.name}
              onClick={() => {
                setServiceId(service.id);
                setSlotId(null);
              }}
            />
          ))}
        </Section>
      ) : null}

      {networkId ? (
        <Section title={t("booking.branch")}>
          {branches.data?.map((branch) => (
            <Choice
              key={branch.id}
              active={branch.id === branchId}
              label={`${branch.name}${branch.city ? `, ${branch.city}` : ""}`}
              onClick={() => {
                setBranchId(branch.id);
                setDoctorId(null);
                setSlotId(null);
              }}
            />
          ))}
        </Section>
      ) : null}

      {branchId && serviceId ? (
        <Section title={t("booking.doctor")}>
          <Choice
            active={doctorId === null}
            label={t("booking.anyDoctor")}
            onClick={() => {
              setDoctorId(null);
              setSlotId(null);
            }}
          />
          {doctors.data?.map((doctor) => (
            <Choice
              key={doctor.id}
              active={doctor.id === doctorId}
              label={`${doctor.full_name}${doctor.specialty ? ` — ${doctor.specialty}` : ""}`}
              onClick={() => {
                setDoctorId(doctor.id);
                setSlotId(null);
              }}
            />
          ))}
        </Section>
      ) : null}

      {serviceId && branchId ? (
        <Section title={t("booking.slot")}>
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
        </Section>
      ) : null}

      {error ? <p className="error">{error}</p> : null}

      <button
        className="button button--primary button--big"
        disabled={!slotId || book.isPending}
        onClick={() => slotId && book.mutate(slotId)}
        type="button"
      >
        {book.isPending ? t("common.loading") : t("booking.confirm")}
      </button>
    </div>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="section">
      <h3 className="section__title">{title}</h3>
      <div className="section__body">{children}</div>
    </section>
  );
}

function Choice({
  active,
  label,
  onClick,
}: {
  active: boolean;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      className={active ? "choice choice--active" : "choice"}
      onClick={onClick}
      type="button"
    >
      {label}
    </button>
  );
}
