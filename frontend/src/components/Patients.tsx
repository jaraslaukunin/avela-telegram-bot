import { useState } from "react";

import type { PatientOut } from "../api/types";
import { ageFromBirth } from "../format";
import { useT } from "../i18n/context";

/** Карточка пациента: аватар с инициалами, имя, возраст и признак взрослый/ребёнок. */
export function PatientCard({
  patient,
  selected = false,
  onSelect,
  onDelete,
}: {
  patient: PatientOut;
  selected?: boolean;
  onSelect?: () => void;
  onDelete?: () => void;
}) {
  const t = useT();
  const age = ageFromBirth(patient.birth_date);
  const isAdult = age === null || age >= 18;

  return (
    <div className={selected ? "patient patient--active" : "patient"}>
      <button className="patient__main" onClick={onSelect} type="button">
        <span className="patient__avatar">{initials(patient.full_name)}</span>
        <span className="patient__info">
          <span className="patient__name">{patient.full_name}</span>
          <span className="patient__meta">
            {patient.birth_date ?? "—"} ·{" "}
            {isAdult ? t("patients.adult") : t("patients.child")}
          </span>
        </span>
      </button>
      {onDelete ? (
        <button className="patient__delete" onClick={onDelete} type="button">
          {t("patients.delete")}
        </button>
      ) : null}
    </div>
  );
}

/** Форма добавления пациента: ФИО и дата рождения. */
export function AddPatientForm({
  onCreate,
  onCancel,
}: {
  onCreate: (fullName: string, birthDate: string) => void;
  onCancel: () => void;
}) {
  const t = useT();
  const [name, setName] = useState("");
  const [birth, setBirth] = useState("");

  return (
    <div className="patient-form card">
      <input
        className="input"
        onChange={(event) => setName(event.target.value)}
        placeholder={t("patients.name")}
        value={name}
      />
      <input
        className="input"
        onChange={(event) => setBirth(event.target.value)}
        type="date"
        value={birth}
      />
      <div className="card__actions">
        <button
          className="button button--primary"
          disabled={!name.trim()}
          onClick={() => onCreate(name.trim(), birth)}
          type="button"
        >
          {t("common.save")}
        </button>
        <button className="button button--secondary" onClick={onCancel} type="button">
          {t("common.cancel")}
        </button>
      </div>
    </div>
  );
}

function initials(fullName: string): string {
  const parts = fullName.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) {
    return "?";
  }
  if (parts.length === 1) {
    return parts[0].slice(0, 2).toUpperCase();
  }
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}
