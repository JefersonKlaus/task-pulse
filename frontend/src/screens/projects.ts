// Empresas e projetos: the companies, each with its projects; a project's page with its pricing rules.
// A rule says how the project pays from a moment on (hourly with an optional flat last hour, or fixed per
// task; whether only approved tasks are paid; the bonus by approved tasks). A task is priced by the rule in
// force when it was finished, so a new rule never changes what was finished before it.
import * as api from "../api.js";
import type { BonusTier, Company, Project, Rule } from "../types.js";
import {
  CURRENCIES, actionsMenu, centsToText, confirmAction, errorMessage, field, formDialog, formatDate, formatMoney,
  h, notify, nowLocal, render, toCents,
} from "../util.js";
import { state } from "./filters.js";

export async function mount(area: HTMLElement): Promise<void> {
  render(area, h("p", { className: "notice" }, "Carregando…"));
  let companies: Company[], projects: Project[];
  try {
    [companies, projects] = await Promise.all([api.companies.list(), api.projects.list()]);
  } catch (error) { return render(area, h("p", { className: "notice" }, errorMessage(error))); }
  const reload = async () => { await mount(area); };

  const cards = companies.map((company) => {
    const own = projects.filter((p) => p.company_id === company.id);
    return h("div", { className: "card", "data-company": company.name },
      h("div", { className: "row" },
        h("h2", {}, company.name, h("span", { className: "count" }, ` · ${own.length} projeto(s)`)),
        h("div", { className: "actions tight" },
          h("button", { className: "secondary small", onclick: () => projectForm(companies, null, company.id,
            (p) => openProject(area, p.id)) }, "Novo projeto"),
          actionsMenu(company.name, [
            { text: "Editar", onclick: () => companyForm(company, reload) },
            { text: "Excluir", danger: true, onclick: async () => {
              if (!(await confirmAction(`Excluir a empresa "${company.name}"?`))) return;
              try { await api.companies.remove(company.id); notify("Empresa excluída."); await reload(); }
              catch (error) { notify(errorMessage(error), true); }
            } }]))),
      company.notes && h("p", { className: "muted notes" }, company.notes),
      own.length ? h("ul", { className: "item-list" }, own.map((p) => {
        const rule = p.rules.find((r) => r.id === p.current_rule_id);
        return h("li", { className: "list-item clickable", tabIndex: 0, onclick: () => openProject(area, p.id),
          onkeydown: (e: KeyboardEvent) => { if (e.key === "Enter") void openProject(area, p.id); } },
        h("div", { className: "list-main" },
          h("div", { className: "list-title" }, h("strong", {}, p.name),
            h("span", { className: "muted" }, rule ? ruleSummary(rule, p.currency) : "sem regra de valor em vigor")),
          h("div", { className: "task-meta" }, h("span", {}, `${p.open_tasks || 0} em aberto`),
            p.deadline && h("span", {}, `Deadline ${formatDate(p.deadline)}`))),
        h("span", { className: "chevron", "aria-hidden": "true" }, "›"));
      })) : h("p", { className: "muted" }, "Nenhum projeto."));
  });

  render(area,
    h("div", { className: "row" }, h("h1", {}, "Empresas e projetos"),
      h("button", { className: "primary", id: "new-company", onclick: () => companyForm(null, reload) }, "Nova empresa")),
    cards.length ? cards : h("div", { className: "card empty-state" }, h("h2", {}, "Nenhuma empresa ainda"),
      h("p", { className: "muted" }, "Cadastre a empresa para a qual você presta serviço, depois os projetos dela.")));
}

function companyForm(company: Company | null, done: () => Promise<void>): void {
  const name = h("input", { id: "c-name", required: true, maxLength: 100, value: company?.name || "" });
  const notes = h("textarea", { id: "c-notes", rows: 3, maxLength: 2000, value: company?.notes || "" });
  formDialog(company ? "Editar empresa" : "Nova empresa", [field("Nome", name), field("Observações", notes)],
    async () => {
      const body = { name: name.value, notes: notes.value };
      if (company) await api.companies.update(company.id, body);
      else await api.companies.create(body);
      notify("Empresa salva.");
      await done();
    });
}

// ------------------------------------------------------------------ a project's page
async function openProject(area: HTMLElement, id: string): Promise<void> {
  render(area, h("p", { className: "notice" }, "Carregando…"));
  let project: Project, companies: Company[];
  try { [project, companies] = await Promise.all([api.projects.get(id), api.companies.list()]); }
  catch (error) { return render(area, h("p", { className: "notice" }, errorMessage(error))); }
  state.companyId = project.company_id;
  state.projectId = project.id;
  const redraw = (p: Project) => drawProject(area, p, companies);
  redraw(project);
}

