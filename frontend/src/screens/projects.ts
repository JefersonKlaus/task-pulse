// Empresas e projetos: the companies, each with its projects; a project's page with its pricing rules.
// A rule says how the project pays from a moment on (hourly with an optional flat last hour, or fixed per
// task; whether only approved tasks are paid; the bonus by approved tasks). A task is priced by the rule in
// force when it was finished, so a new rule never changes what was finished before it.
import * as api from "../api.js";
import { t } from "../i18n.js";
import type { BonusTier, Company, Project, Rule } from "../types.js";
import {
  CURRENCIES, actionsMenu, centsToText, confirmAction, errorMessage, field, formDialog, formatDate, formatMoney,
  h, notify, nowLocal, render, toCents,
} from "../util.js";
import { state } from "./filters.js";

export async function mount(area: HTMLElement): Promise<void> {
  render(area, h("p", { className: "notice" }, t("Carregando…")));
  let companies: Company[], projects: Project[];
  try {
    [companies, projects] = await Promise.all([api.companies.list(), api.projects.list()]);
  } catch (error) { return render(area, h("p", { className: "notice" }, errorMessage(error))); }
  const reload = async () => { await mount(area); };

  const cards = companies.map((company) => {
    const own = projects.filter((p) => p.company_id === company.id);
    return h("div", { className: "card", "data-company": company.name },
      h("div", { className: "row" },
        h("h2", {}, company.name, h("span", { className: "count" }, ` · ${t("{count} projeto(s)", { count: own.length })}`)),
        h("div", { className: "actions tight" },
          h("button", { className: "secondary small", onclick: () => projectForm(companies, null, company.id,
            (p) => openProject(area, p.id)) }, t("Novo projeto")),
          actionsMenu(company.name, [
            { text: t("Editar"), onclick: () => companyForm(company, reload) },
            { text: t("Excluir"), danger: true, onclick: async () => {
              if (!(await confirmAction(t("Excluir a empresa \"{name}\"?", { name: company.name })))) return;
              try { await api.companies.remove(company.id); notify(t("Empresa excluída.")); await reload(); }
              catch (error) { notify(errorMessage(error), true); }
            } }]))),
      company.notes && h("p", { className: "muted notes" }, company.notes),
      own.length ? h("ul", { className: "item-list" }, own.map((p) => {
        const rule = p.rules.find((r) => r.id === p.current_rule_id);
        return h("li", { className: "list-item clickable", tabIndex: 0, onclick: () => openProject(area, p.id),
          onkeydown: (e: KeyboardEvent) => { if (e.key === "Enter") void openProject(area, p.id); } },
        h("div", { className: "list-main" },
          h("div", { className: "list-title" }, h("strong", {}, p.name),
            h("span", { className: "muted" }, rule ? ruleSummary(rule, p.currency) : t("sem regra de valor em vigor"))),
          h("div", { className: "task-meta" }, h("span", {}, t("{count} em aberto", { count: p.open_tasks || 0 })),
            p.deadline && h("span", {}, t("Deadline {date}", { date: formatDate(p.deadline) })))),
        h("span", { className: "chevron", "aria-hidden": "true" }, "›"));
      })) : h("p", { className: "muted" }, t("Nenhum projeto.")));
  });

  render(area,
    h("div", { className: "row" }, h("h1", {}, t("Empresas e projetos")),
      h("button", { className: "primary", id: "new-company", onclick: () => companyForm(null, reload) }, t("Nova empresa"))),
    cards.length ? cards : h("div", { className: "card empty-state" }, h("h2", {}, t("Nenhuma empresa ainda")),
      h("p", { className: "muted" }, t("Cadastre a empresa para a qual você presta serviço, depois os projetos dela."))));
}

function companyForm(company: Company | null, done: () => Promise<void>): void {
  const name = h("input", { id: "c-name", required: true, maxLength: 100, value: company?.name || "" });
  const notes = h("textarea", { id: "c-notes", rows: 3, maxLength: 2000, value: company?.notes || "" });
  formDialog(company ? t("Editar empresa") : t("Nova empresa"), [field(t("Nome"), name), field(t("Observações"), notes)],
    async () => {
      const body = { name: name.value, notes: notes.value };
      if (company) await api.companies.update(company.id, body);
      else await api.companies.create(body);
      notify(t("Empresa salva."));
      await done();
    });
}

