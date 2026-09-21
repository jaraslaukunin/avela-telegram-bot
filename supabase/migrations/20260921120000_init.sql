-- Avela: начальная схема (multi-tenant).
-- Все временные метки — UTC (timestamptz). Часовой пояс — у филиала (branches.timezone, IANA).
-- Доступ к данным — только через backend; RLS включён с политикой deny-by-default.

create extension if not exists btree_gist;

create table networks (
    id uuid primary key default gen_random_uuid(),
    slug text not null unique,
    name text not null,
    is_active boolean not null default true,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table branches (
    id uuid primary key default gen_random_uuid(),
    network_id uuid not null references networks(id) on delete cascade,
    name text not null,
    city text not null default '',
    region text not null default '',
    address text not null default '',
    phone text not null default '',
    timezone text not null default 'Europe/Moscow',
    is_active boolean not null default true,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (network_id, name)
);

create table users (
    id uuid primary key default gen_random_uuid(),
    telegram_id bigint not null unique,
    role text not null default 'patient'
        check (role in ('patient', 'branch_admin', 'network_admin', 'avela_admin')),
    first_name text not null default '',
    last_name text not null default '',
    username text,
    phone text,
    language_code text,
    network_id uuid references networks(id) on delete set null,
    is_active boolean not null default true,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    check (role <> 'network_admin' or network_id is not null)
);

-- Администраторы филиалов: связь многие-ко-многим с филиалами.
create table branch_admins (
    user_id uuid not null references users(id) on delete cascade,
    branch_id uuid not null references branches(id) on delete cascade,
    primary key (user_id, branch_id)
);

create table doctors (
    id uuid primary key default gen_random_uuid(),
    branch_id uuid not null references branches(id) on delete cascade,
    full_name text not null,
    specialty text not null default '',
    photo_path text,
    is_active boolean not null default true,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table services (
    id uuid primary key default gen_random_uuid(),
    network_id uuid not null references networks(id) on delete cascade,
    name text not null,
    duration_minutes integer not null check (duration_minutes > 0),
    is_active boolean not null default true,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (network_id, name)
);

create table doctor_services (
    doctor_id uuid not null references doctors(id) on delete cascade,
    service_id uuid not null references services(id) on delete cascade,
    primary key (doctor_id, service_id)
);

-- Регулярные шаблоны графика врача. Время — локальное время филиала.
create table schedule_templates (
    id uuid primary key default gen_random_uuid(),
    doctor_id uuid not null references doctors(id) on delete cascade,
    service_id uuid not null references services(id) on delete cascade,
    weekday integer not null check (weekday between 0 and 6),
    start_time time not null,
    end_time time not null,
    valid_from date not null,
    valid_until date,
    is_active boolean not null default true,
    created_at timestamptz not null default now(),
    check (start_time < end_time)
);

-- Слоты: врач + услуга + интервал. Пересечения у одного врача запрещены на уровне БД.
create table slots (
    id uuid primary key default gen_random_uuid(),
    doctor_id uuid not null references doctors(id) on delete cascade,
    service_id uuid not null references services(id) on delete restrict,
    starts_at timestamptz not null,
    ends_at timestamptz not null,
    created_at timestamptz not null default now(),
    check (ends_at > starts_at),
    exclude using gist (
        doctor_id with =,
        tstzrange(starts_at, ends_at) with &&
    )
);

create table appointments (
    id uuid primary key default gen_random_uuid(),
    patient_id uuid not null references users(id) on delete restrict,
    slot_id uuid not null references slots(id) on delete restrict,
    status text not null default 'active'
        check (status in ('active', 'cancelled', 'completed', 'rescheduled')),
    patient_full_name text,
    rescheduled_from_id uuid references appointments(id),
    cancelled_by text check (cancelled_by in ('patient', 'admin')),
    cancelled_at timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

-- Один слот — максимум одна активная запись.
create unique index appointments_one_active_per_slot
    on appointments (slot_id) where status = 'active';

-- Запрет пересекающихся активных записей одного пациента
-- (даже у разных врачей, в разных филиалах и сетях).
create or replace function check_patient_overlap() returns trigger as $$
declare
    conflict_id uuid;
begin
    if new.status <> 'active' then
        return new;
    end if;

    select a.id into conflict_id
    from appointments a
    join slots existing_slot on existing_slot.id = a.slot_id
    join slots new_slot on new_slot.id = new.slot_id
    where a.patient_id = new.patient_id
      and a.status = 'active'
      and a.id is distinct from new.id
      and tstzrange(existing_slot.starts_at, existing_slot.ends_at)
          && tstzrange(new_slot.starts_at, new_slot.ends_at)
    limit 1;

    if conflict_id is not null then
        raise exception 'patient_already_has_overlapping_appointment'
            using errcode = '23505';
    end if;

    return new;
end;
$$ language plpgsql;

create trigger trg_check_patient_overlap
    before insert or update on appointments
    for each row execute function check_patient_overlap();

create table audit_logs (
    id bigint generated always as identity primary key,
    actor_user_id uuid references users(id) on delete set null,
    action text not null,
    entity_type text,
    entity_id uuid,
    network_id uuid,
    details jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

-- Уведомления в Telegram: очередь для worker'а.
-- Уникальность (appointment_id, kind) — дедупликация на уровне БД.
create table notifications (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references users(id) on delete cascade,
    appointment_id uuid references appointments(id) on delete set null,
    kind text not null check (
        kind in ('booking_created', 'reminder_24h', 'reminder_2h', 'cancelled', 'rescheduled')
    ),
    scheduled_for timestamptz,
    sent_at timestamptz,
    status text not null default 'pending'
        check (status in ('pending', 'sent', 'skipped', 'failed')),
    error text,
    created_at timestamptz not null default now(),
    unique (appointment_id, kind)
);

-- RLS: включён на всех таблицах, политики не создаются намеренно (deny-by-default).
-- Backend ходит в БД как владелец схемы (asyncpg) и обходит RLS;
-- прямой доступ через Supabase API (anon/authenticated) не видит ничего.
alter table networks enable row level security;
alter table branches enable row level security;
alter table users enable row level security;
alter table branch_admins enable row level security;
alter table doctors enable row level security;
alter table services enable row level security;
alter table doctor_services enable row level security;
alter table schedule_templates enable row level security;
alter table slots enable row level security;
alter table appointments enable row level security;
alter table notifications enable row level security;
alter table audit_logs enable row level security;
