import { useEffect, useState } from "react";
import {
  CircleDollarSign,
  Flower2,
  Home as HomeIcon,
  LogOut,
  Menu,
  ReceiptText,
  Scissors,
  Shapes,
  ShieldCheck,
  Users,
  UsersRound,
  Wallet,
  X,
} from "lucide-react";
import { api, setCsrf } from "./api";
import { AuthResult, Selection, User } from "./types";
import { Home } from "./pages/Home";
import { Catalog } from "./pages/Catalog";
import { Attendances } from "./pages/Attendances";
import { History } from "./pages/History";
import { Login } from "./pages/Login";
import { BusinessSelection } from "./pages/BusinessSelection";
import { Message } from "./components/Common";
const navigation = [
  ["home", "Visão geral", HomeIcon],
  ["attendances", "Atendimentos", ReceiptText],
  ["commissions", "Comissões", CircleDollarSign],
  ["payouts", "Repasses", Wallet],
  ["professionals", "Profissionais", UsersRound],
  ["clients", "Clientes", Users],
  ["services", "Serviços", Scissors],
  ["specialties", "Especialidades", Shapes],
  ["audit", "Auditoria", ShieldCheck],
] as const;
export default function App() {
  const [user, setUser] = useState<User | null>(null),
    [selection, setSelection] = useState<Selection | null>(null),
    [loading, setLoading] = useState(true),
    [page, setPage] = useState("home"),
    [mobile, setMobile] = useState(false),
    [error, setError] = useState("");
  function login(value: AuthResult) {
    setCsrf(value.csrf_token);
    setUser(value.selection_required ? null : value);
    setSelection(value.selection_required ? value : null);
    setMobile(false);
    setPage("home");
    setError("");
  }
  useEffect(() => {
    api<AuthResult>("/auth/me")
      .then(login)
      .catch(() => {})
      .finally(() => setLoading(false));
    const expired = () => {
      setUser(null);
      setSelection(null);
      setCsrf("");
    };
    window.addEventListener("session-expired", expired);
    return () => window.removeEventListener("session-expired", expired);
  }, []);
  function navigate(value: string) {
    setPage(value);
    setMobile(false);
    window.scrollTo(0, 0);
  }
  async function logout() {
    try {
      await api("/auth/logout", "POST");
      setUser(null);
      setSelection(null);
      setCsrf("");
    } catch (e) {
      setError((e as Error).message);
    }
  }
  if (loading)
    return (
      <div className="app-loading" role="status">
        Carregando Beloria…
      </div>
    );
  if (selection)
    return (
      <BusinessSelection
        session={selection}
        selected={login}
        logout={logout}
        logoutError={error}
      />
    );
  if (!user) return <Login loggedIn={login} />;
  const items = navigation.filter(
    ([key]) =>
      user.role === "gestor" ||
      ["home", "attendances", "commissions", "payouts"].includes(key),
  );
  return (
    <div className="app-shell">
      {mobile && (
        <button
          className="sidebar-overlay"
          aria-label="Fechar menu"
          onClick={() => setMobile(false)}
        />
      )}
      <aside className={`sidebar ${mobile ? "open" : ""}`}>
        <a
          className="brand"
          href="#"
          onClick={(e) => {
            e.preventDefault();
            navigate("home");
          }}
        >
          <Flower2 size={31} />
          <span>
            beloria<span className="brand-dot">.</span>
          </span>
        </a>
        <div className="workspace">
          <span className="workspace-avatar">
            {user.business_name.slice(0, 1).toUpperCase()}
          </span>
          <div>
            <strong>{user.business_name}</strong>
            <small>Seu espaço de gestão</small>
            {user.businesses.length > 1 && (
              <button
                className="switch-business"
                onClick={() =>
                  setSelection({
                    selection_required: true,
                    email: user.email,
                    csrf_token: user.csrf_token,
                    businesses: user.businesses,
                  })
                }
              >
                Trocar negócio
              </button>
            )}
          </div>
        </div>
        <p className="nav-label">PRINCIPAL</p>
        <nav aria-label="Navegação principal">
          {items.map(([key, label, Icon], i) => (
            <div key={key}>
              {i === 4 && <p className="nav-label">CADASTROS E CONTROLE</p>}
              <button
                className={page === key ? "active" : ""}
                aria-current={page === key ? "page" : undefined}
                onClick={() => navigate(key)}
              >
                <Icon size={19} />
                {label}
                {page === key && <span className="nav-dot" />}
              </button>
            </div>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <Flower2 size={23} />
          <p>
            Seu talento transforma.
            <br />
            <strong>A gente cuida da gestão.</strong>
          </p>
          <small>Beloria · versão 0.1</small>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <button
            className="icon-button menu-toggle"
            aria-label={mobile ? "Fechar menu" : "Abrir menu"}
            onClick={() => setMobile(!mobile)}
          >
            {mobile ? <X /> : <Menu />}
          </button>
          <span className="breadcrumb">
            Meu negócio <span>/</span>{" "}
            <strong>{navigation.find((x) => x[0] === page)?.[1]}</strong>
          </span>
          <div className="account">
            <span className="avatar">
              {user.email.slice(0, 1).toUpperCase()}
            </span>
            <div>
              <strong>
                {user.role === "gestor" ? "Gestor" : "Profissional"}
              </strong>
              <small>{user.email}</small>
            </div>
            <button
              className="icon-button"
              title="Sair"
              aria-label="Sair"
              onClick={logout}
            >
              <LogOut size={18} />
            </button>
          </div>
        </header>
        <main key={user.id} id="main-content" className="content">
          <Message error={error} />
          {page === "home" ? (
            <Home user={user} navigate={navigate} />
          ) : page === "attendances" || page === "commissions" ? (
            <Attendances
              key={page}
              user={user}
              commissions={page === "commissions"}
            />
          ) : page === "payouts" || page === "audit" ? (
            <History key={page} audit={page === "audit"} user={user} />
          ) : (
            <Catalog key={page} kind={page} />
          )}
          <footer>
            Beloria <span>Gestão com cuidado, para o seu negócio crescer.</span>
          </footer>
        </main>
      </div>
    </div>
  );
}
