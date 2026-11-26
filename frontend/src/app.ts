// The menu, once logged in. The screens before it (Entrar, Criar conta) are in screens/login.ts.
// Configurações is apart from the menu: the gear in the top bar (phones) or at the foot of the sidebar.
import { CONFIG } from "./config.js";
import { getProfile, isSignedIn, signOut } from "./auth.js";
import { N_, isLang, lang, setLang, t } from "./i18n.js";
import { h, ICONS, icon, render } from "./util.js";
import { mount as billing } from "./screens/billing.js";
import { loginScreen } from "./screens/login.js";
import { mount as payments } from "./screens/payments.js";
import { mount as projects } from "./screens/projects.js";
import { mount as settings } from "./screens/settings.js";
import { mount as tasks } from "./screens/tasks.js";

const content = document.getElementById("content")!;
type Mount = (area: HTMLElement) => Promise<void>;
const SCREENS: [string, Mount, keyof typeof ICONS][] = [            // [name in the menu, mount, icon]
  [N_("Tarefas"), tasks, "tasks"], [N_("Faturamento"), billing, "billing"], [N_("Pagamentos"), payments, "payments"],
  [N_("Projetos"), projects, "projects"]];
const SETTINGS = -1;

function start(page = 0): void {
  // Phones and tablets: the menu is a bar fixed at the bottom and the account sits in the top bar.
  // 1024px and up: the same menu is a sidebar and the account sits at its foot (style.css).
  document.getElementById("top-bar")!.hidden = document.getElementById("sidebar")!.hidden = false;
  document.body.classList.add("signed-in");

  const buttons = SCREENS.map(([name, , iconName], i) =>
    h("button", { onclick: () => open(i) }, icon(iconName), h("span", {}, t(name))));
  const settingsButtons: HTMLButtonElement[] = [];
  const open = (index: number) => {
    buttons.forEach((b, i) => (i === index ? b.setAttribute("aria-current", "page") : b.removeAttribute("aria-current")));
    settingsButtons.forEach((b) => (index === SETTINGS ? b.setAttribute("aria-current", "page")
      : b.removeAttribute("aria-current")));
    const area = h("div");
    render(content, area);
    window.scrollTo(0, 0);
    if (index === SETTINGS) void settings(area, () => start(SETTINGS));     // a new language redraws everything
    else void SCREENS[index]![1](area);
  };
  render(document.getElementById("menu")!, buttons);

  for (const place of ["top-account", "side-account"]) {
    const gear = h("button", { className: "settings-link", "aria-label": t("Configurações"), title: t("Configurações"),
      onclick: () => open(SETTINGS) }, icon("settings"), h("span", {}, t("Configurações")));
    settingsButtons.push(gear);
    render(document.getElementById(place)!, gear, CONFIG.skipLogin
      ? h("span", { className: "local-mode" }, t("Modo local, sem login"))      // local server: nobody to log out
      : h("button", { className: "logout", "aria-label": t("Sair"), title: t("Sair"),
        onclick: () => { signOut(); location.reload(); } }, icon("logout"), h("span", {}, t("Sair"))));
  }
  open(page);
}

/** Logged in: the language saved in the login (chosen on another device, say) wins over this browser's. */
async function startSignedIn(): Promise<void> {
  start();
  if (CONFIG.skipLogin) return;
  try {
    const { locale } = await getProfile();
    if (isLang(locale) && locale !== lang()) { setLang(locale); start(); }
  } catch { /* the app works without it */ }
}

if (!CONFIG.apiUrl || (!CONFIG.clientId && !CONFIG.skipLogin)) {
  render(content, h("p", { className: "notice" }, t("Sistema ainda não configurado (js/config.js vazio).")));
} else if (isSignedIn()) void startSignedIn();
else loginScreen(() => void startSignedIn());
