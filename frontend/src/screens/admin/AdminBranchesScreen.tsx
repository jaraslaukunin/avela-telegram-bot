import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "../../api/client";
import { useT } from "../../i18n/context";
import { useAdminScope } from "./useAdminScope";

/** Филиалы сети: список, создание и включение/отключение. */
export default function AdminBranchesScreen() {
  const t = useT();
  const queryClient = useQueryClient();
  const scope = useAdminScope();

  const [name, setName] = useState("");
  const [city, setCity] = useState("");
  const [address, setAddress] = useState("");
  const [phone, setPhone] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const branches = useQuery({
    queryKey: ["admin-branches"],
    queryFn: () => api.adminBranches(),
    enabled: Boolean(scope.data),
    staleTime: 30_000,
  });

  const networkId =
    scope.data && !scope.data.can_access_all ? scope.data.network_ids[0] : undefined;

  // Филиалы создаёт и отключает администратор сети (или владелец),
  // администратор филиала видит список, но не управляет им.
  const canManageBranches = Boolean(
    scope.data && scope.data.role !== "branch_admin",
  );

  const createBranch = useMutation({
    mutationFn: () =>
      api.adminCreateBranch(networkId ?? "", {
        name: name.trim(),
        city,
        address,
        phone,
      }),
    onSuccess: async () => {
      setError("");
      setMessage(t("admin.created"));
      setName("");
      setCity("");
      setAddress("");
      setPhone("");
      await queryClient.invalidateQueries({ queryKey: ["admin-branches"] });
    },
    onError: (mutationError: unknown) =>
      setError(mutationError instanceof Error ? mutationError.message : t("common.error")),
  });

  const toggleBranch = useMutation({
    mutationFn: (payload: { id: string; isActive: boolean }) =>
      api.adminUpdateBranch(payload.id, { is_active: payload.isActive }),
    onSuccess: async () => {
      setError("");
      await queryClient.invalidateQueries({ queryKey: ["admin-branches"] });
    },
    onError: (mutationError: unknown) =>
      setError(mutationError instanceof Error ? mutationError.message : t("common.error")),
  });

  return (
    <div className="screen">
      <h2>{t("admin.branches")}</h2>

      {error ? <p className="error">{error}</p> : null}
      {message ? <p className="success">{message}</p> : null}

      {networkId && canManageBranches ? (
        <section className="card">
          <h3 className="section__title">{t("admin.createBranch")}</h3>
          <input
            className="input"
            onChange={(event) => setName(event.target.value)}
            placeholder={t("admin.branchName")}
            value={name}
          />
          <input
            className="input"
            onChange={(event) => setCity(event.target.value)}
            placeholder={t("admin.cityLabel")}
            value={city}
          />
          <input
            className="input"
            onChange={(event) => setAddress(event.target.value)}
            placeholder={t("admin.address")}
            value={address}
          />
          <input
            className="input"
            onChange={(event) => setPhone(event.target.value)}
            placeholder={t("admin.phoneLabel")}
            value={phone}
          />
          <button
            className="button button--primary"
            disabled={!name.trim() || createBranch.isPending}
            onClick={() => createBranch.mutate()}
            type="button"
          >
            {createBranch.isPending ? t("common.saving") : t("admin.createBranch")}
          </button>
        </section>
      ) : null}

      {branches.isLoading ? <p className="muted">{t("common.loading")}</p> : null}
      {branches.data && branches.data.length === 0 ? (
        <p className="muted">{t("admin.noBranches")}</p>
      ) : null}

      {branches.data?.map((branch) => (
        <article className="card" key={branch.id}>
          <h3 className="card__title">{branch.name}</h3>
          <p className="card__meta">
            {branch.city}
            {branch.address ? `, ${branch.address}` : ""}
          </p>
          <p className="card__meta">{branch.phone}</p>
          <p className="card__meta">{t("admin.timezone")}: {branch.timezone}</p>
          {networkId === branch.network_id && canManageBranches ? (
            <div className="card__actions">
              <button
                className="button button--secondary"
                disabled={toggleBranch.isPending}
                onClick={() => toggleBranch.mutate({ id: branch.id, isActive: false })}
                type="button"
              >
                {t("admin.deactivate")}
              </button>
            </div>
          ) : null}
        </article>
      ))}
    </div>
  );
}
