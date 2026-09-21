import { ReactNode, useEffect, useRef } from "react";
import { X } from "lucide-react";
export function Modal({
  title,
  children,
  close,
}: {
  title: string;
  children: ReactNode;
  close: () => void;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const el = ref.current;
    el?.showModal();
    return () => el?.close();
  }, []);
  return (
    <dialog ref={ref} onCancel={close} aria-labelledby="dialog-title">
      <div className="modal-heading">
        <h2 id="dialog-title">{title}</h2>
        <button
          type="button"
          className="icon-button"
          aria-label="Fechar"
          onClick={close}
        >
          <X size={20} />
        </button>
      </div>
      {children}
    </dialog>
  );
}
export function Message({
  error,
  success,
}: {
  error?: string;
  success?: string;
}) {
  return (
    <>
      {error && (
        <div role="alert" className="message error">
          {error}
        </div>
      )}
      {success && (
        <div role="status" className="message success">
          {success}
        </div>
      )}
    </>
  );
}
export function Empty({
  text = "Nenhum registro encontrado.",
}: {
  text?: string;
}) {
  return (
    <div className="empty">
      <span className="empty-mark">◇</span>
      <p>{text}</p>
      <small>Seus dados aparecerão aqui.</small>
    </div>
  );
}
export function Pagination({
  page,
  total,
  change,
  size = 25,
}: {
  page: number;
  total: number;
  change: (page: number) => void;
  size?: number;
}) {
  return (
    <div className="pagination">
      <small>
        {total} registro{total !== 1 ? "s" : ""} · Página {page} de{" "}
        {Math.max(1, Math.ceil(total / size))}
      </small>
      <div>
        <button
          className="secondary"
          disabled={page <= 1}
          onClick={() => change(page - 1)}
        >
          Anterior
        </button>
        <button
          className="secondary"
          disabled={page * size >= total}
          onClick={() => change(page + 1)}
        >
          Próxima
        </button>
      </div>
    </div>
  );
}
