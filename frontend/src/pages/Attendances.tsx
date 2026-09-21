import { FormEvent, useEffect, useRef, useState } from "react";
import { Plus } from "lucide-react";
import { api, options } from "../api";
import { Attendance, Filters, Page, Row, User, money, query } from "../types";
import { Message, Modal, Pagination } from "../components/Common";
import { AttendanceTable } from "../components/AttendanceTable";
import { PeriodFilter } from "../components/PeriodFilter";
export function Attendances({
  user,
  commissions = false,
}: {
  user: User;
  commissions?: boolean;
}) {
  const [filters, setFilters] = useState<Filters>({
      start: "",
      end: "",
      professional_id: "",
    }),
    [status, setStatus] = useState(""),
    [page, setPage] = useState(1),
    [data, setData] = useState<Page<Attendance>>({
      items: [],
      total: 0,
      page: 1,
      page_size: 25,
    }),
    [professionals, setProfessionals] = useState<Row[]>([]),
    [clients, setClients] = useState<Row[]>([]),
    [services, setServices] = useState<Row[]>([]),
    [error, setError] = useState(""),
    [success, setSuccess] = useState(""),
    [loading, setLoading] = useState(true),
    [modal, setModal] = useState<"new" | "review" | "payout" | null>(null),
    [review, setReview] = useState<{ row: Attendance; decision: string }>(),
    [selected, setSelected] = useState<number[]>([]),
    [saving, setSaving] = useState(false),
    [formError, setFormError] = useState(""),
    [professionalId, setProfessionalId] = useState(
      String(user.professional_id || ""),
    );
  const operation = useRef(crypto.randomUUID());
  async function load() {
    setLoading(true);
    setError("");
    try {
      const statusQuery =
        status === "paid"
          ? "status=approved&paid=true"
          : status === "payable"
            ? "status=approved&paid=false"
            : status
              ? `status=${status}`
              : "";
      const [a, p, c, s] = await Promise.all([
        api<Page<Attendance>>(
          `/attendances?page=${page}&${query(filters)}&${statusQuery}`,
        ),
        options("/professionals"),
        options("/clients"),
        options("/services"),
      ]);
      setData(a);
      setProfessionals(p);
      setClients(c);
      setServices(s);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    setSelected([]);
    void load();
  }, [filters, status, page]);
  function open(value: "new" | "review" | "payout") {
    operation.current = crypto.randomUUID();
    setFormError("");
    setModal(value);
  }
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setSaving(true);
    setFormError("");
    const form = new FormData(e.currentTarget);
    try {
      if (modal === "new")
        await api(
          "/attendances",
          "POST",
          {
            professional_id: Number(form.get("professional_id")),
            client_id: form.get("client_id")
              ? Number(form.get("client_id"))
              : null,
            service_id: Number(form.get("service_id")),
            payment_method: form.get("payment_method"),
          },
          operation.current,
        );
      if (modal === "review" && review)
        await api(`/attendances/${review.row.id}/review`, "POST", {
          decision: review.decision,
          reason: form.get("reason") || null,
        });
      if (modal === "payout")
        await api(
          "/payouts",
          "POST",
          { attendance_ids: selected, reference: form.get("reference") },
          operation.current,
        );
      setModal(null);
      setSelected([]);
      setSuccess(
        modal === "payout"
          ? "Repasse registrado. Nenhuma transferência bancária foi executada."
          : modal === "new"
            ? "Atendimento registrado e enviado para aprovação."
            : "Análise registrada.",
      );
      await load();
    } catch (e) {
      setFormError((e as Error).message);
    } finally {
      setSaving(false);
    }
  }
  const eligibleServices = services.filter(
    (s) =>
      s.active &&
      professionals
        .find((p) => p.id === Number(professionalId))
        ?.specialty_ids.includes(s.specialty_id),
  );
  return (
    <>
      <div className="page-heading">
        <div>
          <p className="eyebrow">
            {commissions ? "Controle financeiro" : "Sua operação"}
          </p>
          <h1>{commissions ? "Comissões" : "Atendimentos"}</h1>
          <p>
            {commissions
              ? "Acompanhe comissões pendentes, aprovadas e pagas."
              : "Registre serviços e acompanhe cada aprovação."}
          </p>
        </div>
        {!commissions && (
          <button className="primary" onClick={() => open("new")}>
            <Plus size={18} /> Novo atendimento
          </button>
        )}
        {commissions && user.role === "gestor" && (
          <button
            className="primary"
            disabled={!selected.length}
            onClick={() => open("payout")}
          >
            Registrar repasse ({selected.length})
          </button>
        )}
      </div>
      <PeriodFilter
        value={filters}
        change={(f) => {
          setPage(1);
          setFilters(f);
        }}
        professionals={professionals}
        user={user}
      />
      <div className="tabs" aria-label="Filtrar situação">
        {[
          ["", "Todos"],
          ["pending", "Pendentes"],
          ["payable", "Aprovados a pagar"],
          ["paid", "Pagos"],
          ["rejected", "Rejeitados"],
        ].map(([value, label]) => (
          <button
            key={value}
            className={status === value ? "active" : ""}
            aria-pressed={status === value}
            onClick={() => {
              setPage(1);
              setStatus(value);
            }}
          >
            {label}
          </button>
        ))}
      </div>
      <Message error={error} success={success} />
      <section className="panel">
        {loading ? (
          <p className="loading" role="status">
            Carregando atendimentos…
          </p>
        ) : (
          <AttendanceTable
            rows={data.items}
            selected={selected}
            select={
              commissions && user.role === "gestor"
                ? (id) =>
                    setSelected((s) =>
                      s.includes(id) ? s.filter((x) => x !== id) : [...s, id],
                    )
                : undefined
            }
            review={
              !commissions && user.role === "gestor"
                ? (row, decision) => {
                    setReview({ row, decision });
                    open("review");
                  }
                : undefined
            }
          />
        )}
        <Pagination page={page} total={data.total} change={setPage} />
      </section>
      {commissions && (
        <p className="footnote">
          O repasse registra um pagamento já realizado. Não executa
          transferência bancária. A seleção considera a página atual.
        </p>
      )}
      {modal && (
        <Modal
          title={
            modal === "new"
              ? "Novo atendimento"
              : modal === "payout"
                ? "Registrar repasse"
                : review?.decision === "approved"
                  ? "Aprovar atendimento"
                  : "Rejeitar atendimento"
          }
          close={() => setModal(null)}
        >
          <form onSubmit={submit}>
            <Message error={formError} />
            {modal === "new" && (
              <>
                <label>
                  Profissional
                  <select
                    aria-label="Profissional"
                    autoFocus
                    name="professional_id"
                    required
                    value={professionalId}
                    onChange={(e) => setProfessionalId(e.target.value)}
                  >
                    <option value="">Selecione</option>
                    {professionals
                      .filter((p) => p.active)
                      .map((p) => (
                        <option key={p.id} value={p.id}>
                          {p.name}
                        </option>
                      ))}
                  </select>
                </label>
                <label>
                  Cliente
                  <select aria-label="Cliente" name="client_id">
                    <option value="">Cliente avulso</option>
                    {clients
                      .filter((c) => c.active)
                      .map((c) => (
                        <option key={c.id} value={c.id}>
                          {c.name}
                        </option>
                      ))}
                  </select>
                </label>
                <label>
                  Serviço
                  <select
                    aria-label="Serviço"
                    name="service_id"
                    required
                    key={professionalId}
                  >
                    <option value="">Selecione</option>
                    {eligibleServices.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.name} · {money(s.price_cents)}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Forma de pagamento
                  <select aria-label="Forma de pagamento" name="payment_method">
                    <option value="pix">Pix</option>
                    <option value="dinheiro">Dinheiro</option>
                    <option value="credito">Cartão de crédito</option>
                    <option value="debito">Cartão de débito</option>
                  </select>
                </label>
                <p className="notice">
                  O valor e a comissão serão calculados no servidor e
                  preservados neste lançamento. O atendimento ficará pendente de
                  aprovação.
                </p>
              </>
            )}
            {modal === "review" && (
              <>
                <p>
                  {review?.row.service_name} · {review?.row.professional_name} ·{" "}
                  {money(review?.row.price_cents || 0)}
                </p>
                {review?.decision === "rejected" ? (
                  <label>
                    Motivo da rejeição
                    <textarea
                      autoFocus
                      name="reason"
                      required
                      maxLength={500}
                    />
                  </label>
                ) : (
                  <p>A aprovação libera a comissão para repasse.</p>
                )}
              </>
            )}
            {modal === "payout" && (
              <>
                <p>
                  {selected.length} atendimento(s) · Total:{" "}
                  <strong>
                    {money(
                      data.items
                        .filter((a) => selected.includes(a.id))
                        .reduce((s, a) => s + a.commission_cents, 0),
                    )}
                  </strong>
                </p>
                <label>
                  Referência do pagamento
                  <input
                    autoFocus
                    name="reference"
                    required
                    maxLength={200}
                    placeholder="Identificador do comprovante ou recibo"
                  />
                </label>
                <p className="notice">
                  Confirme apenas após realizar o pagamento ao profissional.
                </p>
              </>
            )}
            <div className="form-actions">
              <button
                type="button"
                className="secondary"
                onClick={() => setModal(null)}
              >
                Cancelar
              </button>
              <button className="primary" disabled={saving}>
                {saving
                  ? "Salvando…"
                  : modal === "new"
                    ? "Registrar atendimento"
                    : "Confirmar"}
              </button>
            </div>
          </form>
        </Modal>
      )}
    </>
  );
}