// ------------------------------------------------------------------ a project's page
async function openProject(area: HTMLElement, id: string): Promise<void> {
  render(area, h("p", { className: "notice" }, t("Carregando…")));
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
    h("button", { className: "link back", onclick: () => mount(area) }, `‹ ${t("Empresas e projetos")}`),
    h("div", { className: "row" }, h("h1", {}, project.name),
      actionsMenu(project.name, [
        { text: t("Editar projeto"), onclick: () => projectForm(companies, project, project.company_id, redraw) },
        { text: t("Excluir projeto"), danger: true, onclick: async () => {
          if (!(await confirmAction(t("Excluir o projeto \"{name}\" com todas as tarefas e pagamentos?",
            { name: project.name })))) return;
          try {
            await api.projects.remove(project.id); notify(t("Projeto excluído.")); state.projectId = ""; await mount(area);
          } catch (error) { notify(errorMessage(error), true); }
        } }])),
    h("div", { className: "card" }, h("dl", { className: "details" },
      h("dt", {}, t("Empresa")), h("dd", {}, project.company_name),
      h("dt", {}, t("Moeda")), h("dd", {}, project.currency),
      h("dt", {}, t("Deadline")), h("dd", {}, project.deadline ? formatDate(project.deadline) : "—")),
    project.description && h("p", { className: "notes" }, project.description)),
    h("div", { className: "card", id: "rules" },
      h("div", { className: "row" }, h("h2", {}, t("Regras de valor")),
        h("button", { className: "primary small", id: "new-rule", onclick: () => ruleForm(project, null, redraw) },
          t("Nova regra"))),
      h("p", { className: "muted hint" }, t("Cada tarefa vale pela regra em vigor quando foi concluída. Para mudar um "
        + "valor, crie uma regra nova a partir de agora: a anterior termina quando a nova começa.")),
      rules.length ? rules.map((rule) => h("div", { className: "rule" + (rule.id === project.current_rule_id ? " current" : "") },
        h("div", { className: "row" },
          h("div", {},
            h("strong", {}, ruleSummary(rule, project.currency)),
            rule.id === project.current_rule_id && h("span", { className: "badge APPROVED" }, t("em vigor")),
            h("div", { className: "muted" }, rule.ends_at
              ? t("De {start} até {end}", { start: formatDate(rule.starts_at), end: formatDate(rule.ends_at) })
              : t("De {start} em diante", { start: formatDate(rule.starts_at) })),
            h("div", { className: "muted" }, rule.paid_only_if_approved ? t("Só tarefas aprovadas são pagas")
              : t("Tarefas concluídas e aprovadas são pagas (rejeitadas não)")),
            rule.bonus_tiers.length > 0 && h("div", { className: "muted" }, t("Bônus:"), " ", rule.bonus_tiers.map((tier) =>
              t("{count}+ aprovadas = {amount}", { count: tier.min_tasks, amount: formatMoney(tier.bonus_cents, project.currency) }))
              .join(" · "))),
          actionsMenu(t("Regra"), [
            { text: t("Editar"), onclick: () => ruleForm(project, rule, redraw) },
            { text: t("Excluir"), danger: true, onclick: async () => {
              if (!(await confirmAction(t("Excluir esta regra?")))) return;
              try { redraw(await api.projects.removeRule(project.id, rule.id)); notify(t("Regra excluída.")); }
              catch (error) { notify(errorMessage(error), true); }
            } }]))))
        : h("p", { className: "notice-warn" }, t("Sem regra: as tarefas deste projeto valem 0 até você criar uma."))));
}

export function ruleSummary(rule: Rule, currency: string): string {
  if (rule.kind === "fixed") return t("{amount} por tarefa", { amount: formatMoney(rule.fixed_cents, currency) });
  return `${formatMoney(rule.hourly_cents, currency)}/h`
    + (rule.flat_cents ? ` · ${t("última hora {amount}/h se aprovada", { amount: formatMoney(rule.flat_cents, currency) })}` : "");
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
  formDialog(project ? t("Editar projeto") : t("Novo projeto"), [
    field(t("Empresa"), company), field(t("Nome"), name),
    h("div", { className: "two-columns" }, h("div", {}, field(t("Moeda"), currency)),
      h("div", {}, field(t("Deadline (quando acaba)"), deadline))),
    field(t("Descrição"), description),
    rule && [h("h2", { className: "form-section" }, t("Valor")), rule.element],
  ], async () => {
    const body: Record<string, unknown> = { company_id: company.value, name: name.value, currency: currency.value,
      deadline: deadline.value || null, description: description.value };
    if (rule) body.rule = rule.read();
    const saved = project ? await api.projects.update(project.id, body) : await api.projects.create(body);
    notify(t("Projeto salvo."));
    await done(saved);
  });
}

function ruleForm(project: Project, rule: Rule | null, done: (p: Project) => void): void {
  const fields = ruleFields(rule);
  formDialog(rule ? t("Editar regra") : t("Nova regra"), [fields.element], async () => {
    const saved = rule ? await api.projects.updateRule(project.id, rule.id, fields.read())
      : await api.projects.createRule(project.id, fields.read());
    notify(t("Regra salva."));
    done(saved);
  });
}

