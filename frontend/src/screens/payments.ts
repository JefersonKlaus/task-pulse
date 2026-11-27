// Pagamentos: every payment registered (by company and project), what should have been received, what was
// received, the difference and what was not paid.
import * as api from "../api.js";
import { t } from "../i18n.js";
import type { Company, PaymentList, Project } from "../types.js";
import { actionsMenu, confirmAction, errorMessage, formatDate, formatMoney, h, loading, notify, render } from "../util.js";
import { filterBar, state } from "./filters.js";

export async function mount(area: HTMLElement): Promise<void> {
  render(area, loading());
  let companies: Company[], projects: Project[];
  try { [companies, projects] = await Promise.all([api.companies.list(), api.projects.list()]); }
  catch (error) { return render(area, h("p", { className: "notice" }, errorMessage(error))); }
  const list = h("div", { id: "payments" });
  render(area, h("h1", {}, t("Pagamentos")),
    filterBar({ companies, projects, showPeriod: false, onchange: () => void load() }), list);

  async function load(): Promise<void> {
    render(list, loading());
    try { draw(await api.billing.payments({ company_id: state.companyId, project_id: state.projectId })); }
    catch (error) { render(list, h("p", { className: "notice" }, errorMessage(error))); }
  }

  function draw({ payments, totals }: PaymentList): void {
    if (!payments.length) {
      return render(list, h("div", { className: "card empty-state" }, h("h2", {}, t("Nenhum pagamento")),
        h("p", { className: "muted" }, t("Registre um em Faturamento."))));
    }
    const currencies = new Set(payments.map((p) => p.currency));
    const single = currencies.size === 1 ? payments[0]!.currency! : null;
    render(list,
      single && h("div", { className: "totals", id: "payments-totals" },
        h("div", {}, h("span", {}, t("Deveria receber")), h("strong", {}, formatMoney(totals.expected_cents, single))),
        h("div", {}, h("span", {}, t("Recebido")), h("strong", {}, formatMoney(totals.received_cents, single))),
        h("div", {}, h("span", {}, t("Diferença")),
          h("strong", { className: totals.difference_cents < 0 ? "negative" : "positive" },
            formatMoney(totals.difference_cents, single)),
          h("small", { className: "muted" }, t("não pagas: {amount}", { amount: formatMoney(totals.not_paid_cents, single) })))),
      !single && h("p", { className: "muted" }, t("Moedas diferentes: escolha uma empresa ou projeto para ver os totais.")),
      h("div", { className: "card table-scroll" }, h("table", { className: "money", id: "payments-table" },
        h("thead", {}, h("tr", {}, h("th", {}, t("Recebido em")), h("th", {}, t("Projeto")), h("th", {}, t("Período")),
          h("th", { className: "num" }, t("Deveria")), h("th", { className: "num" }, t("Recebido")),
          h("th", { className: "num" }, t("Diferença")), h("th", {}, t("Tarefas")), h("th", {}))),
        h("tbody", {}, payments.map((p) => {
          const money = (cents: number) => formatMoney(cents, p.currency);
          return h("tr", {},
            h("td", {}, formatDate(p.received_on)),
            h("td", {}, h("strong", {}, p.project_name), h("div", { className: "muted" }, p.company_name)),
            h("td", {}, t("{from} a {to}", { from: formatDate(p.period_start), to: formatDate(p.period_end) })),
            h("td", { className: "num" }, money(p.expected_cents)),
            h("td", { className: "num" }, money(p.received_cents)),
            h("td", { className: `num ${p.difference_cents < 0 ? "negative" : "positive"}` }, money(p.difference_cents)),
            h("td", {}, t("{count} paga(s)", { count: p.paid_tasks }), p.not_paid_tasks > 0 &&
              h("div", { className: "muted" }, t("{count} não paga(s): {amount}",
                { count: p.not_paid_tasks, amount: money(p.not_paid_cents) }))),
            h("td", {}, actionsMenu(t("Pagamento"), [{ text: t("Excluir pagamento"), danger: true, onclick: async () => {
              if (!(await confirmAction(t("Excluir este pagamento? As tarefas dele voltam a ficar em aberto.")))) return;
              try { await api.billing.removePayment(p.project_id, p.id); notify(t("Pagamento excluído.")); await load(); }
              catch (error) { notify(errorMessage(error), true); }
            } }])));
        })))));
  }

  await load();
}
