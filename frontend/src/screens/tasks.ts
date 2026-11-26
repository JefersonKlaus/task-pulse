// Tarefas: the tasks by company, project and period. Opens on the ones still being done (DOING); each
// takes time (+ Tempo) and is concluded right there, the finish taking this moment.
import * as api from "../api.js";
import type { Project, Status, Task } from "../types.js";
import { STATUS_LABELS } from "../types.js";
import {
  actionsMenu, confirmAction, errorMessage, field, formDialog, formatDate, formatHours, formatMinutes,
  formatMoney, h, notify, nowLocal, render, toMinutes, whileDisabled,
} from "../util.js";
import { currentPeriod, filterBar, state } from "./filters.js";

type View = "open" | "finished" | "all";
const VIEWS: [View, string][] = [["open", "Em aberto"], ["finished", "Concluídas"], ["all", "Todas"]];
let view: View = "open";

export async function mount(area: HTMLElement): Promise<void> {
  render(area, h("p", { className: "notice" }, "Carregando…"));
  let projects: Project[];
  let companies;
  try {
    [companies, projects] = await Promise.all([api.companies.list(), api.projects.list()]);
  } catch (error) { return render(area, h("p", { className: "notice" }, errorMessage(error))); }

  const list = h("div", { id: "task-list" });
  const newButton = h("button", { className: "primary", id: "new-task", onclick: () => taskForm(projects, null, load) },
    "Nova tarefa");
  const tabs = h("div", { className: "tabs", role: "tablist" });
  const drawTabs = () => render(tabs, VIEWS.map(([key, label]) => h("button", { role: "tab",
    "aria-selected": String(key === view), onclick: () => { view = key; drawTabs(); void load(); } }, label)));
  drawTabs();

  if (!projects.length) {
    return render(area, h("h1", {}, "Tarefas"), h("div", { className: "card empty-state" },
      h("h2", {}, "Nenhum projeto ainda"),
      h("p", { className: "muted" }, "Cadastre a empresa e o projeto (com o valor hora ou fixo) em Empresas e projetos.")));
  }

  async function load(): Promise<void> {
    render(list, h("p", { className: "notice" }, "Carregando…"));
    try {
      const result = await api.tasks.list({ company_id: state.companyId, project_id: state.projectId,
        ...currentPeriod(), state: view });
      drawList(result.tasks, result.totals.minutes);
    } catch (error) { render(list, h("p", { className: "notice" }, errorMessage(error))); }
  }

  function drawList(tasks: Task[], minutes: number): void {
    if (!tasks.length) {
      return render(list, h("div", { className: "card empty-state" }, h("h2", {}, "Nenhuma tarefa"),
        h("p", { className: "muted" }, view === "open" ? "Nada em aberto neste período." : "Nada neste período.")));
    }
    const value = tasks.reduce((sum, t) => sum + t.value_cents, 0);
    const currencies = new Set(tasks.map((t) => t.currency));
    render(list,
      h("p", { className: "muted", id: "task-totals" }, `${tasks.length} tarefa(s) · ${formatHours(minutes)}`,
        view !== "open" && currencies.size === 1 ? ` · ${formatMoney(value, tasks[0]!.currency)}` : ""),
      h("div", { className: "card list-card" }, h("ul", { className: "item-list" }, tasks.map((t) => row(t)))));
  }

  function row(task: Task): HTMLElement {
    const time = h("input", { type: "text", inputMode: "decimal", placeholder: "1:30", "aria-label": `Tempo: ${task.name}` });
    const add = h("button", { className: "secondary small", type: "submit" }, "+ Tempo");
    const quick = h("form", { className: "quick-time" }, time, add);
    quick.addEventListener("submit", (e) => {
      e.preventDefault();
      const minutes = toMinutes(time.value);
      if (!minutes) return notify("Tempo inválido: use 1:30, 1,5 ou 45m.", true);
      void whileDisabled(add, async () => {
        try {
          await api.tasks.addTime(task.project_id, task.id, { minutes });
          notify(`${formatMinutes(minutes)} adicionado(s).`);
          await load();
        } catch (error) { notify(errorMessage(error), true); }
      });
    });
    const open = task.status === "DOING";
    return h("li", { className: "list-item", "data-task": task.name },
      h("div", { className: "list-main" },
        h("div", { className: "list-title" },
          h("strong", {}, task.external_id ? `${task.external_id} · ${task.name}` : task.name),
          h("span", { className: "amount" }, formatMinutes(task.minutes),
            !open && task.value_cents ? ` · ${formatMoney(task.value_cents, task.currency)}` : "")),
        h("div", { className: "task-meta" },
          h("span", { className: `badge ${task.status}` }, STATUS_LABELS[task.status]),
          task.billing && h("span", { className: `badge ${task.billing}` }, task.billing === "paid" ? "Paga" : "Não paga"),
          h("span", {}, task.project_name),
          task.repository && h("span", {}, task.repository),
          h("span", {}, `Início ${formatDate(task.started_at)}`),
          task.finished_at && h("span", {}, `Término ${formatDate(task.finished_at)}`)),
        open && h("div", { className: "actions tight" }, quick,
          h("button", { className: "primary small", onclick: () => finishDialog(task, load) }, "Concluir"))),
      actionsMenu(task.name, [
        { text: "Editar", onclick: () => taskForm(projects, task, load) },
        task.status === "DONE" && { text: "Aprovar", onclick: () => setStatus(task, "APPROVED") },
        task.status === "DONE" && { text: "Rejeitar", onclick: () => setStatus(task, "REJECTED") },
        !open && !task.billing && { text: "Reabrir", onclick: () => setStatus(task, "DOING") },
        !task.billing && { text: "Excluir", danger: true, onclick: async () => {
          if (!(await confirmAction(`Excluir a tarefa "${task.name}"?`))) return;
          try { await api.tasks.remove(task.project_id, task.id); notify("Tarefa excluída."); await load(); }
          catch (error) { notify(errorMessage(error), true); }
        } },
      ]));
  }

  async function setStatus(task: Task, status: Status): Promise<void> {
    try {
      await api.tasks.update(task.project_id, task.id, { status });
      notify(`Tarefa ${STATUS_LABELS[status].toLowerCase()}.`);
      await load();
    } catch (error) { notify(errorMessage(error), true); }
  }

  render(area,
    h("div", { className: "row" }, h("h1", {}, "Tarefas"), newButton),
    filterBar({ companies, projects, onchange: () => void load() }),
    tabs, list);
  await load();
}

