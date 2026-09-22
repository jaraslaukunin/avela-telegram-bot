import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { api } from "../../api/client";
import { useT } from "../../i18n/context";
import { useAdminScope } from "./useAdminScope";

function toggleId(list: string[], id: string): string[] {
  return list.includes(id) ? list.filter((item) => item !== id) : [...list, id];
}

export default function AdminDoctorsScreen() {
  const t = useT();
  const queryClient = useQueryClient();
  const scope = useAdminScope();

  const [branchId, setBranchId] = useState("");
  const [name, setName] = useState("");
  const [specialty, setSpecialty] = useState("");
  const [selectedServices, setSelectedServices] = useState<string[]>([]);
  const [editingDoctorId, setEditingDoctorId] = useState<string | null>(null);
  const [editingServices, setEditingServices] = useState<string[]>([]);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const networkId =
    scope.data && !scope.data.can_access_all ? scope.data.network_ids[0] : undefined;

  const branches = useQuery({
    queryKey: ["admin-branches"],
    queryFn: () => api.adminBranches(),
    staleTime: 5 * 60_000,
  });

  const services = useQuery({
    queryKey: ["admin-services", networkId],
    queryFn: () => api.adminServices(networkId),
    enabled: Boolean(scope.data),
    staleTime: 5 * 60_000,
  });

  const doctors = useQuery({
    queryKey: ["admin-doctors", branchId],
    queryFn: () => api.adminDoctors(branchId),
    enabled: Boolean(branchId),
    staleTime: 10_000,
  });

  useEffect(() => {
    if (!branchId && branches.data && branches.data.length === 1) {
      setBranchId(branches.data[0].id);
    }
  }, [branchId, branches.data]);

  const createDoctor = useMutation({
    mutationFn: () =>
      api.adminCreateDoctor(branchId, {
        full_name: name,
        specialty,
        service_ids: selectedServices,
      }),
    onSuccess: async () => {
      setError("");
      setMessage(t("admin.doctorCreated"));
      setName("");
      setSpecialty("");
      setSelectedServices([]);
      await queryClient.invalidateQueries({ queryKey: ["admin-doctors"] });
    },
    onError: (mutationError: unknown) =>
      setError(mutationError instanceof Error ? mutationError.message : t("common.error")),
  });

  const toggleDoctor = useMutation({
    mutationFn: (payload: { id: string; isActive: boolean }) =>
      api.adminUpdateDoctor(payload.id, { is_active: payload.isActive }),
    onSuccess: async () => {
      setError("");
      await queryClient.invalidateQueries({ queryKey: ["admin-doctors"] });
    },
    onError: (mutationError: unknown) =>
      setError(mutationError instanceof Error ? mutationError.message : t("common.error")),
  });

  const saveServices = useMutation({
    mutationFn: () => api.adminSetDoctorServices(editingDoctorId ?? "", editingServices),
    onSuccess: async () => {
      setError("");
      setEditingDoctorId(null);
      await queryClient.invalidateQueries({ queryKey: ["admin-doctors"] });
    },
    onError: (mutationError: unknown) =>
      setError(mutationError instanceof Error ? mutationError.message : t("common.error")),
  });

  return (
    <div className="screen">
      <h2>{t("admin.doctors")}</h2>

      <section className="section">
        <h3 className="section__title">{t("admin.chooseBranch")}</h3>
        <div className="section__body">
          {branches.data?.length ? null : <p className="muted">{t("admin.noBranches")}</p>}
          {branches.data?.map((branch) => (
            <button
              key={branch.id}
              className={branch.id === branchId ? "choice choice--active" : "choice"}
              onClick={() => {
                setBranchId(branch.id);
                setEditingDoctorId(null);
              }}
              type="button"
            >
              {branch.name}
            </button>
          ))}
        </div>
      </section>

      {error ? <p className="error">{error}</p> : null}
      {message ? <p className="success">{message}</p> : null}

      {branchId ? (
        <section className="section">
          <h3 className="section__title">{t("admin.createDoctor")}</h3>
          <input
            className="input"
            onChange={(event) => setName(event.target.value)}
            placeholder={t("admin.doctorName")}
            value={name}
          />
          <input
            className="input"
            onChange={(event) => setSpecialty(event.target.value)}
            placeholder={t("admin.specialty")}
            value={specialty}
          />
          <p className="muted">{t("admin.servicesHint")}</p>
          <div className="section__body">
            {services.data?.map((service) => (
              <button
                key={service.id}
                className={selectedServices.includes(service.id) ? "choice choice--active" : "choice"}
                onClick={() => setSelectedServices((list) => toggleId(list, service.id))}
                type="button"
              >
                {service.name}
              </button>
            ))}
          </div>
          <button
            className="button button--primary"
            disabled={!name.trim() || createDoctor.isPending}
            onClick={() => createDoctor.mutate()}
            type="button"
          >
            {createDoctor.isPending ? t("common.saving") : t("admin.createDoctor")}
          </button>
        </section>
      ) : null}

      {doctors.isLoading ? <p className="muted">{t("common.loading")}</p> : null}
      {branchId && doctors.data && doctors.data.length === 0 ? (
        <p className="muted">{t("admin.noDoctors")}</p>
      ) : null}

      {doctors.data?.map((doctor) => (
        <article className="card" key={doctor.id}>
          <h3 className="card__title">
            {doctor.full_name}
            {doctor.is_active ? "" : " · ⏸"}
          </h3>
          {doctor.specialty ? <p className="card__meta">{doctor.specialty}</p> : null}

          <div className="card__actions">
            <button
              className="button button--secondary"
              disabled={toggleDoctor.isPending}
              onClick={() =>
                toggleDoctor.mutate({ id: doctor.id, isActive: !doctor.is_active })
              }
              type="button"
            >
              {doctor.is_active ? t("admin.deactivate") : t("admin.activate")}
            </button>
            <button
              className="button button--secondary"
              onClick={() => {
                setEditingDoctorId(doctor.id === editingDoctorId ? null : doctor.id);
                setEditingServices(doctor.service_ids);
              }}
              type="button"
            >
              {t("admin.services")}
            </button>
          </div>

          {editingDoctorId === doctor.id ? (
            <>
              <div className="section__body">
                {services.data?.map((service) => (
                  <button
                    key={service.id}
                    className={
                      editingServices.includes(service.id) ? "choice choice--active" : "choice"
                    }
                    onClick={() => setEditingServices((list) => toggleId(list, service.id))}
                    type="button"
                  >
                    {service.name}
                  </button>
                ))}
              </div>
              <button
                className="button button--primary"
                disabled={saveServices.isPending}
                onClick={() => saveServices.mutate()}
                type="button"
              >
                {saveServices.isPending ? t("common.saving") : t("common.save")}
              </button>
            </>
          ) : null}
        </article>
      ))}
    </div>
  );
}
