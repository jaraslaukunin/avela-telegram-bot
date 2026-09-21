"""Роли пользователей и их иерархия."""

ROLE_PATIENT = "patient"
ROLE_BRANCH_ADMIN = "branch_admin"
ROLE_NETWORK_ADMIN = "network_admin"
ROLE_AVELA_ADMIN = "avela_admin"

# Все административные роли (в порядке возрастания прав).
ADMIN_ROLES = (ROLE_BRANCH_ADMIN, ROLE_NETWORK_ADMIN, ROLE_AVELA_ADMIN)

# Роли, работающие в границах сети.
NETWORK_SCOPED_ROLES = (ROLE_NETWORK_ADMIN, ROLE_AVELA_ADMIN)
