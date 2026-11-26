// Configurações: apart from the other pages (it opens from the gear in the top bar or at the foot of the
// sidebar, never from the menu). The system's language, and the login's name and password. The language is
// kept in the browser and, when logged in, in the login itself (Cognito's `locale`), so it follows the
// person to another device. The name and the password live only in Cognito.
import { changePassword, getProfile, updateProfile } from "../auth.js";
import { CONFIG } from "../config.js";
import { type Lang, LANGUAGES, lang, setLang, t } from "../i18n.js";
import { errorMessage, h, notify, render, revealable, whileDisabled } from "../util.js";
import { checkNewPassword } from "./login.js";

/** `onLanguage`: redraws the whole app (menu included) in the new language, back on this page. */
export async function mount(area: HTMLElement, onLanguage: () => void): Promise<void> {
  render(area, h("p", { className: "notice" }, t("Carregando…")));
  const local = Boolean(CONFIG.skipLogin);
  let profile = { name: "", email: "", locale: "" };
  if (!local) {
    try { profile = await getProfile(); } catch (error) { notify(errorMessage(error), true); }
  }

  // ------------------------------------------------------------ language
  const name = `lang-${Math.random().toString(36).slice(2, 7)}`;
  const language = h("form", { className: "card", id: "settings-language" },
    h("h2", {}, t("Idioma")),
    h("p", { className: "muted hint" }, t("O idioma de todas as telas, dos valores e das datas.")),
    h("fieldset", { className: "choices" }, h("legend", { className: "sr-only" }, t("Idioma")),
      LANGUAGES.map(([code, label]) => h("label", { className: "choice", lang: code },
        h("input", { type: "radio", name, value: code, checked: code === lang(),
          onchange: () => void choose(code) }), label))));
  async function choose(code: Lang): Promise<void> {
    setLang(code);
    if (!local) {
      try { await updateProfile({ locale: code }); } catch (error) { notify(errorMessage(error), true); }
    }
    onLanguage();
    notify(t("Idioma alterado."));
  }

  // ------------------------------------------------------------ account (not in local mode: there is no login)
  if (local) {
    return render(area, h("h1", {}, t("Configurações")), language,
      h("div", { className: "card" }, h("h2", {}, t("Conta")),
        h("p", { className: "muted", id: "settings-local" },
          t("Modo local, sem login: nome e senha só existem no sistema publicado."))));
  }

  const nameInput = h("input", { id: "set-name", autocomplete: "name", required: true, maxLength: 80, value: profile.name });
  const saveName = h("button", { className: "primary", type: "submit" }, t("Salvar nome"));
  const account = h("form", { className: "card", id: "settings-name" },
    h("h2", {}, t("Conta")),
    h("label", { htmlFor: "set-email" }, t("E-mail")),
    h("input", { id: "set-email", type: "email", value: profile.email, readOnly: true, disabled: true }),
    h("p", { className: "muted hint" }, t("O e-mail é o seu login e não muda.")),
    h("label", { htmlFor: "set-name" }, t("Nome")), nameInput,
    h("div", { className: "actions" }, saveName));
  account.addEventListener("submit", (e) => {
    e.preventDefault();
    void whileDisabled(saveName, async () => {
      try {
        const value = nameInput.value.trim();
        if (!value) throw new Error(t("Digite o seu nome."));
        await updateProfile({ name: value });
        notify(t("Nome salvo."));
      } catch (error) { notify(errorMessage(error), true); }
    });
  });

  const current = h("input", { id: "set-current", type: "password", required: true, autocomplete: "current-password" });
  const proposed = h("input", { id: "set-new", type: "password", required: true, autocomplete: "new-password" });
  const repeat = h("input", { id: "set-repeat", type: "password", required: true, autocomplete: "new-password" });
  const savePassword = h("button", { className: "primary", type: "submit" }, t("Alterar senha"));
  const password = h("form", { className: "card", id: "settings-password" },
    h("h2", {}, t("Senha")),
    h("label", { htmlFor: "set-current" }, t("Senha atual")), revealable(current),
    h("label", { htmlFor: "set-new" }, t("Nova senha")), revealable(proposed),
    h("p", { className: "muted field-hint" }, t("10+ caracteres, com maiúscula, minúscula e número")),
    h("label", { htmlFor: "set-repeat" }, t("Repita a nova senha")), revealable(repeat),
    h("div", { className: "actions" }, savePassword));
  password.addEventListener("submit", (e) => {
    e.preventDefault();
    void whileDisabled(savePassword, async () => {
      try {
        checkNewPassword(proposed.value, repeat.value);
        await changePassword(current.value, proposed.value);
        password.reset();
        notify(t("Senha alterada."));
      } catch (error) { notify(errorMessage(error), true); }
    });
  });

  render(area, h("h1", {}, t("Configurações")), language, account, password);
}
