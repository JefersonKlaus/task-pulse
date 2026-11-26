// Pagamentos: every payment registered (by company and project), what should have been received, what was
// received, the difference and what was not paid.
import * as api from "../api.js";
import type { Company, PaymentList, Project } from "../types.js";
import { actionsMenu, confirmAction, errorMessage, formatDate, formatMoney, h, notify, render } from "../util.js";
import { filterBar, state } from "./filters.js";

export async function mount(area: HTMLElement): Promise<void> {
  render(area, h("p", { className: "notice" }, "Carregando…"));
  let companies: Company[], projects: Project[];
  try { [companies, projects] = await Promise.all([api.companies.list(), api.projects.list()]); }
  catch (error) { return render(area, h("p", { className: "notice" }, errorMessage(error))); }
  const list = h("div", { id: "payments" });
  render(area, h("h1", {}, "Pagamentos"),
    filterBar({ companies, projects, showPeriod: false, onchange: () => void load() }), list);

  async function load(): Promise<void> {
    render(list, h("p", { className: "notice" }, "Carregando…"));
    try { draw(await api.billing.payments({ company_id: state.companyId, project_id: state.projectId })); }
    catch (error) { render(list, h("p", { className: "notice" }, errorMessage(error))); }
  }

  function draw({ payments, totals }: PaymentList): void {
    if (!payments.length) {
      return render(list, h("div", { className: "card empty-state" }, h("h2", {}, "Nenhum pagamento"),
        h("p", { className: "muted" }, "Registre um em Faturamento.")));
    }
    const currencies = new Set(payments.map((p) => p.currency));
    const single = currencies.size === 1 ? payments[0]!.currency! : null;
    render(list,
      single && h("div", { className: "totals", id: "payments-totals" },
        h("div", {}, h("span", {}, "Deveria receber"), h("strong", {}, formatMoney(totals.expected_cents, single))),
        h("div", {}, h("span", {}, "Recebido"), h("strong", {}, formatMoney(totals.received_cents, single))),
        h("div", {}, h("span", {}, "Diferença"),
          h("strong", { className: totals.difference_cents < 0 ? "negative" : "positive" },
            formatMoney(totals.difference_cents, single)),
          h("small", { className: "muted" }, `não pagas: ${formatMoney(totals.not_paid_cents, single)}`))),
      !single && h("p", { className: "muted" }, "Moedas diferentes: escolha uma empresa ou projeto para ver os totais."),
      h("div", { className: "card table-scroll" }, h("table", { className: "money", id: "payments-table" },
        h("thead", {}, h("tr", {}, h("th", {}, "Recebido em"), h("th", {}, "Projeto"), h("th", {}, "Período"),
          h("th", { className: "num" }, "Deveria"), h("th", { className: "num" }, "Recebido"),
          h("th", { className: "num" }, "Diferença"), h("th", {}, "Tarefas"), h("th", {}))),
        h("tbody", {}, payments.map((p) => {
          const money = (cents: number) => formatMoney(cents, p.currency);
          return h("tr", {},
            h("td", {}, formatDate(p.received_on)),
            h("td", {}, h("strong", {}, p.project_name), h("div", { className: "muted" }, p.company_name)),
            h("td", {}, `${formatDate(p.period_start)} a ${formatDate(p.period_end)}`),
            h("td", { className: "num" }, money(p.expected_cents)),
            h("td", { className: "num" }, money(p.received_cents)),
            h("td", { className: `num ${p.difference_cents < 0 ? "negative" : "positive"}` }, money(p.difference_cents)),
            h("td", {}, `${p.paid_tasks} paga(s)`, p.not_paid_tasks > 0 &&
              h("div", { className: "muted" }, `${p.not_paid_tasks} não paga(s): ${money(p.not_paid_cents)}`)),
            h("td", {}, actionsMenu("Pagamento", [{ text: "Excluir pagamento", danger: true, onclick: async () => {
              if (!(await confirmAction("Excluir este pagamento? As tarefas dele voltam a ficar em aberto."))) return;
              try { await api.billing.removePayment(p.project_id, p.id); notify("Pagamento excluído."); await load(); }
              catch (error) { notify(errorMessage(error), true); }
            } }])));
        })))));
  }

  await load();
}
