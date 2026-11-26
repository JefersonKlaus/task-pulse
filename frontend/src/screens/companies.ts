// Empresas: the companies you work for. The list (with how many projects and open tasks each has), the
// company's own page with every project of it, and the company form. A company has as many projects as
// needed; each project has its own pricing rules (screens/projects.ts).
import * as api from "../api.js";
import { t } from "../i18n.js";
import type { Company, Project } from "../types.js";
import { actionsMenu, confirmAction, errorMessage, field, formDialog, h, notify, render } from "../util.js";
import { state } from "./filters.js";
import { openProject, projectForm, projectRow } from "./projects.js";

export async function mount(area: HTMLElement): Promise<void> {
  render(area, h("p", { className: "notice" }, t("Carregando…")));
  let companies: Company[];
  try { companies = await api.companies.list(); }
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
          h("div", { className: "list-title" }, h("strong", {}, c.name)),
          h("div", { className: "task-meta" },
            h("span", {}, t("{count} projeto(s)", { count: c.projects || 0 })),
            h("span", {}, t("{count} tarefa(s) em aberto", { count: c.open_tasks || 0 })),
            c.notes && h("span", { className: "one-line" }, c.notes))),
        h("span", { className: "chevron", "aria-hidden": "true" }, "›")))))
      : h("div", { className: "card empty-state" }, h("h2", {}, t("Nenhuma empresa ainda")),
        h("p", { className: "muted" }, t("Cadastre a empresa para a qual você presta serviço. Depois, os projetos dela."))));
}

/** A company's page: its details and every project of it, with Novo projeto already set to it. */
export async function openCompany(area: HTMLElement, id: string): Promise<void> {
  render(area, h("p", { className: "notice" }, t("Carregando…")));
  let companies: Company[], projects: Project[];
  try { [companies, projects] = await Promise.all([api.companies.list(), api.projects.list(id)]); }
  catch (error) { return render(area, h("p", { className: "notice" }, errorMessage(error))); }
  const company = companies.find((c) => c.id === id);
  if (!company) return mount(area);
  state.companyId = company.id;
  const again = () => openCompany(area, id);

  render(area,
    h("button", { className: "link back", onclick: () => mount(area) }, `‹ ${t("Empresas")}`),
    h("div", { className: "row" }, h("h1", {}, company.name),
      actionsMenu(company.name, [
        { text: t("Editar empresa"), onclick: () => companyForm(company, again) },
        { text: t("Excluir empresa"), danger: true, onclick: async () => {
          if (!(await confirmAction(t("Excluir a empresa \"{name}\"?", { name: company.name })))) return;
          try { await api.companies.remove(company.id); notify(t("Empresa excluída.")); state.companyId = ""; await mount(area); }
          catch (error) { notify(errorMessage(error), true); }
        } }])),
    company.notes && h("div", { className: "card" }, h("p", { className: "notes", id: "company-notes" }, company.notes)),
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

export function companyForm(company: Company | null, done: (saved: Company) => void | Promise<void>): void {
  const name = h("input", { id: "c-name", required: true, maxLength: 100, value: company?.name || "" });
  const notes = h("textarea", { id: "c-notes", rows: 3, maxLength: 2000, value: company?.notes || "" });
  formDialog(company ? t("Editar empresa") : t("Nova empresa"), [field(t("Nome"), name), field(t("Observações"), notes)],
    async () => {
      const body = { name: name.value, notes: notes.value };
      const saved = company ? await api.companies.update(company.id, body) : await api.companies.create(body);
      notify(t("Empresa salva."));
      await done(saved);
    });
}
