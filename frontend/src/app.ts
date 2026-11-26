// The menu and the login screen.
import { CONFIG } from "./config.js";
import { type Challenge, isSignedIn, setNewPassword, signIn, signOut } from "./auth.js";
import { errorMessage, h, notify, render, revealable, whileDisabled } from "./util.js";
import { mount as billing } from "./screens/billing.js";
import { mount as payments } from "./screens/payments.js";
import { mount as projects } from "./screens/projects.js";
import { mount as tasks } from "./screens/tasks.js";

const content = document.getElementById("content")!;
type Mount = (area: HTMLElement) => Promise<void>;
const SCREENS: [string, Mount][] = [            // [name in the menu, mount]
  ["Tarefas", tasks], ["Faturamento", billing], ["Pagamentos", payments], ["Empresas e projetos", projects]];

function loginScreen(challenge: Challenge | null = null): void {
  // DDD + number, digits only (no mask): 11987654321
  const phone = h("input", { id: "l-phone", type: "tel", inputMode: "numeric", autocomplete: "tel-national",
    placeholder: "11987654321", maxLength: 11, required: true, title: "DDD + número, só os dígitos (10 ou 11)" });
  const password = h("input", { id: "l-password", type: "password", required: true,
    autocomplete: challenge ? "new-password" : "current-password" });
  const button = h("button", { className: "primary", type: "submit" }, challenge ? "Definir senha" : "Entrar");
  const form = h("form", { className: "card login" },
    h("h1", {}, "Task Pulse"),
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
  const sidebar = document.getElementById("sidebar")!;
  const backdrop = document.getElementById("backdrop")!;
  const toggle = document.getElementById("menu-toggle")!;
  document.getElementById("top-bar")!.hidden = sidebar.hidden = false;
  document.body.classList.add("signed-in");

  // On phones the sidebar is a drawer: ☰ opens it; choosing a page, the backdrop or Esc closes it.
  const setDrawer = (open: boolean) => {
    sidebar.classList.toggle("open", open);
    backdrop.hidden = !open;
    toggle.setAttribute("aria-expanded", String(open));
    toggle.setAttribute("aria-label", open ? "Fechar menu" : "Abrir menu");
  };
  toggle.onclick = () => setDrawer(!sidebar.classList.contains("open"));
  backdrop.onclick = () => setDrawer(false);
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && sidebar.classList.contains("open")) { setDrawer(false); toggle.focus(); }
  });

  const buttons = SCREENS.map(([name], i) => h("button", { onclick: () => open(i) }, name));
  const open = (index: number) => {
    buttons.forEach((b, i) => (i === index ? b.setAttribute("aria-current", "page") : b.removeAttribute("aria-current")));
    setDrawer(false);
    const area = h("div");
    render(content, area);
    void SCREENS[index]![1](area);
  };
  render(document.getElementById("menu")!, buttons);

  const logout = document.getElementById("logout")!;
  if (CONFIG.skipLogin) {                        // local server: there is nobody to log out
    logout.replaceWith(h("span", { id: "local-mode", className: "muted" }, "Modo local, sem login"));
  } else logout.onclick = () => { signOut(); location.reload(); };
  open(0);
}

if (!CONFIG.apiUrl || (!CONFIG.clientId && !CONFIG.skipLogin)) {
  render(content, h("p", { className: "notice" }, "Sistema ainda não configurado (js/config.js vazio)."));
} else if (isSignedIn()) start();
else loginScreen();
