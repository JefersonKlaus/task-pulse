// Every call to the backend. The frontend doesn't know whether the backend is AWS or local: it calls CONFIG.apiUrl.
import { CONFIG } from "./config.js";
import { signOut, token } from "./auth.js";
import { lang, t } from "./i18n.js";
import type { BillingReport, Company, PaymentList, Project, Task, TaskList } from "./types.js";

type Method = "GET" | "POST" | "PUT" | "DELETE";
type Query = Record<string, string | null | undefined>;

/** Calls the API with the login token. Throws an Error with the server's message, in the chosen language
 *  (Accept-Language). */
export async function api<T>(method: Method, path: string, body?: unknown, query?: Query): Promise<T> {
  const jwt = await token();
  if (!jwt) { location.reload(); throw new Error(t("Sessão expirada.")); }
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query || {})) if (value) params.set(key, value);
  const url = CONFIG.apiUrl.replace(/\/$/, "") + path + (params.size ? `?${params}` : "");
  let response: Response;
  try {
    response = await fetch(url, {
      method,
      headers: { Authorization: `Bearer ${jwt}`, "Accept-Language": lang(),
        ...(body ? { "Content-Type": "application/json" } : {}) },
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new Error(t("Sem conexão com o servidor."));
  }
  if (response.status === 401 && !CONFIG.skipLogin) { signOut(); location.reload(); throw new Error(t("Sessão expirada.")); }
  if (response.status === 204) return null as T;
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error((data as { error?: string }).error || t("Algo deu errado. Tente de novo."));
  return data as T;
}

export interface Period { from: string; to: string }

export const companies = {
  list: () => api<Company[]>("GET", "/companies"),
  create: (body: Partial<Company>) => api<Company>("POST", "/companies", body),
  update: (id: string, body: Partial<Company>) => api<Company>("PUT", `/companies/${id}`, body),
  remove: (id: string) => api<null>("DELETE", `/companies/${id}`),
};

export const projects = {
  list: (companyId?: string) => api<Project[]>("GET", "/projects", undefined, { company_id: companyId }),
  get: (id: string) => api<Project>("GET", `/projects/${id}`),
  create: (body: unknown) => api<Project>("POST", "/projects", body),
  update: (id: string, body: unknown) => api<Project>("PUT", `/projects/${id}`, body),
  remove: (id: string) => api<null>("DELETE", `/projects/${id}`),
  createRule: (id: string, body: unknown) => api<Project>("POST", `/projects/${id}/rules`, body),
  updateRule: (id: string, ruleId: string, body: unknown) => api<Project>("PUT", `/projects/${id}/rules/${ruleId}`, body),
  removeRule: (id: string, ruleId: string) => api<Project>("DELETE", `/projects/${id}/rules/${ruleId}`),
};

export interface TaskFilter { company_id?: string; project_id?: string; from?: string; to?: string; state?: string }

export const tasks = {
  list: (filter: TaskFilter) => api<TaskList>("GET", "/tasks", undefined, { ...filter }),
  create: (projectId: string, body: unknown) => api<Task>("POST", `/projects/${projectId}/tasks`, body),
  update: (projectId: string, id: string, body: unknown) => api<Task>("PUT", `/projects/${projectId}/tasks/${id}`, body),
  remove: (projectId: string, id: string) => api<null>("DELETE", `/projects/${projectId}/tasks/${id}`),
  addTime: (projectId: string, id: string, body: { minutes: number; finish?: boolean; finished_at?: string }) =>
    api<Task>("POST", `/projects/${projectId}/tasks/${id}/time`, body),
};

export const billing = {
  get: (projectId: string, period: Period) => api<BillingReport>("GET", `/projects/${projectId}/billing`, undefined, { ...period }),
  pay: (projectId: string, body: unknown) => api<BillingReport>("POST", `/projects/${projectId}/payments`, body),
  payments: (filter: { company_id?: string; project_id?: string }) => api<PaymentList>("GET", "/payments", undefined, filter),
  removePayment: (projectId: string, id: string) => api<null>("DELETE", `/projects/${projectId}/payments/${id}`),
};
