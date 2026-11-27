// The well-known companies that pay for AI training work (data annotation, evaluation, writing and review of
// model answers). They come from the API (backend domain/catalog.py) and are the same for everyone: choosing
// one adds that shared company to your list, and nobody edits it, so reports can put together the work done
// for it. On Empresas each one not chosen yet is a button that adds it with one tap; the Nova empresa form
// suggests them as you type. The lesser-known companies are registered by hand, as any other company.
import * as api from "../api.js";
import { N_, t } from "../i18n.js";
import type { Company } from "../types.js";
import { errorMessage, h, notify, whileDisabled } from "../util.js";

/** The catalog's notes are written in Portuguese; these marks keep their English in i18n.ts. */
export const KNOWN_NOTES = [N_("Plataforma da Labelbox."), N_("Plataforma da Toloka."), N_("Plataforma da Scale AI.")];

let catalog: Promise<Company[]> | null = null;

/** The well-known companies, asked once per page load. */
export function knownCatalog(): Promise<Company[]> {
  catalog ??= api.companies.known().catch((error) => { catalog = null; throw error; });
  return catalog;
}

const key = (name: string) => name.trim().toLowerCase();

/** The known companies not chosen yet, each a button that adds it. Nothing when all were chosen. */
export function knownCompanies(known: Company[], registered: Company[], added: (c: Company) => unknown): HTMLElement | null {
  const have = new Set(registered.map((c) => c.id));
  const missing = known.filter((k) => !have.has(k.id));
  if (!missing.length) return null;
  return h("div", { className: "card", id: "known-companies" },
    h("h2", {}, t("Empresas conhecidas")),
    h("p", { className: "muted hint" }, t("Toque para adicionar. São as mesmas para todos e não são editadas. As que não "
      + "estão aqui, cadastre em Nova empresa.")),
    h("div", { className: "known-list" }, missing.map((k) => {
      const button: HTMLButtonElement = h("button", { type: "button", className: "secondary small", "data-known": k.name,
        onclick: () => whileDisabled(button, async () => {
          try {
            const saved = await api.companies.create({ known_id: k.id });
            notify(t("{name} adicionada.", { name: saved.name }));
            await added(saved);
          } catch (error) { notify(errorMessage(error), true); }
        }) }, `+ ${k.name}`);
      return button;
    })));
}

/** For the name field of Nova empresa: the known names as suggestions. Typing one of them fills in its notes
 * and says that it will be the shared company (the API turns a well-known name into it). */
export function suggestKnown(name: HTMLInputElement, notes: HTMLTextAreaElement, hint: HTMLElement): HTMLDataListElement {
  const list = h("datalist", { id: "known-company-names" });
  name.setAttribute("list", "known-company-names");
  name.setAttribute("autocomplete", "off");
  let known: Company[] = [];
  void knownCatalog().then((all) => {
    known = all;
    list.replaceChildren(...all.map((k) => h("option", { value: k.name })));
  }).catch(() => { /* no suggestions: the form still works */ });
  name.addEventListener("input", () => {
    const match = known.find((k) => key(k.name) === key(name.value));
    hint.hidden = !match;
    if (match?.notes && !notes.value.trim()) notes.value = t(match.notes);
  });
  return list;
}
