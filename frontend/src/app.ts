// The menu and the login screen.
import { CONFIG } from "./config.js";
import { type Challenge, isSignedIn, setNewPassword, signIn, signOut } from "./auth.js";
import { errorMessage, h, ICONS, icon, notify, render, revealable, whileDisabled } from "./util.js";
import { mount as billing } from "./screens/billing.js";
import { mount as payments } from "./screens/payments.js";
import { mount as projects } from "./screens/projects.js";
import { mount as tasks } from "./screens/tasks.js";

const content = document.getElementById("content")!;
type Mount = (area: HTMLElement) => Promise<void>;
const SCREENS: [string, Mount, keyof typeof ICONS][] = [            // [name in the menu, mount, icon]
  ["Tarefas", tasks, "tasks"], ["Faturamento", billing, "billing"], ["Pagamentos", payments, "payments"],
  ["Projetos", projects, "projects"]];

function loginScreen(challenge: Challenge | null = null): void {
  // DDD + number, digits only (no mask): 11987654321
  const phone = h("input", { id: "l-phone", type: "tel", inputMode: "numeric", autocomplete: "tel-national",
    placeholder: "11987654321", maxLength: 11, required: true, title: "DDD + número, só os dígitos (10 ou 11)" });
  const password = h("input", { id: "l-password", type: "password", required: true,
    autocomplete: challenge ? "new-password" : "current-password" });
  const button = h("button", { className: "primary", type: "submit" }, challenge ? "Definir senha" : "Entrar");
  const form = h("form", { className: "card login" },
    h("div", { className: "login-brand" }, h("span", { className: "logo", "aria-hidden": "true" }),
      h("h1", {}, "Task Pulse"),
      h("p", {}, "Cada hora trabalhada, cada tarefa aprovada e quanto ela vale.")),
    challenge && h("p", { className: "muted" },
      "Primeiro acesso: escolha a sua senha (10+ caracteres, com maiúscula, minúscula e número)."),
    !challenge && [h("label", { htmlFor: "l-phone" }, "Celular (DDD + número)"), phone],
    h("label", { htmlFor: "l-password" }, challenge ? "Nova senha" : "Senha"), revealable(password),
    h("div", { className: "actions" }, button));
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    void whileDisabled(button, async () => {
      try {
        if (challenge) { await setNewPassword(challenge, password.value); return start(); }
        const r = await signIn(phone.value.trim(), password.value);
        if (r.challenge) return loginScreen(r.challenge);
        start();
      } catch (error) { notify(errorMessage(error), true); }
    });
  });
  render(content, form);
  (challenge ? password : phone).focus();
}

function start(): void {
  // Phones and tablets: the menu is a bar fixed at the bottom and the account sits in the top bar.
  // 1024px and up: the same menu is a sidebar and the account sits at its foot (style.css).
  document.getElementById("top-bar")!.hidden = document.getElementById("sidebar")!.hidden = false;
  document.body.classList.add("signed-in");

  const buttons = SCREENS.map(([name, , iconName], i) =>
    h("button", { onclick: () => open(i) }, icon(iconName), h("span", {}, name)));
  const open = (index: number) => {
    buttons.forEach((b, i) => (i === index ? b.setAttribute("aria-current", "page") : b.removeAttribute("aria-current")));
    const area = h("div");
    render(content, area);
    window.scrollTo(0, 0);
    void SCREENS[index]![1](area);
  };
  render(document.getElementById("menu")!, buttons);

  for (const place of ["top-account", "side-account"]) {
    render(document.getElementById(place)!, CONFIG.skipLogin
      ? h("span", { className: "local-mode" }, "Modo local, sem login")      // local server: nobody to log out
      : h("button", { className: "logout", "aria-label": "Sair", title: "Sair",
        onclick: () => { signOut(); location.reload(); } }, icon("logout"), h("span", {}, "Sair")));
  }
  open(0);
}

if (!CONFIG.apiUrl || (!CONFIG.clientId && !CONFIG.skipLogin)) {
  render(content, h("p", { className: "notice" }, "Sistema ainda não configurado (js/config.js vazio)."));
} else if (isSignedIn()) start();
else loginScreen();
