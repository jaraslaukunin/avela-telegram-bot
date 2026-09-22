-- Фикс триггера пересечений записей пациента.
--
-- Проблема: в production-БД осталась старая версия функции — она проверяла
-- пересечения даже для отменяемых записей (UPDATE при отмене падал
-- с UniqueViolationError 'patient_already_has_overlapping_appointment')
-- и сравнивала по patient_id (аккаунту), а не по пациенту.
--
-- Теперь: проверка выполняется ТОЛЬКО для active-записей, пересечения
-- считаются по конкретному пациенту (patient_profile_id).
create or replace function check_patient_overlap() returns trigger as $$
declare
    conflict_id uuid;
begin
    -- Отмена, перенос и завершение не блокируются правилом пересечений.
    if new.status <> 'active' then
        return new;
    end if;

    select a.id into conflict_id
    from appointments a
    join slots existing_slot on existing_slot.id = a.slot_id
    join slots new_slot on new_slot.id = new.slot_id
    where a.patient_profile_id = new.patient_profile_id
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

drop trigger if exists trg_check_patient_overlap on appointments;
create trigger trg_check_patient_overlap
    before insert or update on appointments
    for each row execute function check_patient_overlap();
