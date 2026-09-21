# Beloria

- Preserve tenant isolation: derive business from the authenticated session; scope every query and relationship.
- Backend owns prices, commissions, permissions, approval and payouts. Integer cents and basis points only.
- Financial records are immutable except explicit approval/rejection and payout transitions; audit relevant writes.
- Use PostgreSQL tests for constraints, migrations and concurrency. Never claim unexecuted checks passed.
- Interface language: Portuguese; use Profissionais. No scheduling or AI in this MVP.
- Do not commit secrets, local databases, node_modules or generated builds.
- Keep backend modules and frontend components separated. No simulated-success controls.
