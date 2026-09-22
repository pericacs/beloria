import { Page, Row } from "./types";
let csrf = "";
export function setCsrf(value: string) {
  csrf = value;
}
export async function api<T>(
  path: string,
  method = "GET",
  body?: unknown,
  key?: string,
): Promise<T> {
  const response = await fetch("/api" + path, {
    method,
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      "X-CSRF-Token": csrf,
      ...(key ? { "Idempotency-Key": key } : {}),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    if (response.status === 402)
      window.dispatchEvent(new Event("access-changed"));
    if (response.status === 401 && path !== "/auth/login")
      window.dispatchEvent(new Event("session-expired"));
    const detail = Array.isArray(data.detail)
      ? data.detail
          .map((x: any) => `${x.loc?.slice(1).join(".")}: ${x.msg}`)
          .join("; ")
      : data.detail;
    throw new Error(detail || "Não foi possível concluir. Tente novamente.");
  }
  return response.status === 204 ? (undefined as T) : response.json();
}
export async function options(path: string): Promise<Row[]> {
  let result: Row[] = [],
    page = 1;
  for (;;) {
    const response = await api<Page<Row>>(`${path}?page=${page}&page_size=100`);
    result = result.concat(response.items);
    if (result.length >= response.total) return result;
    page++;
  }
}
