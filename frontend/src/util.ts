// Small helpers. Text coming from the user ALWAYS goes in as text (never as HTML).
import { lang, locale, t } from "./i18n.js";

export type Child = Node | string | number | null | undefined | false | Child[];
type Props = Record<string, unknown>;

export function h<K extends keyof HTMLElementTagNameMap>(tag: K, props: Props = {}, ...children: Child[]):
  HTMLElementTagNameMap[K] {
  const el = document.createElement(tag);
  for (const [key, value] of Object.entries(props)) {
    if (value === false || value == null) continue;
    if (key.startsWith("on") && typeof value === "function") el.addEventListener(key.slice(2), value as EventListener);
    else if (key in el && key !== "list") (el as unknown as Record<string, unknown>)[key] = value;
    else el.setAttribute(key, value === true ? "" : String(value));
  }
  append(el, children);
  return el;
}

function append(el: Element, children: Child[]): void {
  for (const child of children) {
    if (child == null || child === false) continue;
    if (Array.isArray(child)) append(el, child);
    else el.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
}

export function render(container: Element, ...children: Child[]): void {
  container.replaceChildren();
  append(container, children);
}

export function notify(text: string, isError = false): void {
  const el = h("div", { className: "toast" + (isError ? " error" : "") }, text);
  document.getElementById("toasts")?.append(el);
  setTimeout(() => el.remove(), isError ? 6000 : 3000);
}

export const errorMessage = (error: unknown): string =>
  error instanceof Error ? error.message : t("Algo deu errado. Tente de novo.");

// ------------------------------------------------------------------ money (integer cents)
export const CURRENCIES = ["BRL", "USD", "EUR"] as const;
export type Currency = (typeof CURRENCIES)[number];

export const formatMoney = (cents: number, currency: string = "BRL"): string =>
  (cents / 100).toLocaleString(locale(), { style: "currency", currency });

/** 123456 -> "1.234,56" (Portuguese) or "1,234.56" (English): an amount in a field, read back by toCents. */
export const centsToText = (cents: number | null | undefined): string =>
  cents == null ? "" : (cents / 100).toLocaleString(locale(), { minimumFractionDigits: 2, maximumFractionDigits: 2 });

/** "80,50", "1.200", "R$ 1.200,00" (Portuguese) or "80.50", "1,200", "$1,200.00" (English) -> integer cents.
 *  null if it is not an amount. */
export function toCents(text: string): number | null {
  let cleaned = String(text).trim().replace(/\s/g, "").replace(/^(R\$|US\$|€|\$)/, "");
  if (lang() === "en") cleaned = cleaned.replace(/[.,]/g, (c) => (c === "." ? "," : "."));   // to the Brazilian form
  if (!/^\d{1,3}(\.\d{3})*(,\d{1,2})?$|^\d+(,\d{1,2})?$/.test(cleaned)) return null;
  const [whole, cents = ""] = cleaned.replace(/\./g, "").split(",");
  return Number(whole) * 100 + Number(cents.padEnd(2, "0"));
}

// ------------------------------------------------------------------ time worked (whole minutes)
/** 150 -> "2:30" */
export const formatMinutes = (minutes: number): string =>
  `${Math.floor(minutes / 60)}:${String(minutes % 60).padStart(2, "0")}`;

/** 150 -> "2,50 h" */
export const formatHours = (minutes: number): string =>
  `${(minutes / 60).toLocaleString(locale(), { minimumFractionDigits: 2, maximumFractionDigits: 2 })} h`;

/** "2:30", "2h30", "2,5", "2.5", "2" (hours) or "45m" (minutes) -> minutes. null if it is not a duration. */
export function toMinutes(text: string): number | null {
  const t = String(text).trim().toLowerCase().replace(/\s/g, "");
  if (t === "") return null;
  let m = /^(\d{1,5})[:h](\d{1,2})m?$/.exec(t);
  if (m) return Number(m[2]) < 60 ? Number(m[1]) * 60 + Number(m[2]) : null;
  m = /^(\d{1,5})m(in)?$/.exec(t);
  if (m) return Number(m[1]);
  m = /^(\d{1,5})([.,]\d{1,2})?h?$/.exec(t);
  if (m) return Math.round(Number(m[1] + (m[2] || "").replace(",", ".")) * 60);
  return null;
}

// ------------------------------------------------------------------ dates (Brasília, UTC-3 all year)
/** This moment in Brasília, "YYYY-MM-DDTHH:MM", whatever the device's time zone. */
export const nowLocal = (): string => new Date(Date.now() - 3 * 3600_000).toISOString().slice(0, 16);
export const today = (): string => nowLocal().slice(0, 10);

/** "2026-11-20" -> "20/11/2026" (English: "11/20/2026"); with the time, "20/11/2026 14:30". */
export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "";
  const [y, m, day] = [iso.slice(0, 4), iso.slice(5, 7), iso.slice(8, 10)];
  const d = lang() === "en" ? `${m}/${day}/${y}` : `${day}/${m}/${y}`;
  return iso.length > 10 ? `${d} ${iso.slice(11, 16)}` : d;
}

