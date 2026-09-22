/** Типы ответов backend API Avela. */

export interface UserOut {
  id: string;
  telegram_id: number;
  role: string;
  first_name: string;
  last_name: string;
  username: string | null;
  phone: string | null;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: UserOut;
}

export interface NetworkOut {
  id: string;
  slug: string;
  name: string;
}

export interface BranchOut {
  id: string;
  network_id: string;
  name: string;
  city: string;
  region: string;
  address: string;
  phone: string;
  timezone: string;
}

export interface ServiceOut {
  id: string;
  network_id: string;
  name: string;
  duration_minutes: number;
}

export interface DoctorOut {
  id: string;
  branch_id: string;
  full_name: string;
  specialty: string;
  photo_path: string | null;
}

/** Врач в админке: с признаком активности и списком услуг. */
export interface AdminDoctorOut extends DoctorOut {
  is_active: boolean;
  service_ids: string[];
}

export interface SlotOut {
  id: string;
  doctor_id: string;
  service_id: string;
  starts_at: string;
  ends_at: string;
}

export interface AppointmentOut {
  id: string;
  status: string;
  slot_id: string;
  doctor_id: string;
  service_id: string;
  starts_at: string;
  ends_at: string;
  doctor_name: string;
  service_name: string;
  branch_name: string;
  branch_address: string;
  branch_phone: string;
  branch_timezone: string;
  cancellable_until: string;
}

export interface AnonymizationOut {
  anonymized: boolean;
  cancelled_appointments: number;
  skipped_notifications: number;
}

export interface ServiceNameOut {
  name: string;
  duration_minutes: number;
  networks_count: number;
}

export interface OfferOut {
  doctor_id: string;
  doctor_name: string;
  specialty: string;
  service_id: string;
  branch_id: string;
  branch_name: string;
  city: string;
  address: string;
  network_name: string;
  price: string | null;
  next_slot_at: string | null;
  slots_count: number;
  distance_km: number | null;
}

export interface OffersResponse {
  service_name: string;
  offers: OfferOut[];
}

export interface PatientOut {
  id: string;
  full_name: string;
  birth_date: string | null;
}

// --- Админ-панель ---

export interface AdminScopeOut {
  role: string;
  can_access_all: boolean;
  network_ids: string[];
  branch_ids: string[];
}

export interface AdminAppointmentOut {
  id: string;
  status: string;
  patient_telegram_id: number;
  patient_name: string;
  doctor_name: string;
  branch_id: string;
  branch_name: string;
  branch_timezone: string;
  doctor_id: string;
  service_id: string;
  starts_at: string;
  ends_at: string;
  cancelled_by: string | null;
}

export interface ScheduleTemplateOut {
  id: string;
  doctor_id: string;
  service_id: string;
  weekday: number;
  start_time: string;
  end_time: string;
  valid_from: string;
  valid_until: string | null;
  is_active: boolean;
}

export interface SlotGenerationResult {
  created: number;
  skipped: number;
}
