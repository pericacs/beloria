import { FormEvent, useEffect, useState } from "react";
import { api } from "../api";
import { AuthResult } from "../types";
import { Message } from "../components/Common";
import { Login } from "./Login";

function ProfileFields() {
  return (
    <>
      <label>
        Nome completo
        <input name="name" required maxLength={160} />
      </label>
      <label>
        Contato
        <input name="contact" maxLength={160} />
      </label>
      <label>
        Vínculo
        <select name="engagement" aria-label="Vínculo">
          <option value="autonomo">Autônomo</option>
          <option value="MEI">MEI</option>
          <option value="CLT">CLT</option>
        </select>
      </label>
      <div className="form-grid">
        <label>
          CPF
          <input name="cpf" maxLength={18} />
        </label>
        <label>
          CNPJ
          <input name="cnpj" maxLength={18} />
        </label>
      </div>
      <p className="footnote">
        MEI: CNPJ obrigatório. Autônomo ou CLT: CPF obrigatório. Especialidades
        e comissão serão definidas pelo responsável.
      </p>
    </>
  );
}
function Credentials() {
  return (
    <>
      <label>
        E-mail
        <input name="email" type="email" autoComplete="username" required />
      </label>
      <label>
        Senha
        <input
          name="password"
          type="password"
          autoComplete="new-password"
          minLength={12}
          maxLength={128}
          required
        />
      </label>
    </>
  );
}

export function PublicSignup({ done }: { done: (result: AuthResult) => void }) {
  const [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setError("");
    const f = new FormData(e.currentTarget);
    try {
      done(
        await api<AuthResult>("/public/signup", "POST", {
          company_name: f.get("company_name"),
          responsible_name: f.get("responsible_name"),
          contact: f.get("contact"),
          email: f.get("email"),
          password: f.get("password"),
        }),
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <main className="signup-page">
      <section className="signup-story">
        <a href="/login" className="wordmark">
          beloria.
        </a>
        <p className="eyebrow">Um novo começo para seu negócio</p>
        <h1>
          Seu talento.
          <br />
          Sua empresa.
          <br />
          <em>Tudo em ordem.</em>
        </h1>
        <p>
          Organize sua operação, acompanhe sua equipe e tenha clareza sobre cada
          resultado.
        </p>
        <div className="trial-note">
          <strong>15 dias para conhecer</strong>
          <span>Sem cartão. Sem cobranças automáticas no cadastro.</span>
        </div>
      </section>
      <section className="signup-form">
        <h2>Crie a conta da sua empresa</h2>
        <p>
          Já tem acesso? <a href="/login">Entrar</a>
        </p>
        <form onSubmit={submit}>
          <Message error={error} />
          <label>
            Nome da empresa
            <input
              name="company_name"
              autoComplete="organization"
              required
              maxLength={160}
            />
          </label>
          <label>
            Nome do responsável
            <input
              name="responsible_name"
              autoComplete="name"
              required
              maxLength={160}
            />
          </label>
          <label>
            Contato da empresa (opcional)
            <input name="contact" maxLength={160} />
          </label>
          <Credentials />
          <p className="footnote">
            Nome da empresa, responsável, e-mail e senha são obrigatórios. Sua
            avaliação começa na conclusão do cadastro.
          </p>
          <button className="primary" disabled={busy}>
            {busy ? "Criando conta…" : "Começar meus 15 dias"}
          </button>
        </form>
      </section>
    </main>
  );
}

export function InvitationSignup({
  token,
  session,
  login,
  done,
}: {
  token: string;
  session: AuthResult | null;
  login: (v: AuthResult) => void;
  done: (v: AuthResult) => void;
}) {
  const [company, setCompany] = useState(""),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [existing, setExisting] = useState(false),
    [loaded, setLoaded] = useState(false);
  useEffect(() => {
    api<{ company_name: string }>(`/public/invitations/${token}`)
      .then((v) => setCompany(v.company_name))
      .catch((e) => setError(e.message))
      .finally(() => setLoaded(true));
  }, [token]);
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setError("");
    const f = new FormData(e.currentTarget);
    const profile = {
      name: f.get("name"),
      contact: f.get("contact"),
      engagement: f.get("engagement"),
      cpf: f.get("cpf") || null,
      cnpj: f.get("cnpj") || null,
    };
    try {
      if (session) {
        await api(`/invitations/${token}/apply`, "POST", profile);
        done(await api<AuthResult>("/auth/me"));
      } else
        done(
          await api<AuthResult>(`/public/invitations/${token}/signup`, "POST", {
            ...profile,
            email: f.get("email"),
            password: f.get("password"),
          }),
        );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  if (existing && !session)
    return (
      <>
        <div className="invite-login-note">
          Entre na sua conta para solicitar vínculo com {company}.
        </div>
        <Login loggedIn={login} />
      </>
    );
  return (
    <main className="invite-page">
      <section className="panel">
        <a href="/login" className="wordmark">
          beloria.
        </a>
        <p className="eyebrow">Convite para especialista</p>
        <h1>{company || "Carregando convite…"}</h1>
        <Message error={error} />
        {loaded && company && (
          <>
            <p>
              Faça parte da equipe. Seu acesso depende da aprovação do
              responsável.
            </p>
            {!session && (
              <button className="secondary" onClick={() => setExisting(true)}>
                Já tenho conta — entrar
              </button>
            )}
            <form onSubmit={submit}>
              <ProfileFields />
              {!session && <Credentials />}
              <button className="primary" disabled={busy}>
                {busy ? "Enviando…" : "Solicitar vínculo"}
              </button>
            </form>
          </>
        )}
        {loaded && !company && <a href="/login">Voltar para o login</a>}
      </section>
    </main>
  );
}
