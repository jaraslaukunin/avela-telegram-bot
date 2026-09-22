import { getInitData } from "../telegram";
import type {
  AdminAppointmentOut,
  AdminDoctorOut,
  AdminScopeOut,
  AnonymizationOut,
  AppointmentOut,
  BranchOut,
  DoctorOut,
  LoginResponse,
  NetworkOut,
  OffersResponse,
  PatientOut,
  ScheduleTemplateOut,
  ServiceNameOut,
  ServiceOut,
  SlotGenerationResult,
  SlotOut,
  UserOut,
} from "./types";

export const API_URL: string =
  (import.meta.env.VITE_API_URL as string | undefined) ?? "http://127.0.0.1:8000";

const TOKEN_KEY = "avela_token";

let accessToken: string | null = null;

export function setAccessToken(token: string | null): void {
  accessToken = token;
  try {
    if (token) {
      sessionStorage.setItem(TOKEN_KEY, token);
    } else {
      sessionStorage.removeItem(TOKEN_KEY);
    }
  } catch {
    // Приватный режим или запрет storage — некритично, работаем из памяти.
  }
}

export function getAccessToken(): string | null {
  return accessToken;
}

function getStoredToken(): string | null {
  try {
    return sessionStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

/** Пользователь открыл Mini App не из Telegram — initData отсутствует. */
export class NotInTelegramError extends ApiError {
  constructor() {
    super(401, "Откройте приложение через Telegram");
    this.name = "NotInTelegramError";
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
    throw new NotInTelegramError();
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

export function offersQuery(params: {
  serviceName: string;
  city?: string;
  latitude?: number;
  longitude?: number;
}): string {
  const query = new URLSearchParams({ service_name: params.serviceName });
  if (params.city) {
    query.set("city", params.city);
  }
  if (params.latitude !== undefined) {
    query.set("latitude", String(params.latitude));
  }
  if (params.longitude !== undefined) {
    query.set("longitude", String(params.longitude));
  }
  return `/catalog/offers?${query.toString()}`;
}

export const api = {
  me: () => request<UserOut>("/auth/me"),

  serviceNames: () => request<ServiceNameOut[]>("/catalog/services"),
  cities: () => request<string[]>("/catalog/cities"),
  offers: (params: {
    serviceName: string;
    city?: string;
    latitude?: number;
    longitude?: number;
  }) => request<OffersResponse>(offersQuery(params)),

  myPatients: () => request<PatientOut[]>("/patients"),
  createPatient: (payload: { full_name: string; birth_date?: string | null }) =>
    request<PatientOut>("/patients", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  networks: () => request<NetworkOut[]>("/networks"),
  branches: (networkId: string) => request<BranchOut[]>(`/networks/${networkId}/branches`),
  services: (networkId: string) => request<ServiceOut[]>(`/services?network_id=${networkId}`),
  doctors: (branchId: string, serviceId: string) =>
    request<DoctorOut[]>(`/branches/${branchId}/doctors?service_id=${serviceId}`),
  availableSlots: (params: { serviceId: string; branchId?: string; doctorId?: string }) =>
    request<SlotOut[]>(slotQuery(params)),

  myAppointments: () => request<AppointmentOut[]>("/appointments"),
  book: (slotId: string, patientId?: string) =>
    request<AppointmentOut>("/appointments", {
      method: "POST",
      body: JSON.stringify(
        patientId ? { slot_id: slotId, patient_id: patientId } : { slot_id: slotId },
      ),
    }),
  cancel: (appointmentId: string) =>
    request<AppointmentOut>(`/appointments/${appointmentId}/cancel`, { method: "POST" }),
  reschedule: (appointmentId: string, newSlotId: string) =>
    request<AppointmentOut>(`/appointments/${appointmentId}/reschedule`, {
      method: "POST",
      body: JSON.stringify({ new_slot_id: newSlotId }),
    }),

  deleteMe: () => request<AnonymizationOut>("/privacy/delete-me", { method: "POST" }),

  // --- Админ-панель ---
  adminScope: () => request<AdminScopeOut>("/admin/scope"),
  adminBranches: (networkId?: string) =>
    request<BranchOut[]>(
      networkId ? `/admin/branches?network_id=${networkId}` : "/admin/branches",
    ),
  adminServices: (networkId?: string) =>
    request<ServiceOut[]>(
      networkId ? `/admin/services?network_id=${networkId}` : "/admin/services",
    ),
  adminAppointments: (branchId?: string) =>
    request<AdminAppointmentOut[]>(
      branchId ? `/admin/appointments?branch_id=${branchId}` : "/admin/appointments",
    ),
  adminCancelAppointment: (appointmentId: string) =>
    request<AdminAppointmentOut>(`/admin/appointments/${appointmentId}/cancel`, {
      method: "POST",
    }),

  adminDoctors: (branchId: string) =>
    request<AdminDoctorOut[]>(`/admin/branches/${branchId}/doctors`),
  adminCreateDoctor: (
    branchId: string,
    body: { full_name: string; specialty: string; service_ids: string[] },
  ) =>
    request<AdminDoctorOut>(`/admin/branches/${branchId}/doctors`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  adminUpdateDoctor: (
    doctorId: string,
    body: { full_name?: string; specialty?: string; is_active?: boolean },
  ) =>
    request<AdminDoctorOut>(`/admin/doctors/${doctorId}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  adminSetDoctorServices: (doctorId: string, serviceIds: string[]) =>
    request<ServiceOut[]>(`/admin/doctors/${doctorId}/services`, {
      method: "PUT",
      body: JSON.stringify({ service_ids: serviceIds }),
    }),

  adminScheduleTemplates: (doctorId: string) =>
    request<ScheduleTemplateOut[]>(`/admin/schedule-templates?doctor_id=${doctorId}`),
  adminCreateTemplate: (
    doctorId: string,
    body: {
      service_id: string;
      weekday: number;
      start_time: string;
      end_time: string;
      valid_from: string;
      valid_until: string | null;
    },
  ) =>
    request<ScheduleTemplateOut>(`/admin/doctors/${doctorId}/schedule-templates`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  adminGenerateSlots: (templateId: string, fromDate: string, toDate: string) =>
    request<SlotGenerationResult>(`/admin/schedule-templates/${templateId}/generate-slots`, {
      method: "POST",
      body: JSON.stringify({ from_date: fromDate, to_date: toDate }),
    }),
};

/**
 * Восстанавливает сессию из sessionStorage, если токен ещё жив.
 *
 * Экономит два сетевых круга (auth/telegram + проверка) при повторном
 * открытии Mini App — а каждый круг до API заметен на мобильной сети.
 */
export async function restoreOrLogin(): Promise<UserOut> {
  const stored = getStoredToken();
  if (stored) {
    setAccessToken(stored);
    try {
      return await api.me();
    } catch {
      setAccessToken(null);
    }
  }

  const data = await login();
  return data.user;
}
