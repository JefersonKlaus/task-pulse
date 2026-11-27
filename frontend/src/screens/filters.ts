// The filters every page shares: company, project and period (month, week or a custom range, with ‹ › to
// move). They are kept while the app is open, so going from Tarefas to Faturamento keeps the same choice.
// Custom: any start and end day, for companies whose pay period is not Monday to Sunday (Sunday to
// Saturday, two weeks...); ‹ › move it by its own length, so the next one starts the day after it ends.
import type { Period } from "../api.js";
import { locale, t } from "../i18n.js";
import type { Company, Project } from "../types.js";
import { addDays, h, today } from "../util.js";

export type PeriodKind = "month" | "week" | "custom";

export const state = {
  companyId: "",
  projectId: "",
  kind: "month" as PeriodKind,
  anchor: today(),            // any day inside the period shown (month and week)
  from: today(),              // custom: first and last day
  to: today(),
};

/** Days from `from` to `to`, both included. */
const lengthOf = (from: string, to: string): number =>
  Math.round((Date.parse(`${to}T12:00:00Z`) - Date.parse(`${from}T12:00:00Z`)) / 86_400_000) + 1;

/** The month or the week (Monday to Sunday) that contains `anchor`; custom: the days chosen. */
export function periodOf(kind: PeriodKind, anchor: string): Period {
  if (kind === "custom") return { from: state.from, to: state.to };
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
  if (kind === "month") {                    // "novembro de 2026" / "November 2026"
    return new Date(`${from}T12:00:00Z`).toLocaleString(locale(), { month: "long", year: "numeric", timeZone: "UTC" });
  }
  const short = (iso: string) => new Date(`${iso}T12:00:00Z`).toLocaleString(locale(),
    { day: "2-digit", month: "2-digit", timeZone: "UTC" });
  return t("{from} a {to}", { from: short(from), to: `${short(to)}/${to.slice(0, 4)}` });
}

export const currentPeriod = (): Period => periodOf(state.kind, state.anchor);

function shift(direction: number): void {
  if (state.kind === "custom") {
    const days = lengthOf(state.from, state.to) * direction;
    state.from = addDays(state.from, days);
    state.to = addDays(state.to, days);
  } else if (state.kind === "week") state.anchor = addDays(state.anchor, 7 * direction);
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
  } }, h("option", { value: "" }, t("Todas as empresas")),
  companies.map((c) => h("option", { value: c.id, selected: c.id === state.companyId }, c.name)));

  const project = h("select", { id: "filter-project", onchange: () => { state.projectId = project.value; onchange(); } });
  const drawProjects = () => {
    project.replaceChildren(...[
      !requireProject && h("option", { value: "" }, t("Todos os projetos")),
      ...visible().map((p) => h("option", { value: p.id, selected: p.id === state.projectId },
        state.companyId ? p.name : `${p.name} · ${p.company_name}`)),
    ].filter((o): o is HTMLOptionElement => Boolean(o)));
    project.value = state.projectId;
  };
  drawProjects();

  // custom: the first and the last day; changing one keeps the range valid (the end never before the start)
  const from = h("input", { type: "date", id: "filter-from", required: true, onchange: () => {
    if (!from.value) return;
    state.from = from.value;
    if (state.to < state.from) state.to = state.from;
    draw();
    onchange();
  } });
  const to = h("input", { type: "date", id: "filter-to", required: true, onchange: () => {
    if (!to.value) return;
    state.to = to.value;
    if (state.to < state.from) state.from = state.to;
    draw();
    onchange();
  } });
  const custom = h("div", { className: "custom-period", id: "custom-period" },
    h("div", {}, h("label", { htmlFor: "filter-from" }, t("De")), from),
    h("div", {}, h("label", { htmlFor: "filter-to" }, t("Até")), to));

  const kind = h("select", { id: "filter-kind", onchange: () => {
    if (kind.value === "custom" && state.kind !== "custom") {     // starts from the period on screen
      ({ from: state.from, to: state.to } = currentPeriod());
    }
    state.kind = kind.value as PeriodKind;
    draw();
    onchange();
  } }, h("option", { value: "month", selected: state.kind === "month" }, t("Mês")),
  h("option", { value: "week", selected: state.kind === "week" }, t("Semana")),
  h("option", { value: "custom", selected: state.kind === "custom" }, t("Personalizado")));
  const label = h("strong", { id: "period-label", className: "period-label" });
  const todayButton = h("button", { className: "secondary small", onclick: () => {
    state.anchor = today(); draw(); onchange();
  } }, t("Hoje"));
  const draw = () => {
    label.textContent = periodLabel(state.kind, state.anchor);
    custom.hidden = state.kind !== "custom";
    todayButton.hidden = state.kind === "custom";     // a custom range moves with ‹ › or its two days
    from.value = state.from;
    to.value = state.to;
  };
  draw();
  const move = (direction: number) => () => { shift(direction); draw(); onchange(); };
  const period = h("div", { className: "period" },
    h("button", { className: "secondary small", "aria-label": t("Período anterior"), onclick: move(-1) }, "‹"),
    kind,
    h("button", { className: "secondary small", "aria-label": t("Próximo período"), onclick: move(1) }, "›"),
    todayButton);

  return h("div", { className: "card" },
    h("div", { className: "filters" },
      h("div", {}, h("label", { htmlFor: "filter-company" }, t("Empresa")), company),
      h("div", {}, h("label", { htmlFor: "filter-project" }, t("Projeto")), project),
      showPeriod && h("div", { className: "period-cell" }, h("label", {}, t("Período:"), " ", label), period, custom)));
}
