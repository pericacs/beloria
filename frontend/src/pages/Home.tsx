import { useEffect, useState } from "react";
import {
  ArrowUpRight,
  Banknote,
  CircleDollarSign,
  ReceiptText,
  Wallet,
} from "lucide-react";
import { api, options } from "../api";
import {
  Attendance,
  Dashboard,
  Filters,
  Page,
  Row,
  User,
  money,
  query,
} from "../types";
import { PeriodFilter } from "../components/PeriodFilter";
import { AttendanceTable } from "../components/AttendanceTable";
import { Empty, Message } from "../components/Common";
export function Home({
  user,
  navigate,
}: {
  user: User;
  navigate: (page: string) => void;
}) {
  const [filters, setFilters] = useState<Filters>({
      start: "",
      end: "",
      professional_id: "",
    }),
    [professionals, setProfessionals] = useState<Row[]>([]),
    [data, setData] = useState<Dashboard>(),
    [rows, setRows] = useState<Attendance[]>([]),
    [error, setError] = useState(""),
    [loading, setLoading] = useState(true);
  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    Promise.all([
      api<Dashboard>("/dashboard?" + query(filters)),
      api<Page<Attendance>>("/attendances?page_size=5&" + query(filters)),
      options("/professionals"),
    ])
      .then(([d, a, p]) => {
        if (active) {
          setData(d);
          setRows(a.items);
          setProfessionals(p);
        }
      })
      .catch((e) => {
        if (active) setError(e.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [filters]);
  const max = Math.max(1, ...(data?.series.map((s) => s.revenue_cents) || []));
  return (
    <>
      <div className="page-heading">
        <div>
          <p className="eyebrow">Seu negócio, em equilíbrio</p>
          <h1>Visão geral</h1>
          <p>Acompanhe o que acontece no {user.business_name}.</p>
        </div>
        <button className="primary" onClick={() => navigate("attendances")}>
          Novo atendimento <ArrowUpRight size={18} />
        </button>
      </div>
      <PeriodFilter
        value={filters}
        change={setFilters}
        professionals={professionals}
        user={user}
      />
      <Message error={error} />
      {loading ? (
        <p role="status" className="loading">
          Carregando seus indicadores…
        </p>
      ) : (
        data && (
          <>
            <div className="metrics">
              <Metric
                title="Faturamento aprovado"
                value={money(data.revenue_cents)}
                icon={<Banknote />}
              />
              <Metric
                title="Atendimentos registrados"
                value={String(data.attendance_count)}
                icon={<ReceiptText />}
              />
              <Metric
                title="Comissões a pagar"
                value={money(data.payable_cents)}
                icon={<CircleDollarSign />}
              />
              <Metric
                title="Repasses registrados"
                value={money(data.paid_cents)}
                icon={<Wallet />}
              />
            </div>
            <div className="home-grid">
              <section className="panel">
                <div className="panel-heading">
                  <div>
                    <h2>Movimento do negócio</h2>
                    <p>Faturamento aprovado por dia</p>
                  </div>
                  <span className="chart-legend">● Receita</span>
                </div>
                {data.series.length ? (
                  <div
                    className="chart"
                    role="img"
                    aria-label="Gráfico do faturamento aprovado por dia"
                  >
                    <div className="chart-bars">
                      {data.series.map((point) => (
                        <div className="chart-column" key={point.day}>
                          <small>{money(point.revenue_cents)}</small>
                          <div
                            className="bar"
                            style={{
                              height: Math.max(
                                4,
                                (point.revenue_cents / max) * 170,
                              ),
                            }}
                          />
                          <span>
                            {point.day.slice(8)}/{point.day.slice(5, 7)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <Empty text="O gráfico começa com seu primeiro atendimento aprovado." />
                )}
              </section>
              <section className="panel summary">
                <p className="eyebrow">Resumo financeiro</p>
                <h2>Cada detalhe conta.</h2>
                <p>As comissões acompanham o status dos seus atendimentos.</p>
                <dl>
                  <div>
                    <dt>
                      <span className="dot amber" /> Pendentes de aprovação
                    </dt>
                    <dd>{money(data.pending_cents)}</dd>
                  </div>
                  <div>
                    <dt>
                      <span className="dot green" /> Aprovadas a pagar
                    </dt>
                    <dd>{money(data.payable_cents)}</dd>
                  </div>
                  <div>
                    <dt>
                      <span className="dot pale" /> Comissões pagas
                    </dt>
                    <dd>{money(data.paid_cents)}</dd>
                  </div>
                </dl>
                <button
                  className="summary-link"
                  onClick={() => navigate("commissions")}
                >
                  Ver comissões <ArrowUpRight size={18} />
                </button>
              </section>
            </div>
            <section className="panel">
              <div className="panel-heading">
                <div>
                  <h2>Últimos atendimentos</h2>
                  <p>O dia a dia do seu negócio em um só lugar.</p>
                </div>
                <button
                  className="text-button"
                  onClick={() => navigate("attendances")}
                >
                  Ver todos <ArrowUpRight size={16} />
                </button>
              </div>
              <AttendanceTable rows={rows} />
            </section>
          </>
        )
      )}
    </>
  );
}
function Metric({
  title,
  value,
  icon,
}: {
  title: string;
  value: string;
  icon: React.ReactNode;
}) {
  return (
    <div className="metric">
      <div className="metric-top">
        <span>{title}</span>
        <span className="metric-icon">{icon}</span>
      </div>
      <strong>{value}</strong>
      <small>No período selecionado</small>
    </div>
  );
}
