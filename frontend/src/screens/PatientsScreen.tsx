import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "../api/client";
import { AddPatientForm, PatientCard } from "../components/Patients";
import { useT } from "../i18n/context";

/** Пациенты аккаунта: список, добавление, удаление. */
export default function PatientsScreen() {
  const t = useT();
  const queryClient = useQueryClient();
  const [adding, setAdding] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [error, setError] = useState("");

  const patients = useQuery({
    queryKey: ["patients"],
    queryFn: api.myPatients,
    staleTime: 30_000,
  });

  const createPatient = useMutation({
    mutationFn: (payload: { full_name: string; birth_date?: string | null }) =>
      api.createPatient(payload),
    onSuccess: async () => {
      setAdding(false);
      setError("");
      await queryClient.invalidateQueries({ queryKey: ["patients"] });
    },
    onError: (mutationError: unknown) =>
      setError(mutationError instanceof Error ? mutationError.message : t("common.error")),
  });

  const deletePatient = useMutation({
    mutationFn: (patientId: string) => api.deletePatient(patientId),
    onSuccess: async () => {
      setDeletingId(null);
      setError("");
      await queryClient.invalidateQueries({ queryKey: ["patients"] });
    },
    onError: (mutationError: unknown) =>
      setError(mutationError instanceof Error ? mutationError.message : t("common.error")),
  });

  return (
    <div className="screen">
      <h2>{t("patients.title")}</h2>

      {patients.isLoading ? <p className="muted">{t("common.loading")}</p> : null}
      {patients.data && patients.data.length === 0 && !adding ? (
        <p className="muted">{t("patients.empty")}</p>
      ) : null}
      {error ? <p className="error">{error}</p> : null}

      <div className="patients">
        {patients.data?.map((patient) => (
          <PatientCard
            key={patient.id}
            patient={patient}
            onDelete={() =>
              setDeletingId(deletingId === patient.id ? null : patient.id)
            }
          />
        ))}
      </div>

      {deletingId ? (
        <div className="card">
          <p className="muted">{t("patients.deleteConfirm")}</p>
          <div className="card__actions">
            <button
              className="button button--danger"
              disabled={deletePatient.isPending}
              onClick={() => deletePatient.mutate(deletingId)}
              type="button"
            >
              {t("patients.delete")}
            </button>
            <button
              className="button button--secondary"
              onClick={() => setDeletingId(null)}
              type="button"
            >
              {t("common.cancel")}
            </button>
          </div>
        </div>
      ) : null}

      {adding ? (
        <AddPatientForm
          onCreate={(fullName, birthDate) =>
            createPatient.mutate({
              full_name: fullName,
              birth_date: birthDate || null,
            })
          }
          onCancel={() => setAdding(false)}
        />
      ) : (
        <button
          className="button button--primary button--big"
          onClick={() => setAdding(true)}
          type="button"
        >
          {t("patients.add")}
        </button>
      )}
    </div>
  );
}