function drawProject(area: HTMLElement, project: Project, companies: Company[]): void {
  const redraw = (p: Project) => drawProject(area, p, companies);
  const rules = [...project.rules].sort((a, b) => b.starts_at.localeCompare(a.starts_at));
  render(area,
    h("button", { className: "link back", onclick: () => mount(area) }, "‹ Empresas e projetos"),
    h("div", { className: "row" }, h("h1", {}, project.name),
      actionsMenu(project.name, [
        { text: "Editar projeto", onclick: () => projectForm(companies, project, project.company_id, redraw) },
        { text: "Excluir projeto", danger: true, onclick: async () => {
          if (!(await confirmAction(`Excluir o projeto "${project.name}" com todas as tarefas e pagamentos?`))) return;
          try { await api.projects.remove(project.id); notify("Projeto excluído."); state.projectId = ""; await mount(area); }
          catch (error) { notify(errorMessage(error), true); }
        } }])),
    h("div", { className: "card" }, h("dl", { className: "details" },
      h("dt", {}, "Empresa"), h("dd", {}, project.company_name),
      h("dt", {}, "Moeda"), h("dd", {}, project.currency),
      h("dt", {}, "Deadline"), h("dd", {}, project.deadline ? formatDate(project.deadline) : "—")),
    project.description && h("p", { className: "notes" }, project.description)),
    h("div", { className: "card", id: "rules" },
      h("div", { className: "row" }, h("h2", {}, "Regras de valor"),
        h("button", { className: "primary small", id: "new-rule", onclick: () => ruleForm(project, null, redraw) },
          "Nova regra")),
      h("p", { className: "muted hint" }, "Cada tarefa vale pela regra em vigor quando foi concluída. Para mudar um "
        + "valor, crie uma regra nova a partir de agora: a anterior termina quando a nova começa."),
      rules.length ? rules.map((rule) => h("div", { className: "rule" + (rule.id === project.current_rule_id ? " current" : "") },
        h("div", { className: "row" },
          h("div", {},
            h("strong", {}, ruleSummary(rule, project.currency)),
            rule.id === project.current_rule_id && h("span", { className: "badge APPROVED" }, "em vigor"),
            h("div", { className: "muted" }, `De ${formatDate(rule.starts_at)} `,
              rule.ends_at ? `até ${formatDate(rule.ends_at)}` : "em diante"),
            h("div", { className: "muted" }, rule.paid_only_if_approved ? "Só tarefas aprovadas são pagas"
              : "Tarefas concluídas e aprovadas são pagas (rejeitadas não)"),
            rule.bonus_tiers.length > 0 && h("div", { className: "muted" }, "Bônus: ", rule.bonus_tiers.map((t) =>
              `${t.min_tasks}+ aprovadas = ${formatMoney(t.bonus_cents, project.currency)}`).join(" · "))),
          actionsMenu("Regra", [
            { text: "Editar", onclick: () => ruleForm(project, rule, redraw) },
            { text: "Excluir", danger: true, onclick: async () => {
              if (!(await confirmAction("Excluir esta regra?"))) return;
              try { redraw(await api.projects.removeRule(project.id, rule.id)); notify("Regra excluída."); }
              catch (error) { notify(errorMessage(error), true); }
            } }]))))
        : h("p", { className: "notice-warn" }, "Sem regra: as tarefas deste projeto valem 0 até você criar uma.")));
}

export function ruleSummary(rule: Rule, currency: string): string {
  if (rule.kind === "fixed") return `${formatMoney(rule.fixed_cents, currency)} por tarefa`;
  return `${formatMoney(rule.hourly_cents, currency)}/h`
    + (rule.flat_cents ? ` · última hora ${formatMoney(rule.flat_cents, currency)}/h se aprovada` : "");
}

// ------------------------------------------------------------------ forms
function projectForm(companies: Company[], project: Project | null, companyId: string,
  done: (p: Project) => void | Promise<void>): void {
  const company = h("select", { id: "p-company", required: true },
    companies.map((c) => h("option", { value: c.id, selected: c.id === companyId }, c.name)));
  const name = h("input", { id: "p-name", required: true, maxLength: 120, value: project?.name || "" });
  const currency = h("select", { id: "p-currency" }, CURRENCIES.map((c) =>
    h("option", { value: c, selected: c === (project?.currency || "BRL") }, c)));
  const deadline = h("input", { id: "p-deadline", type: "date", value: project?.deadline || "" });
  const description = h("textarea", { id: "p-description", rows: 3, maxLength: 4000, value: project?.description || "" });
  const rule = project ? null : ruleFields(null);
  formDialog(project ? "Editar projeto" : "Novo projeto", [
    field("Empresa", company), field("Nome", name),
    h("div", { className: "two-columns" }, h("div", {}, field("Moeda", currency)),
      h("div", {}, field("Deadline (quando acaba)", deadline))),
    field("Descrição", description),
    rule && [h("h2", { className: "form-section" }, "Valor"), rule.element],
  ], async () => {
    const body: Record<string, unknown> = { company_id: company.value, name: name.value, currency: currency.value,
      deadline: deadline.value || null, description: description.value };
    if (rule) body.rule = rule.read();
    const saved = project ? await api.projects.update(project.id, body) : await api.projects.create(body);
    notify("Projeto salvo.");
    await done(saved);
  });
}

