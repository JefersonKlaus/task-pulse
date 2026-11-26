// Cognito login straight through its public API (no library). Tokens live only in the tab's session.
// CONFIG.skipLogin is only ever set by local/server.py: there is no login and the local server
// answers every request as the same user. The deployed API still requires a valid token for everything.
import { CONFIG } from "./config.js";

const STORAGE_KEY = "pulse.tokens";
const MESSAGES: Record<string, string> = {
  NotAuthorizedException: "E-mail ou senha incorretos.",
  UserNotFoundException: "E-mail ou senha incorretos.",
  UsernameExistsException: "Já existe uma conta com este e-mail. Entre com ela.",
  InvalidParameterException: "E-mail inválido.",
  CodeMismatchException: "Código incorreto. Confira o e-mail e tente de novo.",
  ExpiredCodeException: "Código expirado: peça um novo.",
  CodeDeliveryFailureException: "Não foi possível enviar o e-mail. Confira o endereço.",
  InvalidPasswordException: "A senha precisa ter 10 caracteres, com maiúscula, minúscula e número.",
  TooManyRequestsException: "Muitas tentativas. Espere um pouco.",
  LimitExceededException: "Muitas tentativas. Espere um pouco.",
};

/** One call to Cognito's API. `messages`: what to say for each Cognito error (in Portuguese). */
interface AuthResult { IdToken: string; AccessToken: string; ExpiresIn: number; RefreshToken?: string }
interface Tokens { idToken: string; accessToken: string; expiresAt: number; refresh?: string }
type CognitoAnswer = Record<string, any>;
export interface Challenge { session: string; username: string }

async function cognito(target: string, body: unknown, messages: Record<string, string> = MESSAGES,
  fallback = "Não foi possível entrar. Tente de novo."): Promise<CognitoAnswer> {
  const response = await fetch(`https://cognito-idp.${CONFIG.region}.amazonaws.com/`, {
    method: "POST",
    headers: { "Content-Type": "application/x-amz-json-1.1", "X-Amz-Target": `AWSCognitoIdentityProviderService.${target}` },
    body: JSON.stringify(body),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const type = String(data.__type || "").split("#").pop() || "";
    throw new Error(messages[type] || fallback);
  }
  return data;
}

let cached: Tokens | null = null;

function store(result: AuthResult, previous: Partial<Tokens> = {}): void {
  const t: Tokens = { ...previous, idToken: result.IdToken, accessToken: result.AccessToken,      // access: to change the password
    expiresAt: Date.now() + result.ExpiresIn * 1000 };
  if (result.RefreshToken) t.refresh = result.RefreshToken;
  try { sessionStorage.setItem(STORAGE_KEY, JSON.stringify(t)); } catch { /* private mode: kept in memory only */ }
  cached = t;
}

function load(): Tokens | null {
  if (cached) return cached;
  try { cached = JSON.parse(sessionStorage.getItem(STORAGE_KEY) || "null") as Tokens | null; } catch { cached = null; }
  return cached;
}

/** The e-mail is the login: trimmed and in lower case, so "Ana@X.com " and "ana@x.com" are the same account. */
export function normalizeEmail(email: string): string {
  const value = email.trim().toLowerCase();
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value) || value.length > 254) throw new Error("E-mail inválido.");
  return value;
}

/** What signIn can answer besides "signed in": a new password to choose (a login created by the
 *  administrator), or an account whose e-mail was never confirmed (it needs the code). */
export interface SignInResult { challenge?: Challenge; unconfirmed?: boolean }

export async function signIn(email: string, password: string): Promise<SignInResult> {
  const username = normalizeEmail(email);
  let r: CognitoAnswer;
  try {
    r = await cognito("InitiateAuth", { ClientId: CONFIG.clientId,
      AuthFlow: "USER_PASSWORD_AUTH", AuthParameters: { USERNAME: username, PASSWORD: password } },
    { ...MESSAGES, UserNotConfirmedException: "UNCONFIRMED" });
  } catch (error) {
    if (error instanceof Error && error.message === "UNCONFIRMED") return { unconfirmed: true };
    throw error;
  }
  if (r.ChallengeName === "NEW_PASSWORD_REQUIRED") return { challenge: { session: r.Session, username } };
  store(r.AuthenticationResult as AuthResult);
  return {};
}

/** Creates the account. Cognito e-mails a 6-digit code; the account can only log in after confirmSignUp. */
export async function signUp(name: string, email: string, password: string): Promise<{ sentTo: string }> {
  const username = normalizeEmail(email);
  const r = await cognito("SignUp", { ClientId: CONFIG.clientId, Username: username, Password: password,
    UserAttributes: [{ Name: "email", Value: username }, { Name: "name", Value: name.trim() }] },
  MESSAGES, "Não foi possível criar a conta. Tente de novo.");
  return { sentTo: r.CodeDeliveryDetails?.Destination || username };
}

export async function confirmSignUp(email: string, code: string): Promise<void> {
  await cognito("ConfirmSignUp", { ClientId: CONFIG.clientId, Username: normalizeEmail(email),
    ConfirmationCode: code.replace(/\s/g, "") }, MESSAGES, "Não foi possível confirmar. Tente de novo.");
}

export async function resendCode(email: string): Promise<void> {
  await cognito("ResendConfirmationCode", { ClientId: CONFIG.clientId, Username: normalizeEmail(email) },
    MESSAGES, "Não foi possível reenviar o código. Tente de novo.");
}

export async function setNewPassword({ session, username }: Challenge, password: string): Promise<void> {
  const r = await cognito("RespondToAuthChallenge", { ClientId: CONFIG.clientId,
    ChallengeName: "NEW_PASSWORD_REQUIRED", Session: session,
    ChallengeResponses: { USERNAME: username, NEW_PASSWORD: password } });
  store(r.AuthenticationResult as AuthResult);
}

export const isSignedIn = () => Boolean(CONFIG.skipLogin || load()?.idToken);

export function signOut(): void {
  cached = null;
  try { sessionStorage.removeItem(STORAGE_KEY); } catch { /* no storage */ }
}

/** A valid token for the API. Refreshes it automatically when less than 1 minute is left. */
export async function token(): Promise<string | null> {
  if (CONFIG.skipLogin) return "local";          // ignored by the local server
  const t = load();
  if (!t) return null;
  if (Date.now() < t.expiresAt - 60_000) return t.idToken;
  if (!t.refresh) { signOut(); return null; }
  try {
    const r = await cognito("InitiateAuth", { ClientId: CONFIG.clientId, AuthFlow: "REFRESH_TOKEN_AUTH",
      AuthParameters: { REFRESH_TOKEN: t.refresh } });
    store(r.AuthenticationResult as AuthResult, t);
    return load()?.idToken ?? null;
  } catch {
    signOut();
    return null;
  }
}

/** Changes the login's password (Configurações): the current one, then the new one. */
export async function changePassword(current: string, proposed: string): Promise<void> {
  await token();                                 // a fresh session (it refreshes the tokens when needed)
  const access = load()?.accessToken;
  if (!access) throw new Error("Saia e entre de novo para trocar a senha.");
  await cognito("ChangePassword", { AccessToken: access, PreviousPassword: current, ProposedPassword: proposed },
    { ...MESSAGES, NotAuthorizedException: "Senha atual incorreta." }, "Não foi possível trocar a senha. Tente de novo.");
}
