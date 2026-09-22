-- Вторая версия модели записи: пациенты, цены, координаты филиалов.
--
-- Ключевое изменение бизнес-правила: пересечения записей теперь считаются
-- на уровне КОНКРЕТНОГО пациента, а не аккаунта. Один Telegram-аккаунт
-- может вести нескольких пациентов (например, мама и двое детей), и их
-- приёмы могут пересекаться по времени.

create table patients (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references users(id) on delete cascade,
    full_name text not null check (char_length(full_name) between 1 and 300),
    birth_date date,
    created_at timestamptz not null default now()
);

alter table patients enable row level security;

-- Филиал: координаты для поиска ближайшего.
alter table branches
    add column latitude double precision,
    add column longitude double precision;

-- Цена приёма — на связке «врач + услуга» (филиал определяется врачом).
alter table doctor_services add column price numeric(10, 2);

-- Слот хранит СНИМОК цены на момент генерации: цена могла измениться,
-- а запись должна помнить, сколько стоил приём на момент брони.
alter table slots add column price numeric(10, 2);

-- Запись ссылается на конкретного пациента.
alter table appointments
    add column patient_profile_id uuid references patients(id) on delete restrict;

-- Бэкфилл: каждому пользователю — пациент «по умолчанию», старые записи — к нему.
insert into patients (user_id, full_name)
select id,
       coalesce(
           nullif(
               trim(concat_ws(' ', nullif(first_name, ''), nullif(last_name, ''))),
               ''
           ),
           'Пациент'
       )
from users
where not exists (select 1 from patients p where p.user_id = users.id);

update appointments a
set patient_profile_id = (
    select p.id from patients p where p.user_id = a.patient_id limit 1
)
where a.patient_profile_id is null;

-- Пересечения активных записей — по конкретному пациенту.
create or replace function check_patient_overlap() returns trigger as $$
declare
    conflict_id uuid;
begin
    select a.id into conflict_id
    from appointments a
    join slots existing_slot on existing_slot.id = a.slot_id
    join slots new_slot on new_slot.id = new.slot_id
    where a.status = 'active'
      and a.patient_profile_id = new.patient_profile_id
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
