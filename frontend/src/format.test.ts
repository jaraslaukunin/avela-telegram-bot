import { describe, expect, it } from "vitest";

import { formatDate, formatDateTime, formatTime, isCancellable } from "./format";

describe("format", () => {
  it("форматирует дату в таймзоне филиала", () => {
    const value = formatDate("2026-09-25T12:00:00+00:00", "Europe/Moscow");

    expect(value).toContain("25");
  });

  it("formatDateTime и formatTime не пустые", () => {
    expect(formatDateTime("2026-09-25T12:00:00+00:00", "Europe/Moscow")).toBeTruthy();
    expect(formatTime("2026-09-25T12:00:00+00:00", "Europe/Moscow")).toBeTruthy();
  });

  it("кривая таймзона не ломает форматирование", () => {
    expect(formatDateTime("2026-09-25T12:00:00+00:00", "Марс/Олимп")).toBeTruthy();
  });

  it("isCancellable учитывает дедлайн", () => {
    const now = new Date("2026-09-25T10:00:00Z");

    expect(isCancellable("2026-09-25T11:00:00Z", now)).toBe(true);
    expect(isCancellable("2026-09-25T09:00:00Z", now)).toBe(false);
  });
});
