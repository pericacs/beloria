import { Attendance, dateTime, money, statusName } from "../types";
import { Empty } from "./Common";
export function AttendanceTable({
  rows,
  review,
  select,
  selected = [],
}: {
  rows: Attendance[];
  review?: (row: Attendance, decision: string) => void;
  select?: (id: number) => void;
  selected?: number[];
}) {
  if (!rows.length) return <Empty text="Nenhum atendimento neste período." />;
  return (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            {select && <th aria-label="Selecionar" />}
            <th>Atendimento</th>
            <th>Profissional</th>
            <th>Valor</th>
            <th>Comissão</th>
            <th>Situação</th>
            {review && <th>Ações</th>}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id}>
              {select && (
                <td>
                  <input
                    aria-label={`Selecionar atendimento ${row.id}`}
                    type="checkbox"
                    checked={selected.includes(row.id)}
                    disabled={row.status !== "approved" || row.paid}
                    onChange={() => select(row.id)}
                  />
                </td>
              )}
              <td>
                <strong>{row.service_name}</strong>
                <small>
                  {row.client_name} · {dateTime(row.created_at)}
                </small>
                {row.rejection_reason && (
                  <small className="rejection">
                    Motivo: {row.rejection_reason}
                  </small>
                )}
              </td>
              <td>{row.professional_name}</td>
              <td>{money(row.price_cents)}</td>
              <td>
                {money(row.commission_cents)}
                <small>
                  {(row.commission_bps / 100).toLocaleString("pt-BR")}%
                </small>
              </td>
              <td>
                <span className={`badge ${row.paid ? "paid" : row.status}`}>
                  {row.paid ? "Pago" : statusName[row.status]}
                </span>
              </td>
              {review && (
                <td>
                  {row.status === "pending" && (
                    <div className="row-actions">
                      <button
                        className="text-button"
                        onClick={() => review(row, "approved")}
                      >
                        Aprovar
                      </button>
                      <button
                        className="text-button danger"
                        onClick={() => review(row, "rejected")}
                      >
                        Rejeitar
                      </button>
                    </div>
                  )}
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
