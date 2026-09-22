import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { api } from "../api/client";
import type { OfferOut, SlotOut } from "../api/types";
import { AddPatientForm, PatientCard } from "../components/Patients";
import { Loading } from "../components/Loading";
import { SlotCalendar } from "../components/SlotCalendar";
import { formatDate, formatPrice, formatTime } from "../format";
import { useT } from "../i18n/context";
import { hapticImpact } from "../telegram";

type Step = "specialist" | "offers" | "slots" | "patient" | "summary";

const STEP_ORDER: Step[] = ["specialist", "offers", "slots", "patient", "summary"];

/**
 * Запись на приём: специалист → филиал и врач (с ценой и ближайшим временем)
 * → слоты → проверка записи.
 *
 * Бизнес-логики здесь нет: экран только собирает выбор и вызывает API.
 */
export default function BookingScreen() {
  const t = useT();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [step, setStep] = useState<Step>("specialist");
  const [city, setCity] = useState("");
  const [serviceName, setServiceName] = useState("");
  const [offer, setOffer] = useState<OfferOut | null>(null);
  const [slot, setSlot] = useState<SlotOut | null>(null);
  const [patientId, setPatientId] = useState("");
  const [error, setError] = useState("");

  const [addingPatient, setAddingPatient] = useState(false);

  const services = useQuery({
    queryKey: ["service-names"],
    queryFn: api.serviceNames,
    staleTime: 5 * 60_000,
  });

  const cities = useQuery({
    queryKey: ["cities"],
    queryFn: api.cities,
    staleTime: 10 * 60_000,
  });

  const offers = useQuery({
    queryKey: ["offers", serviceName, city],
    queryFn: () => api.offers({ serviceName, city: city || undefined }),
    enabled: Boolean(serviceName) && step !== "specialist",
    staleTime: 30_000,
  });

  const slots = useQuery({
    queryKey: ["slots", offer?.doctor_id, offer?.service_id],
    queryFn: () =>
      api.availableSlots({
        serviceId: offer?.service_id ?? "",
        doctorId: offer?.doctor_id,
      }),
    enabled: Boolean(offer) && (step === "slots" || step === "patient" || step === "summary"),
    staleTime: 10_000,
  });

  const patients = useQuery({
    queryKey: ["patients"],
    queryFn: api.myPatients,
    staleTime: 30_000,
  });

  const createPatient = useMutation({
    mutationFn: (payload: { full_name: string; birth_date?: string | null }) =>
      api.createPatient(payload),
    onSuccess: async (created) => {
      setAddingPatient(false);
      await queryClient.invalidateQueries({ queryKey: ["patients"] });
      setPatientId(created.id);
    },
    onError: (mutationError: unknown) =>
      setError(mutationError instanceof Error ? mutationError.message : t("common.error")),
  });

  const book = useMutation({
    mutationFn: () => api.book(slot?.id ?? "", patientId || undefined),
    onSuccess: () => {
      hapticImpact();
      navigate("/appointments", { state: { booked: true } });
    },
    onError: (mutationError: unknown) =>
      setError(mutationError instanceof Error ? mutationError.message : t("common.error")),
  });

  const selectedPatient = patients.data?.find((patient) => patient.id === patientId);

  return (
    <div className="screen">
      <h2>{t("booking.title")}</h2>
      <Steps step={step} />

      {step === "specialist" ? (
        <>
          <section className="card">
            <h3 className="section__title">{t("booking.city")}</h3>
            <div className="section__body">
              <button
                className={city === "" ? "choice choice--active" : "choice"}
                onClick={() => setCity("")}
                type="button"
              >
                {t("booking.allCities")}
              </button>
              {cities.data?.map((value) => (
                <button
                  key={value}
                  className={value === city ? "choice choice--active" : "choice"}
                  onClick={() => setCity(value)}
                  type="button"
                >
                  {value}
                </button>
              ))}
            </div>
          </section>

          <section className="card">
            <h3 className="section__title">{t("booking.specialist")}</h3>
            {services.isLoading ? <Loading /> : null}
            {services.data && services.data.length === 0 ? (
              <p className="muted">{t("admin.noServices")}</p>
            ) : null}
            <div className="section__body">
              {services.data?.map((service) => (
                <button
                  key={service.name}
                  className="choice choice--big"
                  onClick={() => {
                    setServiceName(service.name);
                    setStep("offers");
                  }}
                  type="button"
                >
                  {service.name}
                  <span className="choice__hint">
                    {service.duration_minutes} {t("booking.minutes")}
                  </span>
                </button>
              ))}
            </div>
          </section>
        </>
      ) : null}

      {step === "offers" ? (
        <>
          <button
            className="button button--secondary"
            onClick={() => setStep("specialist")}
            type="button"
          >
            {t("common.back")}
          </button>

          <p className="muted">
            {serviceName}
            {city ? ` · ${city}` : ""}
          </p>

          {offers.isLoading ? <Loading /> : null}
          {offers.data && offers.data.offers.length === 0 ? (
            <p className="muted">{t("booking.offersEmpty")}</p>
          ) : null}

          {offers.data?.offers.map((value) => (
            <article className="card" key={`${value.doctor_id}-${value.service_id}`}>
              <h3 className="card__title">{value.doctor_name}</h3>
              <p className="card__meta">
                {value.specialty} · {value.network_name}
              </p>
              <p className="card__meta">
                {value.branch_name}, {value.city}
                {value.address ? `, ${value.address}` : ""}
                {value.distance_km !== null ? ` · ${value.distance_km} ${t("booking.km")}` : ""}
              </p>
              <p className="card__time">
                {t("booking.price")}: {formatPrice(value.price)}
              </p>
              <p className="muted">
                {value.next_slot_at
                  ? `${t("booking.nextSlot")}: ${formatDate(value.next_slot_at)} ${formatTime(
                      value.next_slot_at,
                    )} · ${value.slots_count} ${t("booking.slotsCount")}`
                  : t("booking.noTime")}
              </p>
              <div className="card__actions">
                <button
                  className="button button--primary"
                  disabled={value.slots_count === 0}
                  onClick={() => {
                    setOffer(value);
                    setSlot(null);
                    setStep("slots");
                  }}
                  type="button"
                >
                  {t("booking.chooseTime")}
                </button>
              </div>
            </article>
          ))}
        </>
      ) : null}

      {step === "slots" ? (
        <>
          <button
            className="button button--secondary"
            onClick={() => setStep("offers")}
            type="button"
          >
            {t("common.back")}
          </button>

          {offer ? (
            <div className="card">
              <h3 className="card__title">{offer.doctor_name}</h3>
              <p className="card__meta">
                {offer.branch_name}, {offer.city}
              </p>
              <p className="card__time">
                {t("booking.price")}: {formatPrice(offer.price)}
              </p>
            </div>
          ) : null}

          {slots.isLoading ? <Loading /> : null}
          {slots.data && slots.data.length === 0 ? (
            <p className="muted">{t("booking.noSlots")}</p>
          ) : null}

          <SlotCalendar
            slots={slots.data ?? []}
            onPick={(value) => {
              setSlot(value);
              setStep("patient");
            }}
          />
        </>
      ) : null}

      {step === "patient" ? (
        <>
          <button
            className="button button--secondary"
            onClick={() => setStep("slots")}
            type="button"
          >
            {t("common.back")}
          </button>

          <h3 className="section__title">{t("booking.patientStep")}</h3>

          {patients.isLoading ? <Loading /> : null}

          <div className="patients">
            {patients.data?.map((patient) => (
              <PatientCard
                key={patient.id}
                patient={patient}
                selected={patient.id === patientId}
                onSelect={() => setPatientId(patient.id)}
              />
            ))}
          </div>

          {addingPatient ? (
            <AddPatientForm
              onCreate={(fullName, birthDate) =>
                createPatient.mutate({
                  full_name: fullName,
                  birth_date: birthDate || null,
                })
              }
              onCancel={() => setAddingPatient(false)}
            />
          ) : (
            <button
              className="button button--secondary"
              onClick={() => setAddingPatient(true)}
              type="button"
            >
              {t("booking.addPatient")}
            </button>
          )}

          {error ? <p className="error">{error}</p> : null}

          <button
            className="button button--primary button--big"
            disabled={!patientId}
            onClick={() => setStep("summary")}
            type="button"
          >
            {t("booking.continue")}
          </button>
        </>
      ) : null}

      {step === "summary" && offer && slot ? (
        <>
          <button
            className="button button--secondary"
            onClick={() => setStep("patient")}
            type="button"
          >
            {t("common.back")}
          </button>

          <section className="card">
            <h3 className="section__title">{t("booking.summary")}</h3>
            <p className="card__meta">
              {t("booking.who")}: {selectedPatient?.full_name ?? t("booking.choosePatient")}
            </p>
            <p className="card__meta">
              {t("booking.where")}: {offer.branch_name}, {offer.city}
              {offer.address ? `, ${offer.address}` : ""}
            </p>
            <p className="card__meta">
              {t("booking.whom")}: {offer.doctor_name} ({offer.specialty})
            </p>
            <p className="card__meta">
              {t("booking.howMuch")}: {formatPrice(offer.price)}
            </p>
            <p className="card__time">
              {t("booking.when")}: {formatDate(slot.starts_at)} {formatTime(slot.starts_at)}
            </p>
          </section>

          {error ? <p className="error">{error}</p> : null}

          <button
            className="button button--primary button--big"
            disabled={!patientId || book.isPending}
            onClick={() => book.mutate()}
            type="button"
          >
            {book.isPending ? t("common.loading") : t("booking.confirmBooking")}
          </button>
        </>
      ) : null}

      {error && step !== "summary" && step !== "patient" ? (
        <p className="error">{error}</p>
      ) : null}
    </div>
  );
}

function Steps({ step }: { step: Step }) {
  const t = useT();
  const activeIndex = STEP_ORDER.indexOf(step);

  return (
    <div className="steps">
      {STEP_ORDER.map((value, position) => (
        <span
          key={value}
          className={position <= activeIndex ? "steps__item steps__item--active" : "steps__item"}
        >
          {t(`booking.step.${value}`)}
        </span>
      ))}
    </div>
  );
}
