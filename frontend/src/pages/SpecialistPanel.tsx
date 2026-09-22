import { useEffect, useState } from "react";
import {
  Home,
  ReceiptText,
  Wallet,
  LogOut,
  ArrowUpRight,
  Plus,
} from "lucide-react";
import { api } from "../api";
import { Attendance, Dashboard, Page, User, money } from "../types";
import { Attendances } from "./Attendances";
import { History } from "./History";
import { AttendanceTable } from "../components/AttendanceTable";
import { Empty, Message } from "../components/Common";
export function SpecialistPanel({
  user,
  logout,
}: {
  user: User;
  logout: () => Promise<void>;
}) {
  const [tab, setTab] = useState("home"),
    [data, setData] = useState<Dashboard>(),
    [rows, setRows] = useState<Attendance[]>([]),
    [error, setError] = useState("");
  useEffect(() => {
    if (tab !== "home") return;
    let live = true;
    Promise.all([
      api<Dashboard>("/dashboard"),
      api<Page<Attendance>>("/attendances?page_size=5"),
    ])
      .then(([d, r]) => {
        if (live) {
          setData(d);
          setRows(r.items);
        }
      })
      .catch((e) => {
        if (live) setError(e.message);
      });
    return () => {
      live = false;
    };
  }, [tab]);
  return (
    <div className="specialist-shell">
      <header className="specialist-header">
        <div>
          <a className="wordmark" href="/especialista">
            beloria.
          </a>
          <small>{user.business_name}</small>
        </div>
        <div className="specialist-account">
          <span>Meu espaço</span>
          <button className="icon-button" aria-label="Sair" onClick={logout}>
            <LogOut size={20} />
          </button>
        </div>
      </header>
      <main className="specialist-content">
        <Message error={error} />
        {tab === "home" ? (
          <>
            <div className="specialist-greeting">
              <p className="eyebrow">Painel do especialista</p>
              <h1>Seu trabalho, seus resultados.</h1>
              <p>Acompanhe sua produção e cada comissão.</p>
            </div>
            <section className="specialist-action">
              <div>
                <p className="eyebrow">Seu próximo passo</p>
                <h2>Terminou um atendimento?</h2>
                <p>Registre o serviço e envie para aprovação.</p>
              </div>
              <button onClick={() => setTab("attendances")}>
                <Plus size={19} /> Novo atendimento
              </button>
            </section>
            {!data ? (
              <p className="loading">Carregando seus resultados…</p>
            ) : (
              <>
                <div className="metrics specialist-metrics">
                  {[
                    ["Minha produção aprovada", money(data.revenue_cents)],
                    ["Meus atendimentos", String(data.attendance_count)],
                    ["Comissões a receber", money(data.payable_cents)],
                    ["Comissões pagas", money(data.paid_cents)],
                  ].map(([label, value]) => (
                    <section className="metric" key={label}>
                      <span>{label}</span>
                      <strong>{value}</strong>
                      <small>Todo o período · apenas seus valores</small>
                    </section>
                  ))}
                </div>
                <section className="panel">
                  <div className="panel-heading">
                    <div>
                      <h2>Minha produção por dia</h2>
                      <p>Valores de atendimentos aprovados</p>
                    </div>
                  </div>
                  {data.series.length ? (
                    <div className="chart">
                      <div className="chart-bars">
                        {data.series.map((p) => (
                          <div className="chart-column" key={p.day}>
                            <small>{money(p.revenue_cents)}</small>
                            <div
                              className="bar"
                              style={{
                                height: Math.max(
                                  5,
                                  (p.revenue_cents /
                                    Math.max(
                                      1,
                                      ...data.series.map(
                                        (s) => s.revenue_cents,
                                      ),
                                    )) *
                                    140,
                                ),
                              }}
                            />
                            <span>
                              {p.day.slice(8)}/{p.day.slice(5, 7)}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <Empty text="Seu gráfico começa no primeiro atendimento aprovado." />
                  )}
                </section>
                <section className="panel">
                  <div className="panel-heading">
                    <h2>Meus últimos atendimentos</h2>
                    <button
                      className="text-button"
                      onClick={() => setTab("attendances")}
                    >
                      Ver histórico <ArrowUpRight size={16} />
                    </button>
                  </div>
                  <AttendanceTable rows={rows} />
                </section>
              </>
            )}
          </>
        ) : tab === "payouts" ? (
          <History user={user} />
        ) : (
          <Attendances
            key={tab}
            user={user}
            commissions={tab === "commissions"}
          />
        )}
      </main>
      <nav className="specialist-nav" aria-label="Navegação do especialista">
        {[
          ["home", "Início", Home],
          ["attendances", "Atendimentos", ReceiptText],
          ["commissions", "Comissões", Wallet],
          ["payouts", "Repasses", ArrowUpRight],
        ].map(([key, label, Icon]) => (
          <button
            key={key as string}
            className={tab === key ? "active" : ""}
            onClick={() => {
              setTab(key as string);
              window.scrollTo(0, 0);
            }}
          >
            <Icon size={20} />
            <span>{label as string}</span>
          </button>
        ))}
      </nav>
    </div>
  );
}