export function addDays(iso: string, days: number): string {
  const d = new Date(`${iso}T12:00:00Z`);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

// ------------------------------------------------------------------ widgets
/** Runs an action with the button disabled, so repeated clicks don't send it twice. */
export async function whileDisabled<T>(button: HTMLButtonElement, action: () => Promise<T>): Promise<T> {
  button.disabled = true;
  try { return await action(); } finally { button.disabled = false; }
}

/** Opens a modal <dialog>. It is removed from the page when closed; clicking outside it closes it too. */
export function openDialog(title: string, ...children: Child[]): HTMLDialogElement {
  const dialog = h("dialog", { className: "dialog" }, h("h2", {}, title), ...children);
  dialog.addEventListener("click", (e) => {          // the backdrop counts as the <dialog> itself
    const r = dialog.getBoundingClientRect();
    const outside = e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom;
    if (e.target === dialog && outside) dialog.close();
  });
  dialog.addEventListener("close", () => dialog.remove());
  document.body.append(dialog);
  dialog.showModal();
  return dialog;
}

/** A form inside a dialog: `fields`, then Salvar / Cancelar. `save` returns true to close the dialog. */
export function formDialog(title: string, fields: Child[], save: () => Promise<boolean | void>,
  submitText = t("Salvar")): HTMLDialogElement {
  const submit = h("button", { className: "primary", type: "submit" }, submitText);
  const form = h("form", {}, fields, h("div", { className: "actions" }, submit,
    h("button", { className: "secondary", type: "button", onclick: () => dialog.close() }, t("Cancelar"))));
  const dialog = openDialog(title, form);
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    void whileDisabled(submit, async () => {
      try {
        if ((await save()) !== false) dialog.close();
      } catch (error) { notify(errorMessage(error), true); }
    });
  });
  (form.querySelector("input, select, textarea") as HTMLElement | null)?.focus();
  return dialog;
}

/** A labelled field. */
export function field(label: string, input: HTMLElement, hint?: string): Child[] {
  if (!input.id) input.id = `f-${Math.random().toString(36).slice(2, 9)}`;
  return [h("label", { htmlFor: input.id }, label), input, hint ? h("p", { className: "muted hint" }, hint) : null];
}

export async function confirmAction(text: string, confirmText = t("Excluir")): Promise<boolean> {
  return new Promise((resolve) => {
    let answer = false;
    const ok = h("button", { className: "danger", onclick: () => { answer = true; dialog.close(); } }, confirmText);
    const dialog = openDialog(t("Confirmar"), h("p", {}, text), h("div", { className: "actions" }, ok,
      h("button", { className: "secondary", onclick: () => dialog.close() }, t("Cancelar"))));
    dialog.addEventListener("close", () => resolve(answer));
    ok.focus();
  });
}

export interface MenuItem { text: string; onclick: (e: Event) => void; danger?: boolean }

