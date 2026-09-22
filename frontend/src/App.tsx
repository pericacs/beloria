import { useEffect, useRef, useState } from "react";
import { api, setCsrf } from "./api";
import { AuthResult, User } from "./types";
import { ClientPanel } from "./ClientPanel";
import { Login } from "./pages/Login";
import { BusinessSelection } from "./pages/BusinessSelection";
import { PublicSignup, InvitationSignup } from "./pages/PublicSignup";
import { PlatformPanel } from "./pages/PlatformPanel";
import { SpecialistPanel } from "./pages/SpecialistPanel";
import { BillingPage } from "./pages/BillingPage";
import { Message } from "./components/Common";

export default function App() {
  const [auth, setAuth] = useState<AuthResult | null>(null),
    [loading, setLoading] = useState(true),
    [error, setError] = useState(""),
    [invite, setInvite] = useState(
      location.pathname.match(/^\/convite\/([\w-]+)$/)?.[1] || "",
    );
  const choosing = useRef(false);
  function accept(value: AuthResult) {
    setCsrf(value.csrf_token);
    setAuth(value);
    setError("");
  }
  async function refresh() {
    try {
      const value = await api<AuthResult>("/auth/me");
      if (!choosing.current) accept(value);
    } catch {
    } finally {
      setLoading(false);
    }
  }
  async function logout() {
    try {
      await api("/auth/logout", "POST");
      choosing.current = false;
      setAuth(null);
      setCsrf("");
      history.replaceState(null, "", "/login");
    } catch (e) {
      setError((e as Error).message);
    }
  }
  useEffect(() => {
    void refresh();
    const timer = setInterval(() => {
      void refresh();
    }, 15000);
    const expired = () => {
      setAuth(null);
      setCsrf("");
    };
    const changed = () => {
      void refresh();
    };
    window.addEventListener("session-expired", expired);
    window.addEventListener("access-changed", changed);
    return () => {
      clearInterval(timer);
      window.removeEventListener("session-expired", expired);
      window.removeEventListener("access-changed", changed);
    };
  }, []);
  useEffect(() => {
    if (!auth || invite) return;
    const dest = auth.selection_required ? "select" : auth.destination;
    const paths: Record<string, string> = {
      platform: "/beloria",
      client: "/empresa",
      specialist: "/especialista",
      waiting: "/especialista/aguardando",
      payment: "/empresa/assinatura",
      suspended: "/especialista/suspenso",
      conflict: "/acesso-em-analise",
      select: "/selecionar-empresa",
    };
    history.replaceState(null, "", paths[dest]);
  }, [auth, invite]);
  if (loading) return <div className="app-loading">Carregando Beloria…</div>;
  if (invite)
    return (
      <InvitationSignup
        token={invite}
        session={auth}
        login={accept}
        done={(value) => {
          setInvite("");
          accept(value);
        }}
      />
    );
  if (!auth)
    return location.pathname === "/cadastro" ? (
      <PublicSignup done={accept} />
    ) : (
      <Login loggedIn={accept} />
    );
  if (auth.selection_required)
    return (
      <BusinessSelection
        session={auth}
        selected={(value) => {
          choosing.current = false;
          accept(value);
        }}
        logout={logout}
        logoutError={error}
      />
    );
  const user = auth as User;
  if (user.destination === "platform") return <PlatformPanel logout={logout} />;
  if (user.destination === "client")
    return (
      <ClientPanel
        key={user.id}
        user={user}
        logout={logout}
        chooseBusiness={() => {
          choosing.current = true;
          setAuth({
            selection_required: true,
            email: user.email,
            csrf_token: user.csrf_token,
            businesses: user.businesses,
          });
        }}
      />
    );
  if (user.destination === "specialist")
    return <SpecialistPanel user={user} logout={logout} />;
  return (
    <main className="access-screen">
      <div className="access-top">
        <a className="wordmark" href="/">
          beloria.
        </a>
        <button className="secondary" onClick={logout}>
          Sair
        </button>
      </div>
      <Message error={error} />
      {user.destination === "payment" ? (
        <BillingPage />
      ) : (
        <section className="panel access-message">
          <p className="eyebrow">Painel do especialista</p>
          <h1>
            {user.destination === "suspended"
              ? "Acesso suspenso"
              : user.destination === "conflict"
                ? "Vínculos em análise"
                : user.request_state === "rejected"
                  ? "Solicitação não aprovada"
                  : "Aguardando aprovação"}
          </h1>
          <p>
            {user.destination === "suspended"
              ? "Acesso suspenso. Entre em contato com o responsável pela empresa."
              : user.destination === "conflict"
                ? "Há vínculos preexistentes com mais de uma empresa. O administrador precisa analisá-los; seu histórico foi preservado."
                : user.request_state === "rejected"
                  ? user.rejection_reason
                  : "Seu cadastro foi enviado. O responsável pela empresa precisa aprovar seu vínculo antes de liberar os atendimentos e valores."}
          </p>
          <button className="secondary" onClick={refresh}>
            Atualizar situação
          </button>
        </section>
      )}
    </main>
  );
}