/** Conclude a task: the time of this last stretch (optional) and the finish (now, unless typed). */
function finishDialog(task: Task, done: () => Promise<void>): void {
  const time = h("input", { id: "finish-time", type: "text", inputMode: "decimal", placeholder: "0:30" });
  const end = h("input", { id: "finish-at", type: "datetime-local", value: nowLocal() });
  formDialog(`Concluir: ${task.name}`, [
    h("p", { className: "muted" }, `Tempo até agora: ${formatMinutes(task.minutes)}`),
    field("Tempo a adicionar (opcional)", time, "1:30, 1,5 (horas) ou 45m"),
    field("Término", end),
  ], async () => {
    const minutes = time.value.trim() ? toMinutes(time.value) : 0;
    if (minutes == null) throw new Error("Tempo inválido: use 1:30, 1,5 ou 45m.");
    await api.tasks.addTime(task.project_id, task.id, { minutes, finish: true, finished_at: end.value || undefined });
    notify("Tarefa concluída.");
    await done();
  }, "Concluir");
}

/** New task (`task` null) or edit one. */
export function taskForm(projects: Project[], task: Task | null, done: () => Promise<void>): void {
  const project = h("select", { id: "t-project", required: true, disabled: Boolean(task) },
    projects.map((p) => h("option", { value: p.id, selected: p.id === (task?.project_id || state.projectId) },
      `${p.name} · ${p.company_name}`)));
  const name = h("input", { id: "t-name", required: true, maxLength: 200, value: task?.name || "" });
  const externalId = h("input", { id: "t-external", maxLength: 100, value: task?.external_id || "" });
  const repository = h("input", { id: "t-repository", maxLength: 300, value: task?.repository || "",
    placeholder: "acme/portal" });
  const description = h("textarea", { id: "t-description", rows: 3, maxLength: 8000, value: task?.description || "" });
  const status = h("select", { id: "t-status" }, (Object.keys(STATUS_LABELS) as Status[]).map((s) =>
    h("option", { value: s, selected: s === (task?.status || "DOING") }, STATUS_LABELS[s])));
  const started = h("input", { id: "t-started", type: "datetime-local", required: true,
    value: task?.started_at || nowLocal() });
  const minutes = h("input", { id: "t-minutes", inputMode: "decimal", placeholder: "2:30",
    value: task?.minutes ? formatMinutes(task.minutes) : "" });
  const finished = h("input", { id: "t-finished", type: "datetime-local", value: task?.finished_at || nowLocal() });
  const concludedFields = h("div", {}, field(task ? "Tempo total" : "Tempo trabalhado", minutes,
    "1:30, 1,5 (horas) ou 45m"), field("Término", finished));
  const drawStatus = () => { concludedFields.hidden = status.value === "DOING" && !task?.minutes; };
  status.addEventListener("change", drawStatus);
  drawStatus();
  const billed = Boolean(task?.billing);

  formDialog(task ? "Editar tarefa" : "Nova tarefa", [
    field("Projeto", project),
    field("Nome", name),
    h("div", { className: "two-columns" }, h("div", {}, field("ID externo (opcional)", externalId)),
      h("div", {}, field("Repositório", repository))),
    field("Descrição", description),
    billed ? h("p", { className: "notice-warn" }, "Tarefa já faturada: tempo, status e datas não mudam mais.") : [
      h("div", { className: "two-columns" }, h("div", {}, field("Status", status)), h("div", {}, field("Início", started))),
      concludedFields],
  ], async () => {
    const body: Record<string, unknown> = { name: name.value, external_id: externalId.value,
      repository: repository.value, description: description.value };
    if (!billed) {
      body.status = status.value;
      body.started_at = started.value;
      const spent = minutes.value.trim() ? toMinutes(minutes.value) : 0;
      if (spent == null) throw new Error("Tempo inválido: use 1:30, 1,5 ou 45m.");
      body.minutes = spent;
      if (status.value !== "DOING") body.finished_at = finished.value;
    }
    if (task) await api.tasks.update(task.project_id, task.id, body);
    else await api.tasks.create(project.value, body);
    notify(task ? "Tarefa salva." : "Tarefa criada.");
    await done();
  });
}
