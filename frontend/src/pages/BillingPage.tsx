import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { Page, money, dateTime } from "../types";
import { Empty, Message, Pagination } from "../components/Common";
export function BillingPage() {
  const [status, setStatus] = useState<any>(),
    [invoices, setInvoices] = useState<Page<any>>({
      items: [],
      total: 0,
      page: 1,
      page_size: 25,
    }),
    [page, setPage] = useState(1),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  async function load() {
    try {
      const [s, i] = await Promise.all([
        api("/billing/status"),
        api<Page<any>>(`/billing/invoices?page=${page}`),
      ]);
      setStatus(s);
      setInvoices(i);
    } catch (e) {
      setError((e as Error).message);
    }
  }
  useEffect(() => {
    void load();
  }, [page]);
  const checkoutKey = useRef(crypto.randomUUID());
  async function checkout() {
    setBusy(true);
    setError("");
    try {
      const result = await api<any>(
        "/billing/checkout",
        "POST",
        undefined,
        checkoutKey.current,
      );
      location.assign(result.checkout_url);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <div className="page-heading">
        <div>
          <p className="eyebrow">Sua conta Beloria</p>
          <h1>Assinatura e acesso</h1>
          <p>{status?.company_name}</p>
        </div>
      </div>
      <Message error={error} />
      {!status ? (
        <p role="status">Carregando situação…</p>
      ) : (
        <section className="panel billing-status">
          <h2>
            {status.allowed
              ? "Seu acesso está disponível"
              : "Seu acesso operacional está suspenso"}
          </h2>
          {status.state === "legacy_review" ? (
            <p>
              Conta legada: nenhum novo trial foi concedido. A situação
              comercial precisa ser revisada pelo Beloria.
            </p>
          ) : status.state === "subscribed" ? (
            <p>
              Assinatura confirmada até{" "}
              {dateTime(status.subscription.valid_until)}.
            </p>
          ) : (
            <p>
              {status.trial_ends_at
                ? `Período de avaliação: até ${dateTime(status.trial_ends_at)}.`
                : "Acesso bloqueado administrativamente."}
            </p>
          )}
          <p>{status.message}</p>
          {status.payment_available && (
            <button className="primary" disabled={busy} onClick={checkout}>
              Abrir pagamento
            </button>
          )}
          <p className="footnote">
            Criar cobrança ou voltar do checkout não libera o sistema. A
            liberação depende da confirmação validada do provedor.
          </p>
        </section>
      )}
      <section className="panel">
        <div className="panel-heading">
          <h2>Minhas cobranças</h2>
          <button className="text-button" onClick={load}>
            Atualizar
          </button>
        </div>
        {!invoices.items.length ? (
          <Empty text="Nenhuma cobrança gerada." />
        ) : (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Referência</th>
                  <th>Valor</th>
                  <th>Situação</th>
                </tr>
              </thead>
              <tbody>
                {invoices.items.map((i) => (
                  <tr key={i.id}>
                    <td>{i.provider_reference}</td>
                    <td>{money(i.amount_cents)}</td>
                    <td>
                      {i.status === "paid"
                        ? "Confirmada"
                        : i.status === "pending"
                          ? "Pendente"
                          : "Cancelada"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <Pagination page={page} total={invoices.total} change={setPage} />
      </section>
    </>
  );
}