function ruleForm(project: Project, rule: Rule | null, done: (p: Project) => void): void {
  const fields = ruleFields(rule);
  formDialog(rule ? "Editar regra" : "Nova regra", [fields.element], async () => {
    const saved = rule ? await api.projects.updateRule(project.id, rule.id, fields.read())
      : await api.projects.createRule(project.id, fields.read());
    notify("Regra salva.");
    done(saved);
  });
}

/** The fields of a rule, and `read()` that turns them into the API's body (throws on a bad amount). */
function ruleFields(rule: Rule | null): { element: HTMLElement; read: () => Record<string, unknown> } {
  const kindName = `kind-${Math.random().toString(36).slice(2, 7)}`;
  const hourlyRadio = h("input", { type: "radio", name: kindName, value: "hourly", checked: rule?.kind !== "fixed" });
  const fixedRadio = h("input", { type: "radio", name: kindName, value: "fixed", checked: rule?.kind === "fixed" });
  const starts = h("input", { id: "r-starts", type: "datetime-local", required: true, value: rule?.starts_at || nowLocal() });
  const ends = h("input", { id: "r-ends", type: "datetime-local", value: rule?.ends_at || "" });
  const hourly = h("input", { id: "r-hourly", inputMode: "decimal", placeholder: "90,00",
    value: rule?.kind === "hourly" ? centsToText(rule.hourly_cents) : "" });
  const flat = h("input", { id: "r-flat", inputMode: "decimal", placeholder: "opcional",
    value: centsToText(rule?.flat_cents) });
  const fixed = h("input", { id: "r-fixed", inputMode: "decimal", placeholder: "350,00",
    value: rule?.kind === "fixed" ? centsToText(rule.fixed_cents) : "" });
  const onlyApproved = h("input", { id: "r-approved", type: "checkbox", checked: Boolean(rule?.paid_only_if_approved) });
  const hourlyFields = h("div", { className: "two-columns" },
    h("div", {}, field("Valor hora", hourly)),
    h("div", {}, field("Valor flat (última hora, se aprovada)", flat)));
  const fixedFields = h("div", {}, field("Valor fixo por tarefa", fixed));
  const drawKind = () => { hourlyFields.hidden = fixedRadio.checked; fixedFields.hidden = !fixedRadio.checked; };
  hourlyRadio.addEventListener("change", drawKind);
  fixedRadio.addEventListener("change", drawKind);
  drawKind();

  const tiers = h("div", { id: "r-tiers" });
  const addTier = (tier?: BonusTier) => {
    const count = h("input", { type: "number", min: 1, step: 1, placeholder: "nº de tarefas", "aria-label": "Tarefas aprovadas",
      value: tier ? String(tier.min_tasks) : "" });
    const amount = h("input", { inputMode: "decimal", placeholder: "bônus", "aria-label": "Valor do bônus",
      value: centsToText(tier?.bonus_cents) });
    const line: HTMLElement = h("div", { className: "tier-row" }, count, amount,
      h("button", { type: "button", className: "secondary small", "aria-label": "Remover faixa",
        onclick: () => line.remove() }, "×"));
    tiers.append(line);
  };
  rule?.bonus_tiers.forEach(addTier);

  const element = h("div", {},
    h("fieldset", { className: "choices" }, h("legend", {}, "Tipo de valor"),
      h("label", { className: "choice" }, hourlyRadio, "Valor hora"),
      h("label", { className: "choice" }, fixedRadio, "Valor fixo")),
    hourlyFields, fixedFields,
    h("div", { className: "two-columns" }, h("div", {}, field("Vale a partir de", starts)),
      h("div", {}, field("Até (opcional)", ends, "Vazio: até começar outra regra"))),
    h("label", { className: "chip" }, onlyApproved, "Só paga tarefa aprovada"),
    h("span", { className: "field-label" }, "Bônus por tarefas aprovadas no período"),
    tiers,
    h("button", { type: "button", className: "secondary small", onclick: () => addTier() }, "+ Faixa de bônus"));

  const money = (input: HTMLInputElement, label: string, optional = false): number | null => {
    if (optional && !input.value.trim()) return null;
    const cents = toCents(input.value);
    if (cents == null) throw new Error(`${label}: valor inválido (ex.: 90,00)`);
    return cents;
  };
  const read = () => {
    const kind = fixedRadio.checked ? "fixed" : "hourly";
    const bonus = [...tiers.querySelectorAll(".tier-row")].map((row) => {
      const [count, amount] = [...row.querySelectorAll("input")] as HTMLInputElement[];
      return { min_tasks: Number(count!.value), bonus_cents: money(amount!, "Bônus") };
    });
    return { kind, starts_at: starts.value, ends_at: ends.value || null, paid_only_if_approved: onlyApproved.checked,
      bonus_tiers: bonus,
      ...(kind === "hourly" ? { hourly_cents: money(hourly, "Valor hora"), flat_cents: money(flat, "Valor flat", true) }
        : { fixed_cents: money(fixed, "Valor fixo") }) };
  };
  return { element, read };
}
