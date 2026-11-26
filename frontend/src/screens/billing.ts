// Faturamento: a project and a period. Every task concluded in it with what it is worth (by the rule in
// force when it was finished), the bonus, and how it stands: paid, not paid or open. The open ones are
// paid by registering what was received, unticking the ones the company will NOT pay.
import * as api from "../api.js";
import type { BillingReport, Company, Project, Task } from "../types.js";
import { STATUS_LABELS } from "../types.js";
import {
  actionsMenu, centsToText, confirmAction, errorMessage, field, formatDate, formatMinutes, formatMoney, h, notify,
  render, toCents, today, whileDisabled,
} from "../util.js";
import { currentPeriod, filterBar, state } from "./filters.js";

export async function mount(area: HTMLElement): Promise<void> {
  render(area, h("p", { className: "notice" }, "Carregando…"));
  let companies: Company[], projects: Project[];
  try { [companies, projects] = await Promise.all([api.companies.list(), api.projects.list()]); }
  catch (error) { return render(area, h("p", { className: "notice" }, errorMessage(error))); }
  if (!projects.length) {
    return render(area, h("h1", {}, "Faturamento"),
      h("p", { className: "notice" }, "Cadastre um projeto em Empresas e projetos."));
  }
  const report = h("div", { id: "billing" });
  render(area, h("h1", {}, "Faturamento"),
    filterBar({ companies, projects, requireProject: true, onchange: () => void load() }), report);

  async function load(): Promise<void> {
    if (!state.projectId) return render(report, h("p", { className: "notice" }, "Nenhum projeto nesta empresa."));
    render(report, h("p", { className: "notice" }, "Carregando…"));
    try { draw(await api.billing.get(state.projectId, currentPeriod())); }
    catch (error) { render(report, h("p", { className: "notice" }, errorMessage(error))); }
  }

  function draw(data: BillingReport): void {
    const currency = data.project.currency;
    const money = (cents: number) => formatMoney(cents, currency);
    const t = data.totals;
    const openTasks = data.tasks.filter((task) => !task.payment_id);
    const pay = new Map(openTasks.map((task) => [task.id, true]));     // ticked = will be paid

    const toReceive = () => openTasks.reduce((sum, task) => sum + (pay.get(task.id) ? task.value_cents : 0), 0)
      + data.bonus.due_cents;
    const expectedLabel = h("strong", { id: "to-receive" });
    const received = h("input", { id: "pay-received", inputMode: "decimal", required: true });
    const drawExpected = () => {
      expectedLabel.textContent = money(toReceive());
      received.value = centsToText(toReceive());
    };

    const totals = h("div", { className: "totals", id: "billing-totals" },
      h("div", {}, h("span", {}, "Deveria receber"), h("strong", {}, money(t.expected_cents)),
        h("small", { className: "muted" }, `${t.tasks} tarefa(s) · ${formatMinutes(t.minutes)}`)),
      h("div", {}, h("span", {}, "Recebido"), h("strong", {}, money(t.received_cents)),
        h("small", { className: t.difference_cents < 0 ? "negative" : "positive" },
          `diferença ${money(t.difference_cents)}`)),
      h("div", {}, h("span", {}, "Em aberto"), h("strong", {}, money(t.to_receive_cents)),
        h("small", { className: "muted" }, `${t.open_tasks} tarefa(s)`)),
      h("div", {}, h("span", {}, "Pagas"), h("strong", {}, money(t.paid_value_cents)),
        h("small", { className: "muted" }, `${t.paid_tasks} tarefa(s)`)),
      h("div", {}, h("span", {}, "Não pagas"), h("strong", {}, money(t.not_paid_value_cents)),
        h("small", { className: "muted" }, `${t.not_paid_tasks} tarefa(s)`)),
      h("div", {}, h("span", {}, "Bônus do período"), h("strong", {}, money(data.bonus.cents)),
        h("small", { className: "muted" }, `${data.bonus.approved_tasks} aprovada(s)`,
          data.bonus.paid_cents ? ` · ${money(data.bonus.paid_cents)} já pago` : "")));

    const row = (task: Task) => {
      const open = !task.payment_id;
      const box = open && h("input", { type: "checkbox", checked: true, "aria-label": `Será paga: ${task.name}`,
        onchange: (e: Event) => {
          pay.set(task.id, (e.target as HTMLInputElement).checked);
          tr.classList.toggle("not-paid", !(e.target as HTMLInputElement).checked);
          drawExpected();
        } });
      const situation = task.billing === "paid" ? "Paga" : task.billing === "not_paid" ? "Não paga" : "Em aberto";
      const tr: HTMLTableRowElement = h("tr", { className: task.billing === "not_paid" ? "not-paid" : "", "data-task": task.name },
        h("td", { className: "check" }, box || ""),
        h("td", {}, h("strong", {}, task.external_id ? `${task.external_id} · ${task.name}` : task.name),
          task.repository && h("div", { className: "muted" }, task.repository)),
        h("td", {}, h("span", { className: `badge ${task.status}` }, STATUS_LABELS[task.status])),
        h("td", {}, formatDate(task.finished_at)),
        h("td", { className: "num" }, formatMinutes(task.minutes)),
        h("td", { className: "num" }, money(task.billing === "not_paid" ? task.lost_cents : task.value_cents)),
        h("td", {}, h("span", { className: `badge ${task.billing || "open"}` }, situation)));
      return tr;
    };

    const table = data.tasks.length ? h("div", { className: "card table-scroll" }, h("table", { className: "money", id: "billing-tasks" },
      h("thead", {}, h("tr", {}, h("th", {}, open(openTasks) ? "Pagar" : ""), h("th", {}, "Tarefa"), h("th", {}, "Status"),
        h("th", {}, "Término"), h("th", { className: "num" }, "Tempo"), h("th", { className: "num" }, "Valor"),
        h("th", {}, "Situação"))),
      h("tbody", {}, data.tasks.map(row)),
      data.bonus.cents > 0 && h("tfoot", {}, h("tr", {}, h("td", {}), h("td", { colSpan: 4 }, "Bônus por tarefas aprovadas"),
        h("td", { className: "num" }, money(data.bonus.cents)), h("td", {}))))) :
      h("div", { className: "card empty-state" }, h("h2", {}, "Nenhuma tarefa concluída neste período"));

    let payForm: HTMLElement | null = null;
    if (openTasks.length) {
      const receivedOn = h("input", { id: "pay-date", type: "date", value: today(), required: true });
      const notes = h("input", { id: "pay-notes", maxLength: 2000 });
      const submit = h("button", { className: "primary", type: "submit" }, "Registrar pagamento");
      payForm = h("form", { className: "card", id: "pay-form" },
        h("h2", {}, "Registrar pagamento"),
        h("p", { className: "muted" }, "Desmarque na lista as tarefas que NÃO serão pagas. A receber: ", expectedLabel,
          data.bonus.due_cents ? ` (com ${money(data.bonus.due_cents)} de bônus)` : ""),
        h("div", { className: "two-columns" }, h("div", {}, field(`Valor recebido (${currency})`, received)),
          h("div", {}, field("Recebido em", receivedOn))),
        field("Observações", notes),
        h("div", { className: "actions" }, submit));
      payForm.addEventListener("submit", (e) => {
        e.preventDefault();
        const cents = toCents(received.value);
        if (cents == null) return notify("Valor recebido inválido (ex.: 1.234,56).", true);
        void whileDisabled(submit, async () => {
          try {
            draw(await api.billing.pay(data.project.id, { period_start: data.period.from, period_end: data.period.to,
              received_cents: cents, received_on: receivedOn.value, notes: notes.value,
              not_paid_task_ids: openTasks.filter((task) => !pay.get(task.id)).map((task) => task.id) }));
            notify("Pagamento registrado.");
          } catch (error) { notify(errorMessage(error), true); }
        });
      });
      drawExpected();
    }

    const payments = data.payments.length > 0 && h("div", { className: "card" }, h("h2", {}, "Pagamentos deste período"),
      h("ul", { className: "item-list" }, data.payments.map((p) => h("li", { className: "list-item" },
        h("div", { className: "list-main" },
          h("div", { className: "list-title" }, h("strong", {}, `Recebido em ${formatDate(p.received_on)}`),
            h("span", { className: "amount" }, money(p.received_cents))),
          h("div", { className: "task-meta" },
            h("span", {}, `${formatDate(p.period_start)} a ${formatDate(p.period_end)}`),
            h("span", {}, `deveria: ${money(p.expected_cents)}`),
            h("span", { className: p.difference_cents < 0 ? "negative" : "positive" }, `diferença: ${money(p.difference_cents)}`),
            p.not_paid_tasks > 0 && h("span", {}, `${p.not_paid_tasks} não paga(s): ${money(p.not_paid_cents)}`),
            p.notes && h("span", {}, p.notes))),
        actionsMenu("Pagamento", [{ text: "Excluir pagamento", danger: true, onclick: async () => {
          if (!(await confirmAction("Excluir este pagamento? As tarefas dele voltam a ficar em aberto."))) return;
          try { await api.billing.removePayment(data.project.id, p.id); notify("Pagamento excluído."); await load(); }
          catch (error) { notify(errorMessage(error), true); }
        } }])))));

    render(report, totals, table, payForm, payments);
  }

  await load();
}

const open = (tasks: Task[]) => tasks.length > 0;
