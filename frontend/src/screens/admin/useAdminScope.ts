import { useQuery } from "@tanstack/react-query";

import { api } from "../../api/client";
import type { AdminScopeOut } from "../../api/types";

/** Зона видимости администратора: роль и доступные филиалы. */
export function useAdminScope(options: { enabled?: boolean } = {}) {
  return useQuery<AdminScopeOut>({
    queryKey: ["admin-scope"],
    queryFn: api.adminScope,
    staleTime: 5 * 60_000,
    retry: false,
    enabled: options.enabled ?? true,
  });
}
