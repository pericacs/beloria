export type BusinessChoice = {
  membership_id: number;
  name: string;
  role: "gestor" | "profissional";
};
export type Selection = {
  selection_required: true;
  email: string;
  csrf_token: string;
  businesses: BusinessChoice[];
};
export type AuthResult = User | Selection;
export type User = {
  selection_required: false;
  businesses: BusinessChoice[];
  id: number;
  email: string;
  role: "gestor" | "profissional";
  professional_id: number | null;
  business_name: string;
  csrf_token: string;
};
export type Row = {
  id: number;
  name: string;
  active: boolean;
  [key: string]: any;
};
export type Page<T> = {
  items: T[];
  total: number;
  page: number;
  page_size: number;
};
export type Attendance = {
  id: number;
  professional_id: number;
  professional_name: string;
  client_name: string;
  service_name: string;
  price_cents: number;
  commission_bps: number;
  commission_cents: number;
  payment_method: string;
  status: string;
  rejection_reason: string | null;
  created_at: string;
  paid: boolean;
};
export type Dashboard = {
  attendance_count: number;
  revenue_cents: number;
  pending_cents: number;
  payable_cents: number;
  paid_cents: number;
  series: { day: string; revenue_cents: number }[];
};
export type Filters = { start: string; end: string; professional_id: string };
export const money = (cents: number) =>
  new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(
    cents / 100,
  );
export const dateTime = (value: string) =>
  new Date(value).toLocaleString("pt-BR");
export const statusName: Record<string, string> = {
  pending: "Pendente",
  approved: "Aprovado",
  rejected: "Rejeitado",
};
export function query(filters: Filters) {
  return new URLSearchParams(
    Object.entries(filters).filter(([, v]) => v),
  ).toString();
}
