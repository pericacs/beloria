import { Filters, Row, User } from "../types";
export function PeriodFilter({
  value,
  change,
  professionals,
  user,
}: {
  value: Filters;
  change: (value: Filters) => void;
  professionals: Row[];
  user: User;
}) {
  return (
    <div className="filters">
      <label>
        De
        <input
          type="date"
          value={value.start}
          onChange={(e) => change({ ...value, start: e.target.value })}
        />
      </label>
      <label>
        Até
        <input
          type="date"
          value={value.end}
          onChange={(e) => change({ ...value, end: e.target.value })}
        />
      </label>
      {user.role === "gestor" && (
        <label>
          Profissional
          <select
            aria-label="Profissional"
            value={value.professional_id}
            onChange={(e) =>
              change({ ...value, professional_id: e.target.value })
            }
          >
            <option value="">Todos os profissionais</option>
            {professionals.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </label>
      )}
    </div>
  );
}
