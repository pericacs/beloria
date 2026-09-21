import { FormEvent, useState } from "react";
import { ArrowRight, Flower2, ShieldCheck } from "lucide-react";
import { api } from "../api";
import { User } from "../types";
import { Message } from "../components/Common";
export function Login({ loggedIn }: { loggedIn: (user: User) => void }) {
  const [error, setError] = useState(""),
    [loading, setLoading] = useState(false);
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    setLoading(true);
    setError("");
    try {
      loggedIn(
        await api<User>("/auth/login", "POST", {
          business: form.get("business"),
          email: form.get("email"),
          password: form.get("password"),
        }),
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }
  return (
    <div className="login-page">
      <section className="login-story">
        <div className="brand">
          <Flower2 size={35} />
          <span>
            beloria<span className="brand-dot">.</span>
          </span>
        </div>
        <div>
          <p className="eyebrow">Gestão para quem cuida</p>
          <h1>
            Mais clareza.
            <br />
            Mais tempo para
            <br />
            <em>fazer florescer.</em>
          </h1>
          <p>
            O cuidado com o seu negócio começa aqui.
            <br />
            Operação, profissionais e finanças em um só lugar.
          </p>
        </div>
        <small>Feito para o universo da beleza.</small>
      </section>
      <main className="login-main">
        <div className="login-box">
          <span className="login-symbol">
            <Flower2 size={30} />
          </span>
          <h2>Bem-vindo ao Beloria</h2>
          <p>Entre para acompanhar o seu negócio.</p>
          <form onSubmit={submit}>
            <Message error={error} />
            <label>
              Identificador do negócio
              <input
                name="business"
                required
                autoFocus
                autoComplete="organization"
                placeholder="Ex.: meu-salao"
                maxLength={80}
              />
            </label>
            <label>
              E-mail
              <input
                name="email"
                type="email"
                required
                autoComplete="username"
                placeholder="Seu e-mail de acesso"
              />
            </label>
            <label>
              Senha
              <input
                name="password"
                type="password"
                required
                autoComplete="current-password"
                maxLength={128}
              />
            </label>
            <button className="primary" disabled={loading}>
              {loading ? "Entrando…" : "Entrar"}
              <ArrowRight size={18} />
            </button>
          </form>
          <p className="login-note">
            <ShieldCheck size={16} /> Acesso individual e seguro.
          </p>
          <small>Precisa de acesso? Fale com o gestor do seu negócio.</small>
        </div>
      </main>
    </div>
  );
}
