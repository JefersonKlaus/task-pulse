// The filters every page shares: company, project and period (month or week, with ‹ › to move).
// They are kept while the app is open, so going from Tarefas to Faturamento keeps the same choice.
import type { Period } from "../api.js";
import type { Company, Project } from "../types.js";
import { addDays, h, today } from "../util.js";

export type PeriodKind = "month" | "week";

export const state = {
  companyId: "",
  projectId: "",
  kind: "month" as PeriodKind,
  anchor: today(),            // any day inside the period shown
};

const MONTHS = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro",
  "outubro", "novembro", "dezembro"];

/** The month or the week (Monday to Sunday) that contains `anchor`. */
export function periodOf(kind: PeriodKind, anchor: string): Period {
  if (kind === "month") {
    const [y, m] = anchor.split("-").map(Number) as [number, number];
    const last = new Date(Date.UTC(y, m, 0)).getUTCDate();
    const month = String(m).padStart(2, "0");
    return { from: `${y}-${month}-01`, to: `${y}-${month}-${String(last).padStart(2, "0")}` };
  }
  const weekday = (new Date(`${anchor}T12:00:00Z`).getUTCDay() + 6) % 7;      // Monday = 0
  const from = addDays(anchor, -weekday);
  return { from, to: addDays(from, 6) };
}

export function periodLabel(kind: PeriodKind, anchor: string): string {
  const { from, to } = periodOf(kind, anchor);
  if (kind === "month") return `${MONTHS[Number(from.slice(5, 7)) - 1]} de ${from.slice(0, 4)}`;
  return `${from.slice(8, 10)}/${from.slice(5, 7)} a ${to.slice(8, 10)}/${to.slice(5, 7)}/${to.slice(0, 4)}`;
}

export const currentPeriod = (): Period => periodOf(state.kind, state.anchor);

function shift(direction: number): void {
  if (state.kind === "week") state.anchor = addDays(state.anchor, 7 * direction);
  else {
    const [y, m] = state.anchor.split("-").map(Number) as [number, number];
    const d = new Date(Date.UTC(y, m - 1 + direction, 1));
    state.anchor = d.toISOString().slice(0, 10);
  }
}

export interface FilterOptions {
  companies: Company[];
  projects: Project[];
  /** Faturamento needs one project; Tarefas and Pagamentos may show all. */
  requireProject?: boolean;
  showPeriod?: boolean;
  onchange: () => void;
}

/** The filter bar. Changing anything updates `state` and calls `onchange`. */
export function filterBar({ companies, projects, requireProject = false, showPeriod = true, onchange }: FilterOptions):
  HTMLElement {
  if (state.companyId && !companies.some((c) => c.id === state.companyId)) state.companyId = "";
  const visible = () => projects.filter((p) => !state.companyId || p.company_id === state.companyId);
  if (state.projectId && !visible().some((p) => p.id === state.projectId)) state.projectId = "";
  if (requireProject && !state.projectId) state.projectId = visible()[0]?.id || "";

  const company = h("select", { id: "filter-company", onchange: () => {
    state.companyId = company.value;
    state.projectId = "";
    if (requireProject) state.projectId = visible()[0]?.id || "";
    drawProjects();
    onchange();
  } }, h("option", { value: "" }, "Todas as empresas"),
  companies.map((c) => h("option", { value: c.id, selected: c.id === state.companyId }, c.name)));

  const project = h("select", { id: "filter-project", onchange: () => { state.projectId = project.value; onchange(); } });
  const drawProjects = () => {
    project.replaceChildren(...[
      !requireProject && h("option", { value: "" }, "Todos os projetos"),
      ...visible().map((p) => h("option", { value: p.id, selected: p.id === state.projectId },
        state.companyId ? p.name : `${p.name} · ${p.company_name}`)),
    ].filter((o): o is HTMLOptionElement => Boolean(o)));
    project.value = state.projectId;
  };
  drawProjects();

  const kind = h("select", { id: "filter-kind", onchange: () => {
    state.kind = kind.value as PeriodKind;
    drawLabel();
    onchange();
  } }, h("option", { value: "month", selected: state.kind === "month" }, "Mês"),
  h("option", { value: "week", selected: state.kind === "week" }, "Semana"));
  const label = h("strong", { id: "period-label", className: "period-label" });
  const drawLabel = () => { label.textContent = periodLabel(state.kind, state.anchor); };
  drawLabel();
  const move = (direction: number) => () => { shift(direction); drawLabel(); onchange(); };
  const period = h("div", { className: "period" },
    h("button", { className: "secondary small", "aria-label": "Período anterior", onclick: move(-1) }, "‹"),
    kind,
    h("button", { className: "secondary small", "aria-label": "Próximo período", onclick: move(1) }, "›"),
    h("button", { className: "secondary small", onclick: () => { state.anchor = today(); drawLabel(); onchange(); } },
      "Hoje"));

  return h("div", { className: "card" },
    h("div", { className: "filters" },
      h("div", {}, h("label", { htmlFor: "filter-company" }, "Empresa"), company),
      h("div", {}, h("label", { htmlFor: "filter-project" }, "Projeto"), project),
      showPeriod && h("div", { className: "period-cell" }, h("label", {}, "Período: ", label), period)));
}