/** The fields of a rule, and `read()` that turns them into the API's body (throws on a bad amount). */
function ruleFields(rule: Rule | null): { element: HTMLElement; read: () => Record<string, unknown> } {
  const kindName = `kind-${Math.random().toString(36).slice(2, 7)}`;
  const example = centsToText(9000);
  const hourlyRadio = h("input", { type: "radio", name: kindName, value: "hourly", checked: rule?.kind !== "fixed" });
  const fixedRadio = h("input", { type: "radio", name: kindName, value: "fixed", checked: rule?.kind === "fixed" });
  const starts = h("input", { id: "r-starts", type: "datetime-local", required: true, value: rule?.starts_at || nowLocal() });
  const ends = h("input", { id: "r-ends", type: "datetime-local", value: rule?.ends_at || "" });
  const hourly = h("input", { id: "r-hourly", inputMode: "decimal", placeholder: example,
    value: rule?.kind === "hourly" ? centsToText(rule.hourly_cents) : "" });
  const flat = h("input", { id: "r-flat", inputMode: "decimal", placeholder: t("opcional"),
    value: centsToText(rule?.flat_cents) });
  const fixed = h("input", { id: "r-fixed", inputMode: "decimal", placeholder: centsToText(35000),
    value: rule?.kind === "fixed" ? centsToText(rule.fixed_cents) : "" });
  const onlyApproved = h("input", { id: "r-approved", type: "checkbox", checked: Boolean(rule?.paid_only_if_approved) });
  const hourlyFields = h("div", { className: "two-columns" },
    h("div", {}, field(t("Valor hora"), hourly)),
    h("div", {}, field(t("Valor flat (última hora, se aprovada)"), flat)));
  const fixedFields = h("div", {}, field(t("Valor fixo por tarefa"), fixed));
  const drawKind = () => { hourlyFields.hidden = fixedRadio.checked; fixedFields.hidden = !fixedRadio.checked; };
  hourlyRadio.addEventListener("change", drawKind);
  fixedRadio.addEventListener("change", drawKind);
  drawKind();

  const tiers = h("div", { id: "r-tiers" });
  const addTier = (tier?: BonusTier) => {
    const count = h("input", { type: "number", min: 1, step: 1, placeholder: t("nº de tarefas"),
      "aria-label": t("Tarefas aprovadas"), value: tier ? String(tier.min_tasks) : "" });
    const amount = h("input", { inputMode: "decimal", placeholder: t("bônus"), "aria-label": t("Valor do bônus"),
      value: centsToText(tier?.bonus_cents) });
    const line: HTMLElement = h("div", { className: "tier-row" }, count, amount,
      h("button", { type: "button", className: "secondary small", "aria-label": t("Remover faixa"),
        onclick: () => line.remove() }, "×"));
    tiers.append(line);
  };
  rule?.bonus_tiers.forEach(addTier);

  const element = h("div", {},
    h("fieldset", { className: "choices" }, h("legend", {}, t("Tipo de valor")),
      h("label", { className: "choice" }, hourlyRadio, t("Valor hora")),
      h("label", { className: "choice" }, fixedRadio, t("Valor fixo"))),
    hourlyFields, fixedFields,
    h("div", { className: "two-columns" }, h("div", {}, field(t("Vale a partir de"), starts)),
      h("div", {}, field(t("Até (opcional)"), ends, t("Vazio: até começar outra regra")))),
    h("label", { className: "chip" }, onlyApproved, t("Só paga tarefa aprovada")),
    h("span", { className: "field-label" }, t("Bônus por tarefas aprovadas no período")),
    tiers,
    h("button", { type: "button", className: "secondary small", onclick: () => addTier() }, t("+ Faixa de bônus")));

  const money = (input: HTMLInputElement, label: string, optional = false): number | null => {
    if (optional && !input.value.trim()) return null;
    const cents = toCents(input.value);
    if (cents == null) throw new Error(t("{label}: valor inválido (ex.: {example})", { label, example }));
    return cents;
  };
  const read = () => {
    const kind = fixedRadio.checked ? "fixed" : "hourly";
    const bonus = [...tiers.querySelectorAll(".tier-row")].map((row) => {
      const [count, amount] = [...row.querySelectorAll("input")] as HTMLInputElement[];
      return { min_tasks: Number(count!.value), bonus_cents: money(amount!, t("Bônus")) };
    });
    return { kind, starts_at: starts.value, ends_at: ends.value || null, paid_only_if_approved: onlyApproved.checked,
      bonus_tiers: bonus,
      ...(kind === "hourly" ? { hourly_cents: money(hourly, t("Valor hora")), flat_cents: money(flat, t("Valor flat"), true) }
        : { fixed_cents: money(fixed, t("Valor fixo")) }) };
  };
  return { element, read };
}
