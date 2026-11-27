// Tarefas: the tasks by company, project and period. Opens on the ones still being done (DOING); each
// takes time (+ Tempo) and is concluded right there, the finish taking this moment.
import * as api from "../api.js";
import { N_, t } from "../i18n.js";
import type { Project, Status, Task } from "../types.js";
import { STATUS_LABELS } from "../types.js";
import {
  actionsMenu, confirmAction, errorMessage, field, formatDate, formatHours, formatMinutes, formatMoney, formDialog,
  h, loading, notify, nowLocal, render, toMinutes, whileDisabled,
} from "../util.js";
import { currentPeriod, filterBar, state } from "./filters.js";

type View = "open" | "finished" | "all";
const VIEWS: [View, string][] = [["open", N_("Em aberto")], ["finished", N_("Concluídas")], ["all", N_("Todas")]];
let view: View = "open";

const TIME_HINT = () => t("1:30, 1,5 (horas) ou 45m");
const BAD_TIME = () => t("Tempo inválido: use 1:30, 1,5 ou 45m.");

export async function mount(area: HTMLElement): Promise<void> {
  render(area, loading());
  let projects: Project[];
  let companies;
  try {
    [companies, projects] = await Promise.all([api.companies.list(), api.projects.list()]);
  } catch (error) { return render(area, h("p", { className: "notice" }, errorMessage(error))); }

  const list = h("div", { id: "task-list" });
  const newButton = h("button", { className: "primary", id: "new-task", onclick: () => taskForm(projects, null, load) },
    t("Nova tarefa"));
  const tabs = h("div", { className: "tabs", role: "tablist" });
  const drawTabs = () => render(tabs, VIEWS.map(([key, label]) => h("button", { role: "tab",
    "aria-selected": String(key === view), onclick: () => { view = key; drawTabs(); void load(); } }, t(label))));
  drawTabs();

  if (!projects.length) {
    return render(area, h("h1", {}, t("Tarefas")), h("div", { className: "card empty-state" },
      h("h2", {}, t("Nenhum projeto ainda")),
      h("p", { className: "muted" }, t("Cadastre a empresa em Empresas e o projeto (com o valor hora ou fixo) em Projetos."))));
  }

  async function load(): Promise<void> {
    render(list, loading());
    try {
      const result = await api.tasks.list({ company_id: state.companyId, project_id: state.projectId,
        ...currentPeriod(), state: view });
      drawList(result.tasks, result.totals.minutes);
    } catch (error) { render(list, h("p", { className: "notice" }, errorMessage(error))); }
  }

  function drawList(tasks: Task[], minutes: number): void {
    if (!tasks.length) {
      return render(list, h("div", { className: "card empty-state" }, h("h2", {}, t("Nenhuma tarefa")),
        h("p", { className: "muted" }, view === "open" ? t("Nada em aberto neste período.") : t("Nada neste período."))));
    }
    const value = tasks.reduce((sum, task) => sum + task.value_cents, 0);
    const currencies = new Set(tasks.map((task) => task.currency));
    render(list,
      h("p", { className: "muted", id: "task-totals" }, t("{count} tarefa(s) · {hours}",
        { count: tasks.length, hours: formatHours(minutes) }),
        view !== "open" && currencies.size === 1 ? ` · ${formatMoney(value, tasks[0]!.currency)}` : ""),
      h("div", { className: "card list-card" }, h("ul", { className: "item-list" }, tasks.map((task) => row(task)))));
  }

  function row(task: Task): HTMLElement {
    const time = h("input", { type: "text", inputMode: "decimal", placeholder: "1:30",
      "aria-label": t("Tempo: {name}", { name: task.name }) });
    const add = h("button", { className: "secondary small", type: "submit" }, t("+ Tempo"));
    const quick = h("form", { className: "quick-time" }, time, add);
    quick.addEventListener("submit", (e) => {
      e.preventDefault();
      const minutes = toMinutes(time.value);
      if (!minutes) return notify(BAD_TIME(), true);
      void whileDisabled(add, async () => {
        try {
          await api.tasks.addTime(task.project_id, task.id, { minutes });
          notify(t("{time} adicionado(s).", { time: formatMinutes(minutes) }));
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
          h("span", { className: `badge ${task.status}` }, t(STATUS_LABELS[task.status])),
          task.billing && h("span", { className: `badge ${task.billing}` }, task.billing === "paid" ? t("Paga") : t("Não paga")),
          h("span", {}, task.project_name),
          task.repository && h("span", {}, task.repository),
          h("span", {}, t("Início {date}", { date: formatDate(task.started_at) })),
          task.finished_at && h("span", {}, t("Término {date}", { date: formatDate(task.finished_at) }))),
        open && h("div", { className: "actions tight" }, quick,
          h("button", { className: "primary small", onclick: () => finishDialog(task, load) }, t("Concluir")))),
      actionsMenu(task.name, [
        { text: t("Editar"), onclick: () => taskForm(projects, task, load) },
        task.status === "DONE" && { text: t("Aprovar"), onclick: () => setStatus(task, "APPROVED") },
        task.status === "DONE" && { text: t("Rejeitar"), onclick: () => setStatus(task, "REJECTED") },
        !open && !task.billing && { text: t("Reabrir"), onclick: () => setStatus(task, "DOING") },
        !task.billing && { text: t("Excluir"), danger: true, onclick: async () => {
          if (!(await confirmAction(t("Excluir a tarefa \"{name}\"?", { name: task.name })))) return;
          try { await api.tasks.remove(task.project_id, task.id); notify(t("Tarefa excluída.")); await load(); }
          catch (error) { notify(errorMessage(error), true); }
        } },
      ]));
  }

  async function setStatus(task: Task, status: Status): Promise<void> {
    try {
      await api.tasks.update(task.project_id, task.id, { status });
      notify(t("Tarefa: {status}.", { status: t(STATUS_LABELS[status]).toLowerCase() }));
      await load();
    } catch (error) { notify(errorMessage(error), true); }
  }

  render(area,
    h("div", { className: "row" }, h("h1", {}, t("Tarefas")), newButton),
    filterBar({ companies, projects, onchange: () => void load() }),
    tabs, list);
  await load();
}

/** Conclude a task: the time of this last stretch (optional) and the finish (now, unless typed). */
function finishDialog(task: Task, done: () => Promise<void>): void {
  const time = h("input", { id: "finish-time", type: "text", inputMode: "decimal", placeholder: "0:30" });
  const end = h("input", { id: "finish-at", type: "datetime-local", value: nowLocal() });
  formDialog(t("Concluir: {name}", { name: task.name }), [
    h("p", { className: "muted" }, t("Tempo até agora: {time}", { time: formatMinutes(task.minutes) })),
    field(t("Tempo a adicionar (opcional)"), time, TIME_HINT()),
    field(t("Término"), end),
  ], async () => {
    const minutes = time.value.trim() ? toMinutes(time.value) : 0;
    if (minutes == null) throw new Error(BAD_TIME());
    await api.tasks.addTime(task.project_id, task.id, { minutes, finish: true, finished_at: end.value || undefined });
    notify(t("Tarefa concluída."));
    await done();
  }, t("Concluir"));
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
    h("option", { value: s, selected: s === (task?.status || "DOING") }, t(STATUS_LABELS[s]))));
  const started = h("input", { id: "t-started", type: "datetime-local", required: true,
    value: task?.started_at || nowLocal() });
  const minutes = h("input", { id: "t-minutes", inputMode: "decimal", placeholder: "2:30",
    value: task?.minutes ? formatMinutes(task.minutes) : "" });
  const finished = h("input", { id: "t-finished", type: "datetime-local", value: task?.finished_at || nowLocal() });
  const concludedFields = h("div", {}, field(task ? t("Tempo total") : t("Tempo trabalhado"), minutes, TIME_HINT()),
    field(t("Término"), finished));
  const drawStatus = () => { concludedFields.hidden = status.value === "DOING" && !task?.minutes; };
  status.addEventListener("change", drawStatus);
  drawStatus();
  const billed = Boolean(task?.billing);

  formDialog(task ? t("Editar tarefa") : t("Nova tarefa"), [
    field(t("Projeto"), project),
    field(t("Nome"), name),
    h("div", { className: "two-columns" }, h("div", {}, field(t("ID externo (opcional)"), externalId)),
      h("div", {}, field(t("Repositório"), repository))),
    field(t("Descrição"), description),
    billed ? h("p", { className: "notice-warn" }, t("Tarefa já faturada: tempo, status e datas não mudam mais.")) : [
      h("div", { className: "two-columns" }, h("div", {}, field(t("Status"), status)),
        h("div", {}, field(t("Início"), started))),
      concludedFields],
  ], async () => {
    const body: Record<string, unknown> = { name: name.value, external_id: externalId.value,
      repository: repository.value, description: description.value };
    if (!billed) {
      body.status = status.value;
      body.started_at = started.value;
      const spent = minutes.value.trim() ? toMinutes(minutes.value) : 0;
      if (spent == null) throw new Error(BAD_TIME());
      body.minutes = spent;
      if (status.value !== "DOING") body.finished_at = finished.value;
    }
    if (task) await api.tasks.update(task.project_id, task.id, body);
    else await api.tasks.create(project.value, body);
    notify(task ? t("Tarefa salva.") : t("Tarefa criada."));
    await done();
  });
}
