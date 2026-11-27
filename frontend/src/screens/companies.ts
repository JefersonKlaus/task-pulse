// Empresas: the companies you work for. The list (with how many projects and open tasks each has), the
// company's own page with every project of it, and the company form. A company has as many projects as
// needed; each project has its own pricing rules (screens/projects.ts). The well-known companies are one tap
// away and the same for everyone, so they are never edited, only removed from your list
// (screens/known-companies.ts).
import * as api from "../api.js";
import { t } from "../i18n.js";
import type { Company, Project } from "../types.js";
import { actionsMenu, confirmAction, errorMessage, field, formDialog, h, loading, notify, render } from "../util.js";
import { state } from "./filters.js";
import { knownCatalog, knownCompanies, suggestKnown } from "./known-companies.js";
import { openProject, projectForm, projectRow } from "./projects.js";

/** A company's name, with "Padrão" when it is a well-known one. */
function companyTitle(c: Company): HTMLElement[] {
  return [h("strong", {}, c.name), c.known ? h("span", { className: "badge KNOWN" }, t("Padrão")) : null]
    .filter((x): x is HTMLElement => x !== null);
}

export async function mount(area: HTMLElement): Promise<void> {
  render(area, loading());
  let companies: Company[], known: Company[];
  try { [companies, known] = await Promise.all([api.companies.list(), knownCatalog().catch(() => [])]); }
  catch (error) { return render(area, h("p", { className: "notice" }, errorMessage(error))); }

  const newButton = h("button", { className: "primary", id: "new-company",
    onclick: () => companyForm(null, (c) => openCompany(area, c.id)) }, t("Nova empresa"));
  render(area,
    h("div", { className: "row" }, h("h1", {}, t("Empresas")), newButton),
    companies.length
      ? h("div", { className: "card list-card" }, h("ul", { className: "item-list", id: "company-list" },
        companies.map((c) => h("li", { className: "list-item clickable", tabIndex: 0, "data-company": c.name,
          onclick: () => openCompany(area, c.id),
          onkeydown: (e: KeyboardEvent) => { if (e.key === "Enter") void openCompany(area, c.id); } },
        h("div", { className: "list-main" },
          h("div", { className: "list-title" }, ...companyTitle(c)),
          h("div", { className: "task-meta" },
            h("span", {}, t("{count} projeto(s)", { count: c.projects || 0 })),
            h("span", {}, t("{count} tarefa(s) em aberto", { count: c.open_tasks || 0 })),
            c.notes && h("span", { className: "one-line" }, c.known ? t(c.notes) : c.notes))),
        h("span", { className: "chevron", "aria-hidden": "true" }, "›")))))
      : h("div", { className: "card empty-state" }, h("h2", {}, t("Nenhuma empresa ainda")),
        h("p", { className: "muted" }, t("Cadastre a empresa para a qual você presta serviço. Depois, os projetos dela."))),
    knownCompanies(known, companies, () => mount(area)));
}

/** A company's page: its details and every project of it, with Novo projeto already set to it. */
export async function openCompany(area: HTMLElement, id: string): Promise<void> {
  render(area, loading());
  let companies: Company[], projects: Project[];
  try { [companies, projects] = await Promise.all([api.companies.list(), api.projects.list(id)]); }
  catch (error) { return render(area, h("p", { className: "notice" }, errorMessage(error))); }
  const company = companies.find((c) => c.id === id);
  if (!company) return mount(area);
  state.companyId = company.id;
  const again = () => openCompany(area, id);
  const remove = async () => {
    const question = company.known ? t("Remover \"{name}\" da sua lista?", { name: company.name })
      : t("Excluir a empresa \"{name}\"?", { name: company.name });
    if (!(await confirmAction(question, company.known ? t("Remover") : t("Excluir")))) return;
    try {
      await api.companies.remove(company.id);
      notify(company.known ? t("Empresa removida da sua lista.") : t("Empresa excluída."));
      state.companyId = "";
      await mount(area);
    } catch (error) { notify(errorMessage(error), true); }
  };

  render(area,
    h("button", { className: "link back", onclick: () => mount(area) }, `‹ ${t("Empresas")}`),
    h("div", { className: "row" }, h("h1", {}, company.name),
      actionsMenu(company.name, company.known
        ? [{ text: t("Remover da minha lista"), danger: true, onclick: remove }]
        : [{ text: t("Editar empresa"), onclick: () => companyForm(company, again) },
          { text: t("Excluir empresa"), danger: true, onclick: remove }])),
    (company.known || company.notes) && h("div", { className: "card" },
      company.known && h("p", { className: "muted", id: "company-known" },
        h("span", { className: "badge KNOWN" }, t("Padrão")), " ",
        t("Empresa padrão: a mesma para todos que a usam, por isso não é editada.")),
      company.notes && h("p", { className: "notes", id: "company-notes" }, company.known ? t(company.notes) : company.notes)),
    h("div", { className: "card", id: "company-projects" },
      h("div", { className: "row" },
        h("h2", {}, t("Projetos"), h("span", { className: "count" }, ` · ${projects.length}`)),
        h("button", { className: "primary small", id: "new-project",
          onclick: () => projectForm(companies, null, company.id, () => again()) }, t("Novo projeto"))),
      projects.length
        ? h("ul", { className: "item-list" }, projects.map((p) => projectRow(p, false,
          () => openProject(area, p.id, { label: company.name, back: again }))))
        : h("p", { className: "muted" }, t("Nenhum projeto nesta empresa ainda. Uma empresa pode ter vários projetos, "
          + "cada um com o seu valor."))));
}

/** One of your own companies (a well-known one is never edited). A new one with a well-known name becomes
 * that shared company. */
export function companyForm(company: Company | null, done: (saved: Company) => void | Promise<void>): void {
  const name = h("input", { id: "c-name", required: true, maxLength: 100, value: company?.name || "" });
  const notes = h("textarea", { id: "c-notes", rows: 3, maxLength: 2000, value: company?.notes || "" });
  const knownHint = h("p", { className: "muted hint", id: "c-known-hint", hidden: true },
    t("Esta é uma empresa padrão: será a mesma para todos e não poderá ser editada."));
  formDialog(company ? t("Editar empresa") : t("Nova empresa"),
    [field(t("Nome"), name), company ? null : [suggestKnown(name, notes, knownHint), knownHint],
      field(t("Observações"), notes)],
    async () => {
      const body = { name: name.value, notes: notes.value };
      const saved = company ? await api.companies.update(company.id, body) : await api.companies.create(body);
      notify(t("Empresa salva."));
      await done(saved);
    });
}
