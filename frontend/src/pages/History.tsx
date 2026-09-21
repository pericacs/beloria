import { useEffect, useState } from "react";
import { api, options } from "../api";
import { Filters, Page, Row, User, dateTime, money, query } from "../types";
import { Empty, Message, Pagination } from "../components/Common";
import { PeriodFilter } from "../components/PeriodFilter";
const actions: Record<string, string> = {
  created: "Cadastro criado",
  updated: "Cadastro atualizado",
  "attendance.created": "Atendimento registrado",
  "attendance.approved": "Atendimento aprovado",
  "attendance.rejected": "Atendimento rejeitado",
  "payout.created": "Repasse registrado",
  "business.created": "Negócio criado",
};
const entities: Record<string, string> = {
  specialties: "Especialidade",
  professionals: "Profissional",
  clients: "Cliente",
  services: "Serviço",
  attendances: "Atendimento",
  payouts: "Repasse",
  businesses: "Negócio",
};
export function History({
  audit = false,
  user,
}: {
  audit?: boolean;
  user: User;
}) {
  const [data, setData] = useState<Page<any>>({
      items: [],
      total: 0,
      page: 1,
      page_size: 25,
    }),
    [page, setPage] = useState(1),
    [error, setError] = useState(""),
    [loading, setLoading] = useState(true),
    [filters, setFilters] = useState<Filters>({
      start: "",
      end: "",
      professional_id: "",
    }),
    [professionals, setProfessionals] = useState<Row[]>([]);
  useEffect(() => {
    let live = true;
    setLoading(true);
    setError("");
    Promise.all([
      api<Page<any>>(
        `/${audit ? "audit" : "payouts"}?page=${page}&${query(filters)}`,
      ),
      audit ? Promise.resolve([]) : options("/professionals"),
    ])
      .then(([d, p]) => {
        if (live) {
          setData(d);
          setProfessionals(p);
        }
      })
      .catch((e) => {
        if (live) setError(e.message);
      })
      .finally(() => {
        if (live) setLoading(false);
      });
    return () => {
      live = false;
    };
  }, [audit, page, filters]);
  return (
    <>
      <div className="page-heading">
        <div>
          <p className="eyebrow">Transparência em cada ação</p>
          <h1>{audit ? "Auditoria" : "Repasses"}</h1>
          <p>
            {audit
              ? "Histórico de alterações, aprovações e pagamentos."
              : "Pagamentos registrados e suas referências."}
          </p>
        </div>
      </div>
      {!audit && (
        <>
          <PeriodFilter
            value={filters}
            change={(f) => {
              setPage(1);
              setFilters(f);
            }}
            professionals={professionals}
            user={user}
          />
          <p className="footnote">
            O período filtra a data dos atendimentos incluídos. O total
            considera somente os atendimentos do filtro.
          </p>
        </>
      )}
      <Message error={error} />
      <section className="panel">
        {loading ? (
          <p className="loading" role="status">
            Carregando histórico…
          </p>
        ) : !data.items.length ? (
          <Empty />
        ) : (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Data</th>
                  <th>{audit ? "Ação" : "Referência"}</th>
                  <th>{audit ? "Usuário" : "Valor"}</th>
                  <th>{audit ? "Registro" : "Atendimentos"}</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((row) => (
                  <tr key={row.id}>
                    <td>{dateTime(row.created_at)}</td>
                    <td>
                      <strong>
                        {audit
                          ? actions[row.action] || row.action
                          : row.reference}
                      </strong>
                      {row.details?.reason && (
                        <small>{row.details.reason}</small>
                      )}
                    </td>
                    <td>{audit ? row.user_email : money(row.total_cents)}</td>
                    <td>
                      {audit
                        ? `${entities[row.entity] || row.entity} #${row.entity_id}`
                        : row.attendance_ids
                            .map((id: number) => "#" + id)
                            .join(", ")}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <Pagination page={page} total={data.total} change={setPage} />
      </section>
    </>
  );
}
