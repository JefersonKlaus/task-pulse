// Faturamento: a project and a period. Every task concluded in it with what it is worth (by the rule in
// force when it was finished), the bonus, and how it stands: paid, not paid or open. The open ones are
// paid by registering what was received, unticking the ones the company will NOT pay.
import * as api from "../api.js";
import { t } from "../i18n.js";
import type { BillingReport, Company, Project, Task } from "../types.js";
import { STATUS_LABELS } from "../types.js";
import {
  actionsMenu, centsToText, confirmAction, errorMessage, field, formatDate, formatMinutes, formatMoney, h, loading,
  notify, render, toCents, today, whileDisabled,
} from "../util.js";
import { currentPeriod, filterBar, state } from "./filters.js";

export async function mount(area: HTMLElement): Promise<void> {
  render(area, loading());
  let companies: Company[], projects: Project[];
  try { [companies, projects] = await Promise.all([api.companies.list(), api.projects.list()]); }
  catch (error) { return render(area, h("p", { className: "notice" }, errorMessage(error))); }
  if (!projects.length) {
    return render(area, h("h1", {}, t("Faturamento")),
      h("p", { className: "notice" }, t("Cadastre um projeto em Projetos.")));
  }
  const report = h("div", { id: "billing" });
  render(area, h("h1", {}, t("Faturamento")),
    filterBar({ companies, projects, requireProject: true, onchange: () => void load() }), report);

  async function load(): Promise<void> {
    if (!state.projectId) return render(report, h("p", { className: "notice" }, t("Nenhum projeto nesta empresa.")));
    render(report, loading());
    try { draw(await api.billing.get(state.projectId, currentPeriod())); }
    catch (error) { render(report, h("p", { className: "notice" }, errorMessage(error))); }
  }

  function draw(data: BillingReport): void {
    const currency = data.project.currency;
    const money = (cents: number) => formatMoney(cents, currency);
    const totals = data.totals;
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
    const tasksCount = (count: number) => t("{count} tarefa(s)", { count });

    const totalsCard = h("div", { className: "totals", id: "billing-totals" },
      h("div", {}, h("span", {}, t("Deveria receber")), h("strong", {}, money(totals.expected_cents)),
        h("small", { className: "muted" }, `${tasksCount(totals.tasks)} · ${formatMinutes(totals.minutes)}`)),
      h("div", {}, h("span", {}, t("Recebido")), h("strong", {}, money(totals.received_cents)),
        h("small", { className: totals.difference_cents < 0 ? "negative" : "positive" },
          t("diferença {amount}", { amount: money(totals.difference_cents) }))),
      h("div", {}, h("span", {}, t("Em aberto")), h("strong", {}, money(totals.to_receive_cents)),
        h("small", { className: "muted" }, tasksCount(totals.open_tasks))),
      h("div", {}, h("span", {}, t("Pagas")), h("strong", {}, money(totals.paid_value_cents)),
        h("small", { className: "muted" }, tasksCount(totals.paid_tasks))),
      h("div", {}, h("span", {}, t("Não pagas")), h("strong", {}, money(totals.not_paid_value_cents)),
        h("small", { className: "muted" }, tasksCount(totals.not_paid_tasks))),
      h("div", {}, h("span", {}, t("Bônus do período")), h("strong", {}, money(data.bonus.cents)),
        h("small", { className: "muted" }, t("{count} aprovada(s)", { count: data.bonus.approved_tasks }),
          data.bonus.paid_cents ? ` · ${t("{amount} já pago", { amount: money(data.bonus.paid_cents) })}` : "")));

    const row = (task: Task) => {
      const open = !task.payment_id;
      const box = open && h("input", { type: "checkbox", checked: true, "aria-label": t("Será paga: {name}", { name: task.name }),
        onchange: (e: Event) => {
          pay.set(task.id, (e.target as HTMLInputElement).checked);
          tr.classList.toggle("not-paid", !(e.target as HTMLInputElement).checked);
          drawExpected();
        } });
      const situation = task.billing === "paid" ? t("Paga") : task.billing === "not_paid" ? t("Não paga") : t("Em aberto");
      const tr: HTMLTableRowElement = h("tr", { className: task.billing === "not_paid" ? "not-paid" : "", "data-task": task.name },
        h("td", { className: "check" }, box || ""),
        h("td", {}, h("strong", {}, task.external_id ? `${task.external_id} · ${task.name}` : task.name),
          task.repository && h("div", { className: "muted" }, task.repository)),
        h("td", {}, h("span", { className: `badge ${task.status}` }, t(STATUS_LABELS[task.status]))),
        h("td", {}, formatDate(task.finished_at)),
        h("td", { className: "num" }, formatMinutes(task.minutes)),
        h("td", { className: "num" }, money(task.billing === "not_paid" ? task.lost_cents : task.value_cents)),
        h("td", {}, h("span", { className: `badge ${task.billing || "open"}` }, situation)));
      return tr;
    };

    const table = data.tasks.length ? h("div", { className: "card table-scroll" }, h("table", { className: "money", id: "billing-tasks" },
      h("thead", {}, h("tr", {}, h("th", {}, openTasks.length ? t("Pagar") : ""), h("th", {}, t("Tarefa")),
        h("th", {}, t("Status")), h("th", {}, t("Término")), h("th", { className: "num" }, t("Tempo")),
        h("th", { className: "num" }, t("Valor")), h("th", {}, t("Situação")))),
      h("tbody", {}, data.tasks.map(row)),
      data.bonus.cents > 0 && h("tfoot", {}, h("tr", {}, h("td", {}), h("td", { colSpan: 4 }, t("Bônus por tarefas aprovadas")),
        h("td", { className: "num" }, money(data.bonus.cents)), h("td", {}))))) :
      h("div", { className: "card empty-state" }, h("h2", {}, t("Nenhuma tarefa concluída neste período")));

    let payForm: HTMLElement | null = null;
    if (openTasks.length) {
      const receivedOn = h("input", { id: "pay-date", type: "date", value: today(), required: true });
      const notes = h("input", { id: "pay-notes", maxLength: 2000 });
      const submit = h("button", { className: "primary", type: "submit" }, t("Registrar pagamento"));
      payForm = h("form", { className: "card", id: "pay-form" },
        h("h2", {}, t("Registrar pagamento")),
        h("p", { className: "muted" }, t("Desmarque na lista as tarefas que NÃO serão pagas. A receber:"), " ", expectedLabel,
          data.bonus.due_cents ? ` ${t("(com {amount} de bônus)", { amount: money(data.bonus.due_cents) })}` : ""),
        h("div", { className: "two-columns" }, h("div", {}, field(t("Valor recebido ({currency})", { currency }), received)),
          h("div", {}, field(t("Recebido em"), receivedOn))),
        field(t("Observações"), notes),
        h("div", { className: "actions" }, submit));
      payForm.addEventListener("submit", (e) => {
        e.preventDefault();
        const cents = toCents(received.value);
        if (cents == null) return notify(t("Valor recebido inválido (ex.: 1.234,56)."), true);
        void whileDisabled(submit, async () => {
          try {
            draw(await api.billing.pay(data.project.id, { period_start: data.period.from, period_end: data.period.to,
              received_cents: cents, received_on: receivedOn.value, notes: notes.value,
              not_paid_task_ids: openTasks.filter((task) => !pay.get(task.id)).map((task) => task.id) }));
            notify(t("Pagamento registrado."));
          } catch (error) { notify(errorMessage(error), true); }
        });
      });
      drawExpected();
    }

    const payments = data.payments.length > 0 && h("div", { className: "card" }, h("h2", {}, t("Pagamentos deste período")),
      h("ul", { className: "item-list" }, data.payments.map((p) => h("li", { className: "list-item" },
        h("div", { className: "list-main" },
          h("div", { className: "list-title" }, h("strong", {}, t("Recebido em {date}", { date: formatDate(p.received_on) })),
            h("span", { className: "amount" }, money(p.received_cents))),
          h("div", { className: "task-meta" },
            h("span", {}, t("{from} a {to}", { from: formatDate(p.period_start), to: formatDate(p.period_end) })),
            h("span", {}, t("deveria: {amount}", { amount: money(p.expected_cents) })),
            h("span", { className: p.difference_cents < 0 ? "negative" : "positive" },
              t("diferença: {amount}", { amount: money(p.difference_cents) })),
            p.not_paid_tasks > 0 && h("span", {}, t("{count} não paga(s): {amount}",
              { count: p.not_paid_tasks, amount: money(p.not_paid_cents) })),
            p.notes && h("span", {}, p.notes))),
        actionsMenu(t("Pagamento"), [{ text: t("Excluir pagamento"), danger: true, onclick: async () => {
          if (!(await confirmAction(t("Excluir este pagamento? As tarefas dele voltam a ficar em aberto.")))) return;
          try { await api.billing.removePayment(data.project.id, p.id); notify(t("Pagamento excluído.")); await load(); }
          catch (error) { notify(errorMessage(error), true); }
        } }])))));

    render(report, totalsCard, table, payForm, payments);
  }

  await load();
}
