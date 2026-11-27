// Sobre: what Task Pulse is, that it is open source and meant to stay free, who made it, and where the
// code is (to run it on your own AWS account or to help). Opened from the "i" next to Configurações, and
// from the login screen (no login needed).
import { t } from "../i18n.js";
import { h, icon } from "../util.js";

export const AUTHOR = "Jeferson Klaus";
export const LINKEDIN = "https://www.linkedin.com/in/jeferson-klaus-cb/";
export const REPOSITORY = "https://github.com/JefersonKlaus/task-pulse";

const external = (href: string, text: string, id: string) =>
  h("a", { className: "button secondary external", href, target: "_blank", rel: "noopener noreferrer", id },
    h("span", {}, text), icon("external"));

/** The page. `back`: a link above the title (the login screen uses it to go back). */
export function aboutPage(back?: { label: string; onclick: () => void }): HTMLElement {
  return h("div", { className: "about", id: "about" },
    back && h("button", { className: "link back", onclick: back.onclick }, `‹ ${back.label}`),
    h("h1", {}, t("Sobre o Task Pulse")),
    h("p", { className: "about-lead" }, t("O Task Pulse registra cada hora trabalhada e cada tarefa aprovada, e mostra "
      + "quanto ela vale, quanto você deveria receber e quanto recebeu.")),

    h("section", { className: "card about-card" },
      h("span", { className: "about-icon", "aria-hidden": "true" }, "♥"),
      h("div", {},
        h("h2", {}, t("Gratuito e de código aberto")),
        h("p", {}, t("É um projeto de código aberto, feito para ajudar todo mundo que trabalha por tarefa ou por hora.")),
        h("p", {}, t("A intenção é que ele seja sempre gratuito, e vou fazer tudo o que puder para que continue assim.")))),

    h("section", { className: "card about-card" },
      h("span", { className: "about-icon", "aria-hidden": "true" }, "JK"),
      h("div", {},
        h("h2", {}, t("Quem fez")),
        h("p", {}, t("Desenvolvido por {name}.", { name: AUTHOR })),
        external(LINKEDIN, t("LinkedIn"), "about-linkedin"))),

    h("section", { className: "card about-card" },
      h("span", { className: "about-icon", "aria-hidden": "true" }, "</>"),
      h("div", {},
        h("h2", {}, t("Rode na sua conta ou ajude o projeto")),
        h("p", {}, t("Quer levantar o Task Pulse na sua própria conta da AWS, sugerir uma melhoria ou contribuir com "
          + "código? O repositório tem tudo, com o passo a passo para publicar.")),
        external(REPOSITORY, t("Ver o código no GitHub"), "about-github"))));
}
