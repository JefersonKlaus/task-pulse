// The menu, once logged in. The screens before it (Entrar, Criar conta) are in screens/login.ts.
import { CONFIG } from "./config.js";
import { isSignedIn, signOut } from "./auth.js";
import { h, ICONS, icon, render } from "./util.js";
import { mount as billing } from "./screens/billing.js";
import { loginScreen } from "./screens/login.js";
import { mount as payments } from "./screens/payments.js";
import { mount as projects } from "./screens/projects.js";
import { mount as tasks } from "./screens/tasks.js";

const content = document.getElementById("content")!;
type Mount = (area: HTMLElement) => Promise<void>;
const SCREENS: [string, Mount, keyof typeof ICONS][] = [            // [name in the menu, mount, icon]
  ["Tarefas", tasks, "tasks"], ["Faturamento", billing, "billing"], ["Pagamentos", payments, "payments"],
  ["Projetos", projects, "projects"]];

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
else loginScreen(start);
