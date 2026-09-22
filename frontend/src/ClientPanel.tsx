import { useState } from "react";
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

import { User } from "./types";
import { Home } from "./pages/Home";
import { Catalog } from "./pages/Catalog";
import { Attendances } from "./pages/Attendances";
import { History } from "./pages/History";
import { Invitations } from "./pages/Invitations";
import { BillingPage } from "./pages/BillingPage";

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
  ["invitations", "Convites e aprovações", UsersRound],
  ["billing", "Assinatura", Wallet],
  ["audit", "Auditoria", ShieldCheck],
] as const;
export function ClientPanel({
  user,
  logout,
  chooseBusiness,
}: {
  user: User;
  logout: () => Promise<void>;
  chooseBusiness: () => void;
}) {
  const [page, setPage] = useState("home"),
    [mobile, setMobile] = useState(false);
  function navigate(value: string) {
    setPage(value);
    setMobile(false);
    window.scrollTo(0, 0);
  }
  const error = "";
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
              <button className="switch-business" onClick={chooseBusiness}>
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
          {page === "invitations" ? (
            <Invitations />
          ) : page === "billing" ? (
            <BillingPage />
          ) : page === "home" ? (
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
