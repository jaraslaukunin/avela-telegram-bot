-- Heartbeat фоновых сервисов (worker) для публичной status page.
create table service_heartbeats (
    name text primary key,
    updated_at timestamptz not null default now()
);

alter table service_heartbeats enable row level security;
