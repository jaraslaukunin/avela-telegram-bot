import { getInitData } from "../telegram";
import type {
  AnonymizationOut,
  AppointmentOut,
  BranchOut,
  DoctorOut,
  LoginResponse,
  NetworkOut,
  ServiceOut,
  SlotOut,
  UserOut,
} from "./types";

export const API_URL: string =
  (import.meta.env.VITE_API_URL as string | undefined) ?? "http://127.0.0.1:8000";

let accessToken: string | null = null;

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

export function getAccessToken(): string | null {
  return accessToken;
}

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Accept", "application/json");
  if (options.body) {
    headers.set("Content-Type", "application/json");
  }
  if (accessToken) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }

  const response = await fetch(`${API_URL}${path}`, { ...options, headers });

  if (!response.ok) {
    let detail = `Ошибка ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: unknown };
      if (body?.detail) {
        detail = String(body.detail);
      }
    } catch {
      // тело не JSON — оставляем общий текст
    }
    throw new ApiError(response.status, detail);
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export async function login(): Promise<LoginResponse> {
  const initData = getInitData();
  if (!initData) {
    throw new ApiError(401, "Откройте приложение через Telegram");
  }

  const data = await request<LoginResponse>("/auth/telegram", {
    method: "POST",
    body: JSON.stringify({ init_data: initData }),
  });
  setAccessToken(data.access_token);
  return data;
}

export function slotQuery(params: {
  serviceId: string;
  branchId?: string;
  doctorId?: string;
  from?: string;
  to?: string;
}): string {
  const query = new URLSearchParams({ service_id: params.serviceId });
  if (params.branchId) {
    query.set("branch_id", params.branchId);
  }
  if (params.doctorId) {
    query.set("doctor_id", params.doctorId);
  }
  if (params.from) {
    query.set("from", params.from);
  }
  if (params.to) {
    query.set("to", params.to);
  }
  return `/slots/available?${query.toString()}`;
}

export const api = {
  me: () => request<UserOut>("/auth/me"),

  networks: () => request<NetworkOut[]>("/networks"),
  branches: (networkId: string) => request<BranchOut[]>(`/networks/${networkId}/branches`),
  services: (networkId: string) => request<ServiceOut[]>(`/services?network_id=${networkId}`),
  doctors: (branchId: string, serviceId: string) =>
    request<DoctorOut[]>(`/branches/${branchId}/doctors?service_id=${serviceId}`),
  availableSlots: (params: { serviceId: string; branchId?: string; doctorId?: string }) =>
    request<SlotOut[]>(slotQuery(params)),

  myAppointments: () => request<AppointmentOut[]>("/appointments"),
  book: (slotId: string) =>
    request<AppointmentOut>("/appointments", {
      method: "POST",
      body: JSON.stringify({ slot_id: slotId }),
    }),
  cancel: (appointmentId: string) =>
    request<AppointmentOut>(`/appointments/${appointmentId}/cancel`, { method: "POST" }),
  reschedule: (appointmentId: string, newSlotId: string) =>
    request<AppointmentOut>(`/appointments/${appointmentId}/reschedule`, {
      method: "POST",
      body: JSON.stringify({ new_slot_id: newSlotId }),
    }),

  deleteMe: () => request<AnonymizationOut>("/privacy/delete-me", { method: "POST" }),
};