/** A "⋮" button that opens a small menu of a row's actions (Editar, Excluir...). */
export function actionsMenu(label: string, items: (MenuItem | false | null | undefined)[]): HTMLElement {
  const list = h("div", { className: "menu-list", role: "menu", hidden: true },
    items.filter((i): i is MenuItem => Boolean(i)).map(({ text, onclick, danger }) => h("button", {
      role: "menuitem", className: danger ? "danger-item" : null,
      onclick: (e: Event) => { close(); onclick(e); } }, text)));
  const button = h("button", { className: "kebab", title: t("Ações"), "aria-label": t("Ações: {name}", { name: label }),
    "aria-haspopup": "menu", "aria-expanded": "false",
    onclick: (e: Event) => { e.stopPropagation(); if (list.hidden) open(); else close(); } }, "⋮");
  const outside = (e: Event) => { if (!list.contains(e.target as Node) && e.target !== button) close(); };
  const keys = (e: KeyboardEvent) => { if (e.key === "Escape") { close(); button.focus(); } };
  let openedAt = 0;
  const scrolled = () => { if (button.getBoundingClientRect().top !== openedAt) close(); };
  function open(): void {
    const r = button.getBoundingClientRect();
    openedAt = r.top;
    list.style.right = `${document.documentElement.clientWidth - r.right}px`;
    list.hidden = false;
    const below = r.bottom + 4 + list.offsetHeight <= window.innerHeight;
    list.style.top = `${below ? r.bottom + 4 : Math.max(4, r.top - 4 - list.offsetHeight)}px`;
    button.setAttribute("aria-expanded", "true");
    document.addEventListener("click", outside, true);
    document.addEventListener("keydown", keys);
    document.addEventListener("scroll", scrolled, true);
    (list.querySelector("button") as HTMLButtonElement | null)?.focus();
  }
  function close(): void {
    list.hidden = true;
    button.setAttribute("aria-expanded", "false");
    document.removeEventListener("click", outside, true);
    document.removeEventListener("keydown", keys);
    document.removeEventListener("scroll", scrolled, true);
  }
  return h("div", { className: "menu" }, button, list);
}

const SVG = "http://www.w3.org/2000/svg";
const EYE = "M1 12s4-7 11-7 11 7 11 7-4 7-11 7S1 12 1 12z M12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6z";
const EYE_OFF = "M3 3l18 18 M10.6 5.1A10.7 10.7 0 0 1 12 5c7 0 11 7 11 7a18 18 0 0 1-3.2 4.1 M6.6 6.6A18 18 0 0 0 1 12s4 7 11 7a10.6 10.6 0 0 0 5.4-1.6 M9.9 9.9a3 3 0 0 0 4.2 4.2";

/** Stroke icons (24x24 paths), drawn in the text color. */
export const ICONS = {
  tasks: "M9 11l3 3 8-8 M20 12v7a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h9",
  billing: "M4 6h16a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2z M12 10a2.5 2.5 0 1 0 0 5 2.5 2.5 0 0 0 0-5z",
  payments: "M4 19V9 M10 19V5 M16 19v-7 M22 19H2",
  projects: "M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z",
  companies: "M3 21h18 M5 21V7l7-4 7 4v14 M9 21v-6h6v6",
  logout: "M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4 M16 17l5-5-5-5 M21 12H9",
  settings: "M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z",
} as const;

export function icon(name: keyof typeof ICONS): SVGSVGElement {
  const svg = document.createElementNS(SVG, "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("aria-hidden", "true");
  svg.setAttribute("class", "icon-svg");
  const path = document.createElementNS(SVG, "path");
  path.setAttribute("d", ICONS[name]);
  svg.append(path);
  return svg;
}

/** A password input with an eye button that shows / hides what was typed. */
export function revealable(input: HTMLInputElement): HTMLElement {
  const path = document.createElementNS(SVG, "path");
  const icon = document.createElementNS(SVG, "svg");
  icon.setAttribute("viewBox", "0 0 24 24");
  icon.setAttribute("aria-hidden", "true");
  icon.append(path);
  const toggle = h("button", { type: "button", className: "reveal", onclick: () => {
    input.type = input.type === "password" ? "text" : "password";
    update();
    input.focus();
  } }, icon);
  function update(): void {
    const shown = input.type === "text";
    path.setAttribute("d", shown ? EYE_OFF : EYE);
    toggle.setAttribute("aria-label", shown ? t("Ocultar senha") : t("Mostrar senha"));
    toggle.title = shown ? t("Ocultar senha") : t("Mostrar senha");
    toggle.setAttribute("aria-pressed", String(shown));
  }
  update();
  return h("div", { className: "password-field" }, input, toggle);
}
