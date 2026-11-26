// Before logging in: Entrar (e-mail + senha), Criar conta (nome, e-mail, senha) and Confirmar e-mail (the
// 6-digit code Cognito sends to a new account). A login created by the administrator may also be asked
// for a new password on its first access. Every screen here has the language switch at its foot.
import {
  type Challenge, confirmSignUp, normalizeEmail, resendCode, setNewPassword, signIn, signUp,
} from "../auth.js";
import { LANGUAGES, lang, setLang, t } from "../i18n.js";
import { errorMessage, h, notify, render, revealable, whileDisabled } from "../util.js";

const passwordRule = () => t("10+ caracteres, com maiúscula, minúscula e número");
const content = () => document.getElementById("content")!;

/** The card every screen here shares: the brand on top, then the form, then the language switch. */
function card(form: HTMLFormElement, redraw: () => void, ...children: (Node | false | null | undefined)[]): HTMLFormElement {
  form.className = "card login";
  form.prepend(h("div", { className: "login-brand" }, h("span", { className: "logo", "aria-hidden": "true" }),
    h("h1", {}, "Task Pulse"), h("p", {}, t("Cada hora trabalhada, cada tarefa aprovada e quanto ela vale."))));
  for (const child of children) if (child) form.append(child);
  form.append(h("p", { className: "login-languages" }, LANGUAGES.map(([code, name]) =>
    h("button", { type: "button", className: "link", lang: code, "aria-pressed": String(code === lang()),
      onclick: () => { setLang(code); redraw(); } }, name))));
  return form;
}

function onSubmit(form: HTMLFormElement, button: HTMLButtonElement, action: () => Promise<void>): void {
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    void whileDisabled(button, async () => {
      try { await action(); } catch (error) { notify(errorMessage(error), true); }
    });
  });
}

const switchLink = (question: string, text: string, onclick: () => void) =>
  h("p", { className: "login-switch" }, question, " ", h("button", { type: "button", className: "link", onclick }, text));

export function loginScreen(start: () => void, email = ""): void {
  const emailInput = h("input", { id: "l-email", type: "email", autocomplete: "email", required: true, value: email,
    maxLength: 254, placeholder: t("voce@exemplo.com") });
  const password = h("input", { id: "l-password", type: "password", required: true, autocomplete: "current-password" });
  const button = h("button", { className: "primary", type: "submit" }, t("Entrar"));
  const form = card(h("form"), () => loginScreen(start, emailInput.value),
    h("h2", {}, t("Entrar")),
    h("label", { htmlFor: "l-email" }, t("E-mail")), emailInput,
    h("label", { htmlFor: "l-password" }, t("Senha")), revealable(password),
    h("div", { className: "actions" }, button),
    switchLink(t("Ainda não tem conta?"), t("Criar conta"), () => signUpScreen(start, emailInput.value)));
  onSubmit(form, button, async () => {
    const r = await signIn(emailInput.value, password.value);
    if (r.challenge) return newPasswordScreen(start, r.challenge);
    if (r.unconfirmed) {                     // created but never confirmed: send a new code and ask for it
      await resendCode(emailInput.value);
      return confirmScreen(start, emailInput.value, password.value);
    }
    start();
  });
  render(content(), form);
  (email ? password : emailInput).focus();
}

