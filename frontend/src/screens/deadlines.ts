// A project's deadlines (packages to deliver): as many as needed, each on one day, every week on a weekday
// or every month on a day. The recurring ones move on by themselves: the API sends each one's next day
// (`next_on`) and the nearest of all (`next_deadline`). Edited in the project form; shown on its page and in
// the lists.
import { N_, locale, t } from "../i18n.js";
import type { Deadline, DeadlineKind, Project } from "../types.js";
import { formatDate, h } from "../util.js";

const KINDS: [DeadlineKind, string][] = [["weekly", N_("Toda semana")], ["monthly", N_("Todo mês")], ["date", N_("Num dia")]];

/** "segunda-feira"... for 1 (Monday) to 7 (Sunday), in the chosen language. 1 Jan 2024 was a Monday. */
export function weekdayName(weekday: number): string {
  return new Intl.DateTimeFormat(locale(), { weekday: "long" }).format(new Date(2024, 0, weekday));
}

/** When it is: "Toda semana, sexta-feira", "Todo mês, dia 30", "Em 15/01/2027". */
export function deadlineWhen(d: Deadline): string {
  if (d.kind === "weekly") return t("Toda semana, {weekday}", { weekday: weekdayName(d.weekday || 1) });
  if (d.kind === "monthly") return t("Todo mês, dia {day}", { day: d.month_day || 1 });
  return t("Em {date}", { date: formatDate(d.on) });
}

/** The nearest deadline, for a list: "Pacote semanal 28/11/2026". */
export function nextDeadlineText(p: Project): string | null {
  const next = p.next_deadline;
  if (!next?.next_on) return null;
  return t("Prazo {date}", { date: formatDate(next.next_on) }) + (next.label ? ` · ${next.label}` : "");
}

/** The deadlines on a project's page, nearest first; past ones last. */
export function deadlinesCard(project: Project, edit: () => unknown): HTMLElement {
  const sorted = [...project.deadlines].sort((a, b) =>
    (a.next_on || "9999").localeCompare(b.next_on || "9999"));
  return h("div", { className: "card", id: "deadlines" },
    h("div", { className: "row" }, h("h2", {}, t("Prazos")),
      h("button", { className: "secondary small", id: "edit-deadlines", onclick: edit }, t("Editar prazos"))),
    sorted.length
      ? h("ul", { className: "deadline-list" }, sorted.map((d) => h("li", { className: "deadline" + (d.next_on ? "" : " past"),
        "data-deadline": d.label || deadlineWhen(d) },
      h("div", {}, h("strong", {}, d.label || t("Prazo")), h("div", { className: "muted" }, deadlineWhen(d))),
      h("span", { className: "deadline-next" }, d.next_on ? formatDate(d.next_on) : t("passou")))))
      : h("p", { className: "muted" }, t("Sem prazos. Um projeto pode ter vários: por semana, por mês ou num dia.")));
}

/** The deadline rows of the project form, and `read()` that turns them into the API's list. */
export function deadlineFields(deadlines: Deadline[]): { element: HTMLElement; read: () => Record<string, unknown>[] } {
  const rows = h("div", { id: "p-deadlines" });
  const readers: { row: HTMLElement; read: () => Record<string, unknown> }[] = [];

  const add = (d?: Deadline) => {
    const label = h("input", { maxLength: 80, placeholder: t("Nome (ex.: Pacote 1)"), "aria-label": t("Nome do prazo"),
      value: d?.label || "" });
    const kind = h("select", { "aria-label": t("Repete"), className: "deadline-kind" },
      KINDS.map(([value, text]) => h("option", { value, selected: value === (d?.kind || "weekly") }, t(text))));
    const weekday = h("select", { "aria-label": t("Dia da semana") }, [1, 2, 3, 4, 5, 6, 7].map((n) =>
      h("option", { value: String(n), selected: n === (d?.weekday || 5) }, weekdayName(n))));
    const monthDay = h("input", { type: "number", min: 1, max: 31, step: 1, "aria-label": t("Dia do mês"),
      placeholder: t("dia"), value: d?.month_day ? String(d.month_day) : "" });
    const on = h("input", { type: "date", "aria-label": t("Data do prazo"), value: d?.on || "" });
    const show = () => {
      weekday.hidden = kind.value !== "weekly";
      monthDay.hidden = kind.value !== "monthly";
      on.hidden = kind.value !== "date";
      monthDay.required = kind.value === "monthly";      // the browser asks for the value that is shown
      on.required = kind.value === "date";
    };
    kind.addEventListener("change", show);
    show();
    const row: HTMLElement = h("div", { className: "deadline-row" }, label, kind, weekday, monthDay, on,
      h("button", { type: "button", className: "secondary small", "aria-label": t("Remover prazo"),
        onclick: () => { row.remove(); readers.splice(readers.findIndex((r) => r.row === row), 1); } }, "×"));
    readers.push({ row, read: () => ({
      ...(d ? { id: d.id } : {}), label: label.value, kind: kind.value,
      ...(kind.value === "weekly" ? { weekday: Number(weekday.value) } : {}),
      ...(kind.value === "monthly" ? { month_day: Number(monthDay.value) } : {}),
      ...(kind.value === "date" ? { on: on.value } : {}),
    }) });
    rows.append(row);
  };
  deadlines.forEach(add);

  const element = h("div", {},
    h("span", { className: "field-label" }, t("Prazos (pacotes)")),
    h("p", { className: "muted hint" }, t("Quantos precisar: toda semana, todo mês ou num dia. Os que repetem andam sozinhos.")),
    rows,
    h("button", { type: "button", className: "secondary small", id: "add-deadline", onclick: () => add() }, t("+ Prazo")));
  return { element, read: () => readers.map((r) => r.read()) };
}
