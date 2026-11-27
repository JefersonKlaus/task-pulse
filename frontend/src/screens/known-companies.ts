// The well-known companies that pay for AI training work (data annotation, evaluation, writing and review of
// model answers). On Empresas each one not registered yet is a button that adds it with one tap; the Nova empresa
// form suggests them as you type. The lesser-known ones are registered by hand, as any other company.
import * as api from "../api.js";
import { N_, t } from "../i18n.js";
import type { Company } from "../types.js";
import { errorMessage, h, notify, whileDisabled } from "../util.js";

export interface Known { name: string; notes?: string }

/** Alphabetical. `notes`: who runs it, when the brand is not the company's own name. */
export const KNOWN: Known[] = [
  { name: "Alignerr", notes: N_("Plataforma da Labelbox.") },
  { name: "Appen" },
  { name: "DataAnnotation" },
  { name: "Handshake AI" },
  { name: "Invisible Technologies" },
  { name: "Mercor" },
  { name: "micro1" },
  { name: "Mindrift", notes: N_("Plataforma da Toloka.") },
  { name: "Outlier", notes: N_("Plataforma da Scale AI.") },
  { name: "Prolific" },
  { name: "TELUS Digital" },
  { name: "Toloka" },
  { name: "Turing" },
];

const key = (name: string) => name.trim().toLowerCase();

/** The known company with this name (any case), if it is one. */
export function findKnown(name: string): Known | undefined {
  return KNOWN.find((k) => key(k.name) === key(name));
}

/** The known companies not registered yet, each a button that adds it. Nothing when all are registered. */
export function knownCompanies(registered: Company[], added: (c: Company) => unknown): HTMLElement | null {
  const have = new Set(registered.map((c) => key(c.name)));
  const missing = KNOWN.filter((k) => !have.has(key(k.name)));
  if (!missing.length) return null;
  return h("div", { className: "card", id: "known-companies" },
    h("h2", {}, t("Empresas conhecidas")),
    h("p", { className: "muted hint" }, t("Toque para adicionar. As que não estão aqui, cadastre em Nova empresa.")),
    h("div", { className: "known-list" }, missing.map((k) => {
      const button: HTMLButtonElement = h("button", { type: "button", className: "secondary small", "data-known": k.name,
        onclick: () => whileDisabled(button, async () => {
          try {
            const saved = await api.companies.create({ name: k.name, notes: k.notes ? t(k.notes) : "" });
            notify(t("{name} adicionada.", { name: saved.name }));
            await added(saved);
          } catch (error) { notify(errorMessage(error), true); }
        }) }, `+ ${k.name}`);
      return button;
    })));
}

/** For the name field of Nova empresa: the known names as suggestions, and their notes filled in when picked. */
export function suggestKnown(name: HTMLInputElement, notes: HTMLTextAreaElement): HTMLDataListElement {
  name.setAttribute("list", "known-company-names");
  name.setAttribute("autocomplete", "off");
  name.addEventListener("input", () => {
    const known = findKnown(name.value);
    if (known?.notes && !notes.value.trim()) notes.value = t(known.notes);
  });
  return h("datalist", { id: "known-company-names" }, KNOWN.map((k) => h("option", { value: k.name })));
}