export function signUpScreen(start: () => void, email = ""): void {
  const name = h("input", { id: "s-name", autocomplete: "name", required: true, maxLength: 80 });
  const emailInput = h("input", { id: "s-email", type: "email", autocomplete: "email", required: true, value: email,
    maxLength: 254, placeholder: t("voce@exemplo.com") });
  const password = h("input", { id: "s-password", type: "password", required: true, autocomplete: "new-password" });
  const repeat = h("input", { id: "s-repeat", type: "password", required: true, autocomplete: "new-password" });
  const button = h("button", { className: "primary", type: "submit" }, t("Criar conta"));
  const form = card(h("form"), () => signUpScreen(start, emailInput.value),
    h("h2", {}, t("Criar conta")),
    h("label", { htmlFor: "s-name" }, t("Nome")), name,
    h("label", { htmlFor: "s-email" }, t("E-mail")), emailInput,
    h("label", { htmlFor: "s-password" }, t("Senha")), revealable(password),
    h("p", { className: "muted field-hint" }, passwordRule()),
    h("label", { htmlFor: "s-repeat" }, t("Repita a senha")), revealable(repeat),
    h("div", { className: "actions" }, button),
    switchLink(t("Já tem conta?"), t("Entrar"), () => loginScreen(start, emailInput.value)));
  onSubmit(form, button, async () => {
    if (!name.value.trim()) throw new Error(t("Digite o seu nome."));
    checkNewPassword(password.value, repeat.value);
    const { sentTo } = await signUp(name.value, emailInput.value, password.value, lang());
    notify(t("Enviamos um código para {email}.", { email: sentTo }));
    confirmScreen(start, emailInput.value, password.value);
  });
  render(content(), form);
  name.focus();
}

/** The code sent by e-mail. With the password still in memory (just typed), it logs in right after. */
function confirmScreen(start: () => void, typed: string, password: string): void {
  const email = normalizeEmail(typed);
  const code = h("input", { id: "c-code", inputMode: "numeric", autocomplete: "one-time-code", required: true,
    maxLength: 6, pattern: "[0-9]{6}", placeholder: "000000", className: "code-input" });
  const button = h("button", { className: "primary", type: "submit" }, t("Confirmar"));
  const resend = h("button", { type: "button", className: "link" }, t("Reenviar código"));
  resend.addEventListener("click", () => void whileDisabled(resend, async () => {
    try { await resendCode(email); notify(t("Código reenviado.")); } catch (error) { notify(errorMessage(error), true); }
  }));
  const form = card(h("form"), () => confirmScreen(start, email, password),
    h("h2", {}, t("Confirme o seu e-mail")),
    h("p", { className: "muted" }, t("Digite o código de 6 dígitos que enviamos para"), " ", h("strong", {}, email),
      ". ", t("Confira também a caixa de spam.")),
    h("label", { htmlFor: "c-code" }, t("Código")), code,
    h("div", { className: "actions" }, button),
    h("p", { className: "login-switch" }, t("Não chegou?"), " ", resend, " · ",
      h("button", { type: "button", className: "link", onclick: () => loginScreen(start, email) }, t("Voltar"))));
  onSubmit(form, button, async () => {
    await confirmSignUp(email, code.value);
    notify(t("E-mail confirmado."));
    const r = await signIn(email, password);
    if (r.challenge) return newPasswordScreen(start, r.challenge);
    start();
  });
  render(content(), form);
  code.focus();
}

function newPasswordScreen(start: () => void, challenge: Challenge): void {
  const password = h("input", { id: "l-password", type: "password", required: true, autocomplete: "new-password" });
  const button = h("button", { className: "primary", type: "submit" }, t("Definir senha"));
  const form = card(h("form"), () => newPasswordScreen(start, challenge),
    h("h2", {}, t("Primeiro acesso")),
    h("p", { className: "muted" }, t("Escolha a sua senha ({rule}).", { rule: passwordRule() })),
    h("label", { htmlFor: "l-password" }, t("Nova senha")), revealable(password),
    h("div", { className: "actions" }, button));
  onSubmit(form, button, async () => { await setNewPassword(challenge, password.value); start(); });
  render(content(), form);
  password.focus();
}

/** The same policy as the Cognito pool (infra/cognito.tf), checked here to answer before the request. */
export function checkNewPassword(password: string, repeat: string): void {
  const strong = password.length >= 10 && /[a-z]/.test(password) && /[A-Z]/.test(password) && /\d/.test(password);
  if (!strong) throw new Error(t("A senha precisa ter {rule}.", { rule: passwordRule() }));
  if (password !== repeat) throw new Error(t("As senhas não são iguais."));
}
