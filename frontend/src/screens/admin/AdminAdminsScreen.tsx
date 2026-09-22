import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "../../api/client";
import { useT } from "../../i18n/context";
import { useAdminScope } from "./useAdminScope";

/**
 * Администраторы: назначение по уровням.
 *
 * - Администратор Avela: назначает админов сетей и админов филиалов.
 * - Администратор сети: назначает только админов филиалов своей сети.
 * - Администратор филиала: никого не назначает (сюда не попадёт — экран закрыт).
 */
export default function AdminAdminsScreen() {
  const t = useT();
  const scope = useAdminScope();
  const role = scope.data?.role ?? "patient";

  const [networkId, setNetworkId] = useState("");
  const [branchId, setBranchId] = useState("");
  const [telegramId, setTelegramId] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const isAvelaAdmin = role === "avela_admin";
  const canAssignBranchAdmins = role === "avela_admin" || role === "network_admin";

  const networks = useQuery({
    queryKey: ["admin-networks"],
    queryFn: () => api.adminNetworks(),
    enabled: isAvelaAdmin,
    staleTime: 5 * 60_000,
  });

  const branches = useQuery({
    queryKey: ["admin-branches"],
    queryFn: () => api.adminBranches(),
    enabled: canAssignBranchAdmins,
    staleTime: 5 * 60_000,
  });

  const assignNetworkAdmin = useMutation({
    mutationFn: () => api.adminAssignNetworkAdmin(networkId, Number(telegramId)),
    onSuccess: () => {
      setError("");
      setMessage(t("admin.assigned"));
      setTelegramId("");
    },
    onError: (mutationError: unknown) =>
      setError(mutationError instanceof Error ? mutationError.message : t("common.error")),
  });

  const assignBranchAdmin = useMutation({
    mutationFn: () => api.adminAssignBranchAdmin(branchId, Number(telegramId)),
    onSuccess: () => {
      setError("");
      setMessage(t("admin.assigned"));
      setTelegramId("");
    },
    onError: (mutationError: unknown) =>
      setError(mutationError instanceof Error ? mutationError.message : t("common.error")),
  });

  if (!canAssignBranchAdmins && !isAvelaAdmin) {
    return (
      <div className="screen">
        <h2>{t("admin.admins")}</h2>
        <p className="muted">{t("admin.noAccessHint")}</p>
      </div>
    );
  }

  return (
    <div className="screen">
      <h2>{t("admin.admins")}</h2>

      {error ? <p className="error">{error}</p> : null}
      {message ? <p className="success">{message}</p> : null}

      <section className="card">
        <h3 className="section__title">{t("admin.telegramId")}</h3>
        <input
          className="input"
          inputMode="numeric"
          onChange={(event) => setTelegramId(event.target.value)}
          placeholder="855318466"
          value={telegramId}
        />
      </section>

      {isAvelaAdmin ? (
        <section className="card">
          <h3 className="section__title">
            {t("admin.assignNetworkAdmin")} — {t("admin.chooseNetwork")}
          </h3>
          <div className="section__body">
            {networks.data?.map((network) => (
              <button
                key={network.id}
                className={network.id === networkId ? "choice choice--active" : "choice"}
                onClick={() => setNetworkId(network.id)}
                type="button"
              >
                {network.name}
              </button>
            ))}
          </div>
          <button
            className="button button--primary"
            disabled={!networkId || !telegramId.trim() || assignNetworkAdmin.isPending}
            onClick={() => assignNetworkAdmin.mutate()}
            type="button"
          >
            {assignNetworkAdmin.isPending ? t("common.saving") : t("admin.assign")}
          </button>
        </section>
      ) : null}

      {canAssignBranchAdmins ? (
        <section className="card">
          <h3 className="section__title">
            {t("admin.assignBranchAdmin")} — {t("admin.chooseBranch")}
          </h3>
          <div className="section__body">
            {branches.data?.map((branch) => (
              <button
                key={branch.id}
                className={branch.id === branchId ? "choice choice--active" : "choice"}
                onClick={() => setBranchId(branch.id)}
                type="button"
              >
                {branch.name}
              </button>
            ))}
          </div>
          <button
            className="button button--primary"
            disabled={!branchId || !telegramId.trim() || assignBranchAdmin.isPending}
            onClick={() => assignBranchAdmin.mutate()}
            type="button"
          >
            {assignBranchAdmin.isPending ? t("common.saving") : t("admin.assign")}
          </button>
        </section>
      ) : null}
    </div>
  );
}
