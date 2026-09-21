import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, API_URL, api, slotQuery } from "./client";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("api client", () => {
  it("строит запрос свободных слотов с фильтрами", () => {
    const query = slotQuery({ serviceId: "svc-1", branchId: "br-1" });

    expect(query).toBe("/slots/available?service_id=svc-1&branch_id=br-1");
  });

  it("без фильтров оставляет только услугу", () => {
    expect(slotQuery({ serviceId: "svc-1" })).toBe("/slots/available?service_id=svc-1");
  });

  it("обращается к API_URL и прокидывает detail ошибки", async () => {
    const calls: string[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, options?: RequestInit) => {
        calls.push(`${options?.method ?? "GET"} ${url}`);
        return new Response(JSON.stringify({ detail: "Слот уже занят" }), {
          status: 409,
          headers: { "Content-Type": "application/json" },
        });
      }),
    );

    await expect(api.book("slot-1")).rejects.toBeInstanceOf(ApiError);
    await expect(api.book("slot-1")).rejects.toThrow("Слот уже занят");
    expect(calls[0]).toBe(`POST ${API_URL}/appointments`);
  });
});
