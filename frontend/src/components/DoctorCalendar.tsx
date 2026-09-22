import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "../api/client";
import type { CalendarDayOut } from "../api/types";
import { useT } from "../i18n/context";

const WEEKDAYS = [0, 1, 2, 3, 4, 5, 6];

function isoDate(date: Date): string {
  return date.toISOString().slice(0, 10);
}

/**
 * Календарь врача: зелёный — есть свободные слоты, красный — всё занято,
 * серый — график не сформирован или дата прошла.
 */
export function DoctorCalendar({ doctorId }: { doctorId: string }) {
  const t = useT();
  const [monthOffset, setMonthOffset] = useState(0);
  const [selected, setSelected] = useState<CalendarDayOut | null>(null);

  const first = new Date();
  first.setDate(1);
  first.setMonth(first.getMonth() + monthOffset);
  const last = new Date(first.getFullYear(), first.getMonth() + 1, 0);

  const start = isoDate(first);
  const end = isoDate(last);

  const calendar = useQuery({
    queryKey: ["doctor-calendar", doctorId, start, end],
    queryFn: () => api.adminDoctorCalendar(doctorId, start, end),
    enabled: Boolean(doctorId),
    staleTime: 30_000,
  });

  const days = calendar.data?.days ?? [];
  const leading = (first.getDay() + 6) % 7; // понедельник — первый столбец
  const monthLabel = first.toLocaleDateString("ru-RU", {
    month: "long",
    year: "numeric",
  });

  const stateText = (day: CalendarDayOut): string => {
    if (day.state === "free") {
      return `${t("admin.stateFree")}: ${day.free_slots}/${day.total_slots}`;
    }
    if (day.state === "booked") {
      return t("admin.stateBooked");
    }
    return t("admin.stateNone");
  };

  return (
    <section className="calendar card">
      <div className="calendar__head">
        <button
          className="button button--secondary calendar__nav"
          onClick={() => {
            setMonthOffset(monthOffset - 1);
            setSelected(null);
          }}
          type="button"
        >
          ‹
        </button>
        <span className="calendar__month">{monthLabel}</span>
        <button
          className="button button--secondary calendar__nav"
          onClick={() => {
            setMonthOffset(monthOffset + 1);
            setSelected(null);
          }}
          type="button"
        >
          ›
        </button>
      </div>

      <div className="calendar__weekdays">
        {WEEKDAYS.map((day) => (
          <span key={day} className="calendar__weekday">
            {t(`weekday.${day}`).slice(0, 2)}
          </span>
        ))}
      </div>

      <div className="calendar__grid">
        {Array.from({ length: leading }, (_value, index) => (
          <span key={`pad-${index}`} className="calendar__pad" />
        ))}
        {days.map((day) => (
          <button
            key={day.date}
            className={`calendar__day calendar__day--${day.state}${
              selected?.date === day.date ? " calendar__day--selected" : ""
            }`}
            onClick={() => setSelected(day)}
            type="button"
          >
            {Number(day.date.slice(-2))}
          </button>
        ))}
      </div>

      {calendar.isLoading ? <p className="muted">{t("common.loading")}</p> : null}

      <div className="calendar__legend">
        <span className="calendar__legend-item">
          <span className="calendar__dot calendar__dot--free" />
          {t("admin.stateFree")}
        </span>
        <span className="calendar__legend-item">
          <span className="calendar__dot calendar__dot--booked" />
          {t("admin.stateBooked")}
        </span>
        <span className="calendar__legend-item">
          <span className="calendar__dot calendar__dot--none" />
          {t("admin.stateNone")}
        </span>
      </div>

      {selected ? (
        <p className="muted">
          {selected.date}: {stateText(selected)}
        </p>
      ) : null}
    </section>
  );
}
