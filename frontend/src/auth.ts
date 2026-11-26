// Cognito login straight through its public API (no library). Tokens live only in the tab's session.
// CONFIG.skipLogin is only ever set by local/server.py: there is no login and the local server
// answers every request as the same user. The deployed API still requires a valid token for everything.
import { CONFIG } from "./config.js";

const STORAGE_KEY = "pulse.tokens";
const MESSAGES: Record<string, string> = {
  NotAuthorizedException: "Celular ou senha incorretos.",
  UserNotFoundException: "Celular ou senha incorretos.",
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

/** "11987654321" (DDD + number, digits only) -> "+5511987654321", the login's Cognito username. */
export function phoneToUsername(digits: string): string {
  if (!/^[1-9]{2}\d{8,9}$/.test(digits)) throw new Error("Celular inválido: digite DDD + número, só os dígitos.");
  return `+55${digits}`;
}

/** Returns {challenge} if Cognito asks for a new password (first access), otherwise stores the tokens. */
export async function signIn(phone: string, password: string): Promise<{ challenge?: Challenge }> {
  const username = phoneToUsername(phone);
  const r = await cognito("InitiateAuth", { ClientId: CONFIG.clientId,
    AuthFlow: "USER_PASSWORD_AUTH", AuthParameters: { USERNAME: username, PASSWORD: password } });
  if (r.ChallengeName === "NEW_PASSWORD_REQUIRED") return { challenge: { session: r.Session, username } };
  store(r.AuthenticationResult as AuthResult);
  return {};
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
