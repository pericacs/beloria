import { FormEvent, useEffect, useState } from "react";
import { api } from "../api";
import { Page, dateTime, money } from "../types";
import { Empty, Message, Modal, Pagination } from "../components/Common";
const stateName: Record<string, string> = {
  legacy_review: "Legado — revisar contratação",
  trial: "Trial ativo",
  subscribed: "Assinatura válida",
  payment_required: "Aguardando pagamento",
  blocked: "Bloqueado",
};
export function PlatformPanel({ logout }: { logout: () => Promise<void> }) {
  const [tab, setTab] = useState("companies"),
    [page, setPage] = useState(1),
    [data, setData] = useState<Page<any>>({
      items: [],
      total: 0,
      page: 1,
      page_size: 25,
    }),
    [error, setError] = useState(""),
    [success, setSuccess] = useState(""),
    [review, setReview] = useState<any>(null),
    [busy, setBusy] = useState(false),
    [loading, setLoading] = useState(true);
  async function load() {
    setLoading(true);
    setError("");
    try {
      setData(await api<Page<any>>(`/platform/${tab}?page=${page}`));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    void load();
  }, [tab, page]);
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    const f = new FormData(e.currentTarget);
    try {
      await api(`/platform/companies/${review.id}/access`, "PUT", {
        access_blocked: !review.access_blocked,
        reason: f.get("reason"),
      });
      setReview(null);
      setSuccess(
        "Situação de acesso atualizada. Remover bloqueio não renova trial nem confirma pagamento.",
      );
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="platform-shell">
      <header className="platform-header">
        <a className="wordmark" href="/beloria">
          beloria.
        </a>
        <span>Administração da plataforma</span>
        <button className="secondary" onClick={logout}>
          Sair
        </button>
      </header>
      <main className="platform-main">
        <div className="page-heading">
          <div>
            <p className="eyebrow">Painel Beloria</p>
            <h1>Empresas e acesso</h1>
            <p>
              Acompanhe a contratação, as assinaturas e a situação de cada
              empresa.
            </p>
          </div>
        </div>
        <div className="platform-notice">
          Cobrança real ainda indisponível. Planos, preços, periodicidade e
          provedor precisam ser configurados.
        </div>
        <div className="tabs">
          {[
            ["companies", "Empresas e assinaturas"],
            ["payments", "Pagamentos"],
            ["conflicts", "Vínculos em análise"],
            ["audit", "Histórico da plataforma"],
          ].map(([key, label]) => (
            <button
              key={key}
              className={tab === key ? "active" : ""}
              onClick={() => {
                setPage(1);
                setTab(key);
              }}
            >
              {label}
            </button>
          ))}
        </div>
        <Message error={error} success={success} />
        <section className="panel">
          {loading ? (
            <p className="loading">Carregando…</p>
          ) : !data.items.length ? (
            <Empty />
          ) : (
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    {(tab === "companies"
                      ? [
                          "Empresa",
                          "Responsável",
                          "Acesso / trial",
                          "Assinatura",
                          "Ações",
                        ]
                      : tab === "payments"
                        ? ["Empresa", "Referência", "Valor", "Situação"]
                        : tab === "conflicts"
                          ? ["Identidade", "Vínculos preservados"]
                          : ["Data", "Ação", "Empresa"]
                    ).map((h) => (
                      <th key={h}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((r) => (
                    <tr key={r.id || r.identity_id}>
                      {tab === "companies" ? (
                        <>
                          <td>
                            <strong>{r.name}</strong>
                            <small>Empresa #{r.id}</small>
                          </td>
                          <td>
                            {r.responsible_name || "Cadastro anterior"}
                            <small>{r.contact}</small>
                          </td>
                          <td>
                            {stateName[r.state]}
                            <small>
                              {r.trial_started_at
                                ? `${dateTime(r.trial_started_at)} até ${dateTime(r.trial_ends_at)}`
                                : "Sem novo trial"}
                            </small>
                          </td>
                          <td>
                            {r.subscription
                              ? `${r.subscription.status === "active" ? "Ativa" : "Cancelada"} até ${dateTime(r.subscription.valid_until)}`
                              : "Sem assinatura confirmada"}
                          </td>
                          <td>
                            <button
                              className="text-button"
                              onClick={() => setReview(r)}
                            >
                              {r.access_blocked
                                ? "Remover bloqueio manual"
                                : "Bloquear acesso"}
                            </button>
                          </td>
                        </>
                      ) : tab === "payments" ? (
                        <>
                          <td>{r.company_name}</td>
                          <td>{r.provider_reference}</td>
                          <td>{money(r.amount_cents)}</td>
                          <td>
                            {r.status === "paid"
                              ? "Confirmado"
                              : r.status === "pending"
                                ? "Pendente"
                                : "Cancelado"}
                          </td>
                        </>
                      ) : tab === "conflicts" ? (
                        <>
                          <td>#{r.identity_id}</td>
                          <td>
                            {r.memberships.map((m: any) => (
                              <div key={m.id}>
                                {m.company_name} · {m.role} · vínculo #{m.id}
                              </div>
                            ))}
                            <small>
                              Exige revisão individual. Nenhum vínculo foi
                              removido automaticamente.
                            </small>
                          </td>
                        </>
                      ) : (
                        <>
                          <td>{dateTime(r.created_at)}</td>
                          <td>
                            {r.action}
                            <small>{r.details?.reason}</small>
                          </td>
                          <td>{r.company_name || "Plataforma"}</td>
                        </>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <Pagination page={page} total={data.total} change={setPage} />
        </section>
      </main>
      {review && (
        <Modal
          title={
            review.access_blocked
              ? "Remover bloqueio manual"
              : "Bloquear acesso da empresa"
          }
          close={() => setReview(null)}
        >
          <form onSubmit={submit}>
            <Message error={error} />
            <p>{review.name}</p>
            <label>
              Motivo
              <input name="reason" required maxLength={500} />
            </label>
            <p className="footnote">
              Esta ação não altera a validade do trial nem a confirmação de
              pagamento.
            </p>
            <button className="primary" disabled={busy}>
              Confirmar alteração
            </button>
          </form>
        </Modal>
      )}
    </div>
  );
}
