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
