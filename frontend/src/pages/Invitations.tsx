import { FormEvent, useEffect, useState } from "react";
import { api, options } from "../api";
import { Page, Row, dateTime } from "../types";
import { Empty, Message, Modal, Pagination } from "../components/Common";
export function Invitations() {
  const [invitations, setInvitations] = useState<Page<any>>({
      items: [],
      total: 0,
      page: 1,
      page_size: 25,
    }),
    [applications, setApplications] = useState<Page<any>>({
      items: [],
      total: 0,
      page: 1,
      page_size: 25,
    }),
    [page, setPage] = useState(1),
    [invitePage, setInvitePage] = useState(1),
    [specs, setSpecs] = useState<Row[]>([]),
    [link, setLink] = useState(""),
    [error, setError] = useState(""),
    [success, setSuccess] = useState(""),
    [busy, setBusy] = useState(false),
    [review, setReview] = useState<any>(null),
    [formError, setFormError] = useState(""),
    [loading, setLoading] = useState(true);
  async function load() {
    setLoading(true);
    try {
      const [i, r, s] = await Promise.all([
        api<Page<any>>(`/invitations?page=${invitePage}`),
        api<Page<any>>(`/join-requests?page=${page}`),
        options("/specialties"),
      ]);
      setInvitations(i);
      setApplications(r);
      setSpecs(s);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    void load();
  }, [page, invitePage]);
  async function generate() {
    setBusy(true);
    setError("");
    try {
      const value = await api<any>("/invitations", "POST", { valid_days: 7 });
      setLink(location.origin + value.path);
      setSuccess(
        "Convite criado. Válido por 7 dias. Copie o link agora: ele não será exibido novamente.",
      );
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function revoke(id: number) {
    setError("");
    try {
      await api(`/invitations/${id}/revoke`, "POST");
      setSuccess("Convite revogado.");
      await load();
    } catch (e) {
      setError((e as Error).message);
    }
  }
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setFormError("");
    const f = new FormData(e.currentTarget);
    try {
      await api(`/join-requests/${review.id}/review`, "POST", {
        decision: review.decision,
        reason: f.get("reason") || null,
        specialty_ids: f.getAll("specialty_ids").map(Number),
        commission_bps:
          review.decision === "approved"
            ? Math.round(Number(f.get("commission")) * 100)
            : null,
      });
      setReview(null);
      setSuccess("Análise do vínculo registrada.");
      await load();
    } catch (e) {
      setFormError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <div className="page-heading">
        <div>
          <p className="eyebrow">Sua equipe começa aqui</p>
          <h1>Convites e aprovações</h1>
          <p>
            A aprovação do vínculo libera o especialista. Atendimentos são
            aprovados separadamente.
          </p>
        </div>
        <button className="primary" onClick={generate} disabled={busy}>
          Gerar convite
        </button>
      </div>
      <Message error={error} success={success} />
      {link && (
        <section className="panel invite-share">
          <label>
            Link do convite
            <input readOnly value={link} />
          </label>
          <div className="row-actions">
            <button
              className="secondary"
              onClick={async () => {
                try {
                  await navigator.clipboard.writeText(link);
                  setSuccess("Link copiado.");
                } catch {
                  setError(
                    "Não foi possível copiar automaticamente. Selecione e copie o link acima.",
                  );
                }
              }}
            >
              Copiar link
            </button>
            <a
              className="button-link"
              target="_blank"
              rel="noreferrer"
              href={`https://wa.me/?text=${encodeURIComponent("Você recebeu um convite para a equipe no Beloria: " + link)}`}
            >
              Compartilhar pelo WhatsApp
            </a>
          </div>
        </section>
      )}
      <section className="panel">
        <div className="panel-heading">
          <h2>Solicitações de especialistas</h2>
          <button className="text-button" onClick={load}>
            Atualizar
          </button>
        </div>
        {loading ? (
          <p className="loading">Carregando solicitações…</p>
        ) : !applications.items.length ? (
          <Empty text="Nenhuma solicitação recebida." />
        ) : (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Especialista</th>
                  <th>Vínculo</th>
                  <th>Situação</th>
                  <th>Análise</th>
                </tr>
              </thead>
              <tbody>
                {applications.items.map((r) => (
                  <tr key={r.id}>
                    <td>
                      <strong>{r.name}</strong>
                      <small>{r.contact}</small>
                    </td>
                    <td>
                      {r.engagement === "autonomo" ? "Autônomo" : r.engagement}
                    </td>
                    <td>
                      <span className={`badge ${r.status}`}>
                        {r.status === "pending"
                          ? "Pendente"
                          : r.status === "approved"
                            ? "Aprovado"
                            : "Rejeitado"}
                      </span>
                      {r.rejection_reason && (
                        <small>{r.rejection_reason}</small>
                      )}
                    </td>
                    <td>
                      {r.status === "pending" && (
                        <div className="row-actions">
                          <button
                            className="text-button"
                            onClick={() => {
                              setFormError("");
                              setReview({ ...r, decision: "approved" });
                            }}
                          >
                            Aprovar vínculo
                          </button>
                          <button
                            className="text-button danger"
                            onClick={() => {
                              setFormError("");
                              setReview({ ...r, decision: "rejected" });
                            }}
                          >
                            Rejeitar vínculo
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <Pagination page={page} total={applications.total} change={setPage} />
      </section>
      <section className="panel">
        <div className="panel-heading">
          <h2>Convites gerados</h2>
        </div>
        {!invitations.items.length ? (
          <Empty />
        ) : (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Criado</th>
                  <th>Validade</th>
                  <th>Situação</th>
                  <th>Ação</th>
                </tr>
              </thead>
              <tbody>
                {invitations.items.map((i) => (
                  <tr key={i.id}>
                    <td>{dateTime(i.created_at)}</td>
                    <td>{dateTime(i.expires_at)}</td>
                    <td>
                      {i.revoked
                        ? "Revogado"
                        : new Date(i.expires_at) < new Date()
                          ? "Expirado"
                          : "Válido"}
                    </td>
                    <td>
                      {!i.revoked && (
                        <button
                          className="text-button danger"
                          onClick={() => revoke(i.id)}
                        >
                          Revogar
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <Pagination
          page={invitePage}
          total={invitations.total}
          change={setInvitePage}
        />
      </section>
      {review && (
        <Modal
          title={
            review.decision === "approved"
              ? "Aprovar especialista"
              : "Rejeitar solicitação"
          }
          close={() => setReview(null)}
        >
          <form onSubmit={submit}>
            <Message error={formError} />
            <p>
              {review.name} · {review.contact}
            </p>
            <p className="footnote">
              {review.cpf && `CPF: ${review.cpf}`}{" "}
              {review.cnpj && `CNPJ: ${review.cnpj}`}
            </p>
            {review.decision === "approved" ? (
              <>
                <label>
                  Comissão (%)
                  <input
                    name="commission"
                    type="number"
                    min={0}
                    max={100}
                    step="0.01"
                    required
                  />
                </label>
                <fieldset>
                  <legend>Especialidades autorizadas</legend>
                  {specs
                    .filter((s) => s.active)
                    .map((s) => (
                      <label className="check" key={s.id}>
                        <input
                          name="specialty_ids"
                          type="checkbox"
                          value={s.id}
                        />
                        {s.name}
                      </label>
                    ))}
                </fieldset>
              </>
            ) : (
              <label>
                Motivo da rejeição
                <textarea name="reason" required maxLength={500} />
              </label>
            )}
            <button className="primary" disabled={busy}>
              {busy ? "Salvando…" : "Confirmar análise"}
            </button>
          </form>
        </Modal>
      )}
    </>
  );
}
