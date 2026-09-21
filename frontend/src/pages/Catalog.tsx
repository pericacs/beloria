import { FormEvent, useEffect, useState } from "react";
import { Plus, Pencil } from "lucide-react";
import { api, options } from "../api";
import { Page, Row, money } from "../types";
import { Empty, Message, Modal, Pagination } from "../components/Common";
const labels: Record<string, string> = {
  specialties: "Especialidades",
  professionals: "Profissionais",
  clients: "Clientes",
  services: "Serviços",
};
export function Catalog({ kind }: { kind: string }) {
  const [data, setData] = useState<Page<Row>>({
      items: [],
      total: 0,
      page: 1,
      page_size: 25,
    }),
    [page, setPage] = useState(1),
    [loading, setLoading] = useState(true),
    [error, setError] = useState(""),
    [success, setSuccess] = useState(""),
    [editing, setEditing] = useState<Row | null | undefined>(),
    [specialties, setSpecialties] = useState<Row[]>([]),
    [saving, setSaving] = useState(false),
    [formError, setFormError] = useState("");
  async function load() {
    setLoading(true);
    setError("");
    try {
      const [rows, specs] = await Promise.all([
        api<Page<Row>>(`/${kind}?page=${page}`),
        kind === "services" || kind === "professionals"
          ? options("/specialties")
          : Promise.resolve([]),
      ]);
      setData(rows);
      setSpecialties(specs);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    void load();
  }, [kind, page]);
  function edit(row: Row | null) {
    setFormError("");
    setEditing(row);
  }
  async function save(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setSaving(true);
    setFormError("");
    const form = new FormData(e.currentTarget);
    const body: Record<string, unknown> = {
      name: form.get("name"),
      active: form.get("active") === "on",
    };
    if (kind === "clients" || kind === "professionals")
      body.contact = form.get("contact");
    if (kind === "services") {
      body.specialty_id = Number(form.get("specialty_id"));
      body.price_cents = Math.round(Number(form.get("price")) * 100);
    }
    if (kind === "professionals") {
      Object.assign(body, {
        commission_bps: Math.round(Number(form.get("commission")) * 100),
        engagement: form.get("engagement"),
        cpf: form.get("cpf") || null,
        cnpj: form.get("cnpj") || null,
        specialty_ids: form.getAll("specialty_ids").map(Number),
        email: form.get("email"),
      });
      if (form.get("password")) body.password = form.get("password");
    }
    try {
      await api(
        `/${kind}${editing ? "/" + editing.id : ""}`,
        editing ? "PUT" : "POST",
        body,
      );
      setEditing(undefined);
      setSuccess("Cadastro salvo com sucesso.");
      await load();
    } catch (e) {
      setFormError((e as Error).message);
    } finally {
      setSaving(false);
    }
  }
  return (
    <>
      <div className="page-heading">
        <div>
          <p className="eyebrow">Organize seu negócio</p>
          <h1>{labels[kind]}</h1>
          <p>Cadastros que fazem parte da sua operação.</p>
        </div>
        <button className="primary" onClick={() => edit(null)}>
          <Plus size={18} /> Novo cadastro
        </button>
      </div>
      <Message error={error} success={success} />
      <section className="panel">
        <div className="panel-heading">
          <h2>{labels[kind]} cadastrados</h2>
          <span className="count">{data.total}</span>
        </div>
        {loading ? (
          <p className="loading" role="status">
            Carregando cadastros…
          </p>
        ) : data.items.length ? (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Nome</th>
                  <th>Detalhes</th>
                  <th>Situação</th>
                  <th>Ações</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((row) => (
                  <tr key={row.id}>
                    <td>
                      <strong>{row.name}</strong>
                    </td>
                    <td>
                      {kind === "services"
                        ? money(row.price_cents)
                        : kind === "professionals"
                          ? `${(row.commission_bps / 100).toLocaleString("pt-BR")}% · ${row.engagement === "autonomo" ? "Autônomo" : row.engagement}`
                          : row.contact || "—"}
                    </td>
                    <td>
                      <span
                        className={`badge ${row.active ? "approved" : "rejected"}`}
                      >
                        {row.active ? "Ativo" : "Inativo"}
                      </span>
                    </td>
                    <td>
                      <button className="text-button" onClick={() => edit(row)}>
                        <Pencil size={14} /> Editar
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <Empty />
        )}
        <Pagination page={page} total={data.total} change={setPage} />
      </section>
      {editing !== undefined && (
        <Modal
          title={editing ? "Editar cadastro" : "Novo cadastro"}
          close={() => setEditing(undefined)}
        >
          <form onSubmit={save}>
            <Message error={formError} />
            <label>
              Nome
              <input
                autoFocus
                name="name"
                required
                maxLength={120}
                defaultValue={editing?.name}
              />
            </label>
            {(kind === "clients" || kind === "professionals") && (
              <label>
                Contato
                <input
                  name="contact"
                  maxLength={160}
                  defaultValue={editing?.contact}
                />
              </label>
            )}
            {kind === "services" && (
              <>
                <label>
                  Especialidade
                  <select
                    aria-label="Especialidade"
                    name="specialty_id"
                    required
                    defaultValue={editing?.specialty_id || ""}
                  >
                    <option value="">Selecione</option>
                    {specialties
                      .filter((s) => s.active || s.id === editing?.specialty_id)
                      .map((s) => (
                        <option key={s.id} value={s.id}>
                          {s.name}
                          {!s.active ? " (inativa)" : ""}
                        </option>
                      ))}
                  </select>
                </label>
                <label>
                  Preço (R$)
                  <input
                    name="price"
                    type="number"
                    min="0"
                    max="1000000"
                    step="0.01"
                    required
                    defaultValue={editing ? editing.price_cents / 100 : ""}
                  />
                </label>
              </>
            )}
            {kind === "professionals" && (
              <>
                <div className="form-grid">
                  <label>
                    Comissão (%)
                    <input
                      name="commission"
                      type="number"
                      min="0"
                      max="100"
                      step="0.01"
                      required
                      defaultValue={editing ? editing.commission_bps / 100 : ""}
                    />
                  </label>
                  <label>
                    Vínculo
                    <select
                      aria-label="Vínculo"
                      name="engagement"
                      defaultValue={editing?.engagement || "autonomo"}
                    >
                      <option value="autonomo">Autônomo</option>
                      <option value="MEI">MEI</option>
                      <option value="CLT">CLT</option>
                    </select>
                  </label>
                  <label>
                    CPF
                    <input
                      name="cpf"
                      defaultValue={editing?.cpf || ""}
                      maxLength={18}
                    />
                  </label>
                  <label>
                    CNPJ
                    <input
                      name="cnpj"
                      defaultValue={editing?.cnpj || ""}
                      maxLength={18}
                    />
                  </label>
                </div>
                <small>
                  MEI exige CNPJ; autônomo e CLT exigem CPF. CNPJ numérico ou
                  alfanumérico.
                </small>
                <fieldset>
                  <legend>Especialidades</legend>
                  {specialties.length === 0 ? (
                    <p>Cadastre uma especialidade primeiro.</p>
                  ) : (
                    specialties
                      .filter(
                        (s) =>
                          s.active || editing?.specialty_ids.includes(s.id),
                      )
                      .map((s) => (
                        <label className="check" key={s.id}>
                          <input
                            name="specialty_ids"
                            type="checkbox"
                            value={s.id}
                            defaultChecked={editing?.specialty_ids.includes(
                              s.id,
                            )}
                          />
                          {s.name}
                          {!s.active ? " (inativa)" : ""}
                        </label>
                      ))
                  )}
                </fieldset>
                <label>
                  E-mail de acesso
                  <input
                    name="email"
                    type="email"
                    required
                    defaultValue={editing?.email}
                    autoComplete="off"
                  />
                </label>
                <label>
                  {editing ? "Nova senha (opcional)" : "Senha de acesso"}
                  <input
                    name="password"
                    type="password"
                    minLength={12}
                    maxLength={128}
                    required={!editing}
                    autoComplete="new-password"
                  />
                </label>
                <small>
                  Mínimo de 12 caracteres. Cada profissional tem seu próprio
                  acesso.
                </small>
              </>
            )}
            <label className="check">
              <input
                name="active"
                type="checkbox"
                defaultChecked={editing?.active ?? true}
              />
              Cadastro ativo
            </label>
            <div className="form-actions">
              <button
                type="button"
                className="secondary"
                onClick={() => setEditing(undefined)}
              >
                Cancelar
              </button>
              <button className="primary" disabled={saving}>
                {saving ? "Salvando…" : "Salvar cadastro"}
              </button>
            </div>
          </form>
        </Modal>
      )}
    </>
  );
}
