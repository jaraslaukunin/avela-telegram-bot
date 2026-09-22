import { useState } from "react";

import type { SlotOut } from "../api/types";
import { formatTime } from "../format";
import { useT } from "../i18n/context";

function dayKey(iso: string): string {
  const date = new Date(iso);
  const month = `${date.getMonth() + 1}`.padStart(2, "0");
  const day = `${date.getDate()}`.padStart(2, "0");
  return `${date.getFullYear()}-${month}-${day}`;
}

/**
 * Календарь доступности для пациента: зелёный день — есть свободное время,
 * серый — свободного времени нет. Выбор слота — внутри выбранного дня.
 */
export function SlotCalendar({
  slots,
  onPick,
}: {
  slots: SlotOut[];
  onPick: (slot: SlotOut) => void;
}) {
  const t = useT();
  const [monthOffset, setMonthOffset] = useState(0);
  const [selectedDay, setSelectedDay] = useState<string | null>(null);

  const byDay = new Map<string, SlotOut[]>();
  for (const slot of slots) {
    const key = dayKey(slot.starts_at);
    const list = byDay.get(key);
    if (list) {
      list.push(slot);
    } else {
      byDay.set(key, [slot]);
    }
  }

  const first = new Date();
  first.setDate(1);
  first.setMonth(first.getMonth() + monthOffset);
  const daysInMonth = new Date(first.getFullYear(), first.getMonth() + 1, 0).getDate();
  const leading = (first.getDay() + 6) % 7;

  const monthLabel = first.toLocaleDateString("ru-RU", {
    month: "long",
    year: "numeric",
  });

  const cells: (string | null)[] = [
    ...Array.from({ length: leading }, () => null),
    ...Array.from({ length: daysInMonth }, (_value, index) => {
      const date = new Date(first.getFullYear(), first.getMonth(), index + 1);
      const month = `${date.getMonth() + 1}`.padStart(2, "0");
      const day = `${date.getDate()}`.padStart(2, "0");
      return `${date.getFullYear()}-${month}-${day}`;
    }),
  ];

  const selectedSlots = selectedDay ? byDay.get(selectedDay) ?? [] : [];

  return (
    <section className="card calendar">
      <div className="calendar__head">
        <button
          className="button button--secondary calendar__nav"
          onClick={() => {
            setMonthOffset(monthOffset - 1);
            setSelectedDay(null);
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
            setSelectedDay(null);
          }}
          type="button"
        >
          ›
        </button>
      </div>

      <div className="calendar__weekdays">
        {[0, 1, 2, 3, 4, 5, 6].map((day) => (
          <span key={day} className="calendar__weekday">
            {t(`weekday.${day}`).slice(0, 2)}
          </span>
        ))}
      </div>

      <div className="calendar__grid">
        {cells.map((key, index) => {
          if (key === null) {
            return <span key={`pad-${index}`} className="calendar__pad" />;
          }
          const hasSlots = byDay.has(key);
          const className = [
            "calendar__day",
            hasSlots ? "calendar__day--free" : "calendar__day--none",
            selectedDay === key ? "calendar__day--selected" : "",
          ]
            .filter(Boolean)
            .join(" ");
          return (
            <button
              key={key}
              className={className}
              disabled={!hasSlots}
              onClick={() => setSelectedDay(key)}
              type="button"
            >
              {Number(key.slice(-2))}
            </button>
          );
        })}
      </div>

      <div className="calendar__legend">
        <span className="calendar__legend-item">
          <span className="calendar__dot calendar__dot--free" />
          {t("booking.dayFree")}
        </span>
        <span className="calendar__legend-item">
          <span className="calendar__dot calendar__dot--none" />
          {t("booking.dayNone")}
        </span>
      </div>

      {selectedDay ? (
        selectedSlots.length > 0 ? (
          <div className="slots">
            {selectedSlots.map((slot) => (
              <button
                key={slot.id}
                className="slot"
                onClick={() => onPick(slot)}
                type="button"
              >
                <span className="slot__date">{t("booking.chooseTime")}</span>
                <span className="slot__time">{formatTime(slot.starts_at)}</span>
              </button>
            ))}
          </div>
        ) : (
          <p className="muted">{t("booking.dayNoSlots")}</p>
        )
      ) : (
        <p className="muted">{t("booking.chooseDay")}</p>
      )}
    </section>
  );
}
