import { useState } from "react";
import { Flower2 } from "lucide-react";
import { api } from "../api";
import { AuthResult, Selection } from "../types";
import { Message } from "../components/Common";

export function BusinessSelection({
  session,
  selected,
  logout,
  logoutError,
}: {
  session: Selection;
  selected: (result: AuthResult) => void;
  logout: () => Promise<void>;
  logoutError?: string;
}) {
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  async function choose(membership_id: number) {
    setBusy(true);
    setError("");
    try {
      selected(
        await api<AuthResult>("/auth/select-business", "POST", {
          membership_id,
        }),
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <main className="login-main business-selection">
      <section className="login-box">
        <span className="login-symbol">
          <Flower2 size={30} />
        </span>
        <h1>Escolha seu negócio</h1>
        <p>
          Você entrou como {session.email}. Selecione onde deseja trabalhar.
        </p>
        <Message error={error || logoutError} />
        <div className="business-choices">
          {session.businesses.map((b) => (
            <button
              className="secondary"
              disabled={busy}
              key={b.membership_id}
              onClick={() => choose(b.membership_id)}
            >
              <strong>{b.name}</strong>
              <span>{b.role === "gestor" ? "Gestor" : "Profissional"}</span>
            </button>
          ))}
        </div>
        {!session.businesses.length && (
          <p>Nenhum vínculo ativo. Contate o administrador.</p>
        )}
        <button
          className="text-button"
          disabled={busy}
          onClick={async () => {
            try {
              await logout();
            } catch (e) {
              setError((e as Error).message);
            }
          }}
        >
          Sair
        </button>
        {busy && <p role="status">Abrindo negócio…</p>}
      </section>
    </main>
  );
}
