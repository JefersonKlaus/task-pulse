// The system's languages: Portuguese (Brazil), its first language, and English. The texts are written in
// Portuguese in the code, each wrapped in t(); EN below says each one in English ({name} = a value).
// N_() only marks a text to be translated later (with t) where it is defined, like the menu names.
// local/tests/test_frontend_i18n.py checks that every text has its English.
export type Lang = "pt-BR" | "en";
export const LANGUAGES: [Lang, string][] = [["pt-BR", "Português (Brasil)"], ["en", "English"]];
const STORAGE_KEY = "pulse.lang";

export const isLang = (value: unknown): value is Lang => value === "pt-BR" || value === "en";

/** This browser's choice; the first time, the browser's own language (English if it is English). */
function initial(): Lang {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (isLang(saved)) return saved;
  } catch { /* no storage */ }
  return /^en\b/i.test(navigator.language || "") ? "en" : "pt-BR";
}

let current: Lang = initial();
document.documentElement.lang = current;

export const lang = (): Lang => current;
/** For numbers, money and dates (Intl). */
export const locale = (): string => (current === "en" ? "en-US" : "pt-BR");

export function setLang(value: Lang): void {
  current = value;
  document.documentElement.lang = value;
  try { localStorage.setItem(STORAGE_KEY, value); } catch { /* no storage */ }
}

export const N_ = (text: string): string => text;

/** The text in the chosen language, with its {values} filled in. */
export function t(text: string, values: Record<string, string | number> = {}): string {
  const chosen = current === "en" ? EN[text] ?? text : text;
  return chosen.replace(/\{(\w+)\}/g, (all, key: string) => (key in values ? String(values[key]) : all));
}

const EN: Record<string, string> = {
  // the app and its menu
  "Tarefas": "Tasks",
  "Faturamento": "Billing",
  "Pagamentos": "Payments",
  "Projetos": "Projects",
  "Empresas": "Companies",
  "Configurações": "Settings",
  "Sair": "Log out",
  "Modo local, sem login": "Local mode, no login",
  "Sistema ainda não configurado (js/config.js vazio).": "The system is not configured yet (js/config.js is empty).",
  "Carregando…": "Loading…",
  "Algo deu errado. Tente de novo.": "Something went wrong. Try again.",
  "Sessão expirada.": "Session expired.",
  "Sem conexão com o servidor.": "No connection to the server.",
  "Salvar": "Save",
  "Cancelar": "Cancel",
  "Confirmar": "Confirm",
  "Excluir": "Delete",
  "Editar": "Edit",
  "Ações": "Actions",
  "Ações: {name}": "Actions: {name}",
  "Mostrar senha": "Show password",
  "Ocultar senha": "Hide password",
  // filters
  "Empresa": "Company",
  "Projeto": "Project",
  "Período:": "Period:",
  "Todas as empresas": "All companies",
  "Todos os projetos": "All projects",
  "Mês": "Month",
  "Semana": "Week",
  "Hoje": "Today",
  "Período anterior": "Previous period",
  "Próximo período": "Next period",
  "{from} a {to}": "{from} to {to}",
  // task statuses
  "Fazendo": "Doing",
  "Concluída": "Done",
  "Aprovada": "Approved",
  "Rejeitada": "Rejected",
  // tasks
  "Em aberto": "Open",
  "Concluídas": "Done",
  "Todas": "All",
  "Nova tarefa": "New task",
  "Nenhum projeto ainda": "No projects yet",
  "Cadastre a empresa em Empresas e o projeto (com o valor hora ou fixo) em Projetos.":
    "Add the company in Companies and the project (with its hourly or fixed rate) in Projects.",
  "Nenhuma tarefa": "No tasks",
  "Nada em aberto neste período.": "Nothing open in this period.",
  "Nada neste período.": "Nothing in this period.",
  "{count} tarefa(s) · {hours}": "{count} task(s) · {hours}",
  "Tempo: {name}": "Time: {name}",
  "+ Tempo": "+ Time",
  "Tempo inválido: use 1:30, 1,5 ou 45m.": "Invalid time: use 1:30, 1.5 or 45m.",
  "1:30, 1,5 (horas) ou 45m": "1:30, 1.5 (hours) or 45m",
  "{time} adicionado(s).": "{time} added.",
  "Paga": "Paid",
  "Não paga": "Not paid",
  "Início {date}": "Started {date}",
  "Término {date}": "Finished {date}",
  "Concluir": "Finish",
  "Aprovar": "Approve",
  "Rejeitar": "Reject",
  "Reabrir": "Reopen",
  "Excluir a tarefa \"{name}\"?": "Delete the task \"{name}\"?",
  "Tarefa excluída.": "Task deleted.",
  "Tarefa: {status}.": "Task: {status}.",
  "Concluir: {name}": "Finish: {name}",
  "Tempo até agora: {time}": "Time so far: {time}",
  "Tempo a adicionar (opcional)": "Time to add (optional)",
  "Término": "Finish",
  "Tarefa concluída.": "Task finished.",
  "Tempo total": "Total time",
  "Tempo trabalhado": "Time worked",
  "Editar tarefa": "Edit task",
  "Nome": "Name",
  "ID externo (opcional)": "External ID (optional)",
  "Repositório": "Repository",
  "Descrição": "Description",
  "Tarefa já faturada: tempo, status e datas não mudam mais.":
    "Task already billed: its time, status and dates can't change any more.",
  "Status": "Status",
  "Início": "Start",
  "Tarefa salva.": "Task saved.",
  "Tarefa criada.": "Task created.",
  // billing
  "Cadastre um projeto em Projetos.": "Add a project in Projects.",
  "Nenhum projeto nesta empresa.": "No projects in this company.",
  "{count} tarefa(s)": "{count} task(s)",
  "Deveria receber": "Should receive",
  "Recebido": "Received",
  "diferença {amount}": "difference {amount}",
  "Pagas": "Paid",
  "Não pagas": "Not paid",
  "Bônus do período": "Period bonus",
  "{count} aprovada(s)": "{count} approved",
  "{amount} já pago": "{amount} already paid",
  "Será paga: {name}": "Will be paid: {name}",
  "Pagar": "Pay",
  "Tarefa": "Task",
  "Tempo": "Time",
  "Valor": "Amount",
  "Situação": "Situation",
  "Bônus por tarefas aprovadas": "Bonus for approved tasks",
  "Nenhuma tarefa concluída neste período": "No tasks finished in this period",
  "Registrar pagamento": "Register payment",
  "Desmarque na lista as tarefas que NÃO serão pagas. A receber:":
    "Untick the tasks that will NOT be paid. To receive:",
  "(com {amount} de bônus)": "(with {amount} of bonus)",
  "Valor recebido ({currency})": "Amount received ({currency})",
  "Recebido em": "Received on",
  "Observações": "Notes",
  "Valor recebido inválido (ex.: 1.234,56).": "Invalid amount received (e.g. 1,234.56).",
  "Pagamento registrado.": "Payment registered.",
  "Pagamentos deste período": "Payments of this period",
  "Recebido em {date}": "Received on {date}",
  "deveria: {amount}": "should: {amount}",
  "diferença: {amount}": "difference: {amount}",
  "{count} não paga(s): {amount}": "{count} not paid: {amount}",
  "Pagamento": "Payment",
  "Excluir pagamento": "Delete payment",
  "Excluir este pagamento? As tarefas dele voltam a ficar em aberto.":
    "Delete this payment? Its tasks become open again.",
  "Pagamento excluído.": "Payment deleted.",
  // payments
  "Nenhum pagamento": "No payments",
  "Registre um em Faturamento.": "Register one in Billing.",
  "Diferença": "Difference",
  "não pagas: {amount}": "not paid: {amount}",
  "Moedas diferentes: escolha uma empresa ou projeto para ver os totais.":
    "Different currencies: choose a company or project to see the totals.",
  "Período": "Period",
  "Deveria": "Should",
  "{count} paga(s)": "{count} paid",
  // companies, projects and rules
  "{count} projeto(s)": "{count} project(s)",
  "Novo projeto": "New project",
  "Excluir a empresa \"{name}\"?": "Delete the company \"{name}\"?",
  "Empresa excluída.": "Company deleted.",
  "sem regra de valor em vigor": "no pricing rule in force",
  "{count} em aberto": "{count} open",
  "Deadline {date}": "Deadline {date}",
  "Nova empresa": "New company",
  "Nenhuma empresa ainda": "No companies yet",
  "Editar empresa": "Edit company",
  "Excluir empresa": "Delete company",
  "{count} tarefa(s) em aberto": "{count} open task(s)",
  "Cadastre a empresa para a qual você presta serviço. Depois, os projetos dela.":
    "Add the company you work for. Then, its projects.",
  "Nenhum projeto nesta empresa ainda. Uma empresa pode ter vários projetos, cada um com o seu valor.":
    "No projects in this company yet. A company can have many projects, each with its own rate.",
  "Todo projeto é de uma empresa. Cadastre a empresa primeiro.": "Every project belongs to a company. Add the company first.",
  "Uma empresa pode ter vários projetos, cada um com o seu valor.": "A company can have many projects, each with its own rate.",
  "Empresa salva.": "Company saved.",
  "Empresas conhecidas": "Well-known companies",
  "Toque para adicionar. As que não estão aqui, cadastre em Nova empresa.":
    "Tap to add. For the ones not listed here, use New company.",
  "{name} adicionada.": "{name} added.",
  "Plataforma da Labelbox.": "Run by Labelbox.",
  "Plataforma da Toloka.": "Run by Toloka.",
  "Plataforma da Scale AI.": "Run by Scale AI.",
  "Editar projeto": "Edit project",
  "Excluir projeto": "Delete project",
  "Excluir o projeto \"{name}\" com todas as tarefas e pagamentos?":
    "Delete the project \"{name}\" with all its tasks and payments?",
  "Projeto excluído.": "Project deleted.",
  "Moeda": "Currency",
  "Deadline": "Deadline",
  "Regras de valor": "Pricing rules",
  "Nova regra": "New rule",
  "Cada tarefa vale pela regra em vigor quando foi concluída. Para mudar um valor, crie uma regra nova a partir de agora: a anterior termina quando a nova começa.":
    "Each task is worth what the rule in force when it was finished says. To change a value, create a new rule from now on: the previous one ends when the new one starts.",
  "em vigor": "in force",
  "De {start} até {end}": "From {start} to {end}",
  "De {start} em diante": "From {start} on",
  "Só tarefas aprovadas são pagas": "Only approved tasks are paid",
  "Tarefas concluídas e aprovadas são pagas (rejeitadas não)": "Done and approved tasks are paid (rejected ones aren't)",
  "Bônus:": "Bonus:",
  "{count}+ aprovadas = {amount}": "{count}+ approved = {amount}",
  "Regra": "Rule",
  "Excluir esta regra?": "Delete this rule?",
  "Regra excluída.": "Rule deleted.",
  "Sem regra: as tarefas deste projeto valem 0 até você criar uma.":
    "No rule: this project's tasks are worth 0 until you create one.",
  "{amount} por tarefa": "{amount} per task",
  "última hora {amount}/h se aprovada": "last hour {amount}/h if approved",
  "Deadline (quando acaba)": "Deadline (when it ends)",
  "Projeto salvo.": "Project saved.",
  "Editar regra": "Edit rule",
  "Regra salva.": "Rule saved.",
  "opcional": "optional",
  "Valor hora": "Hourly rate",
  "Valor flat (última hora, se aprovada)": "Flat rate (last hour, if approved)",
  "Valor fixo por tarefa": "Fixed amount per task",
  "nº de tarefas": "no. of tasks",
  "Tarefas aprovadas": "Approved tasks",
  "bônus": "bonus",
  "Valor do bônus": "Bonus amount",
  "Remover faixa": "Remove tier",
  "Tipo de valor": "Pricing type",
  "Valor fixo": "Fixed amount",
  "Vale a partir de": "Valid from",
  "Até (opcional)": "Until (optional)",
  "Vazio: até começar outra regra": "Empty: until another rule starts",
  "Só paga tarefa aprovada": "Only pay approved tasks",
  "Bônus por tarefas aprovadas no período": "Bonus for tasks approved in the period",
  "+ Faixa de bônus": "+ Bonus tier",
  "{label}: valor inválido (ex.: {example})": "{label}: invalid amount (e.g. {example})",
  "Bônus": "Bonus",
  "Valor flat": "Flat rate",
  // login
  "10+ caracteres, com maiúscula, minúscula e número": "10+ characters, with upper case, lower case and a number",
  "Cada hora trabalhada, cada tarefa aprovada e quanto ela vale.": "Every hour worked, every task approved and what it is worth.",
  "voce@exemplo.com": "you@example.com",
  "Entrar": "Log in",
  "E-mail": "E-mail",
  "Senha": "Password",
  "Ainda não tem conta?": "No account yet?",
  "Criar conta": "Sign up",
  "Repita a senha": "Repeat the password",
  "Já tem conta?": "Already have an account?",
  "Digite o seu nome.": "Type your name.",
  "Enviamos um código para {email}.": "We sent a code to {email}.",
  "Reenviar código": "Send the code again",
  "Código reenviado.": "Code sent again.",
  "Confirme o seu e-mail": "Confirm your e-mail",
  "Digite o código de 6 dígitos que enviamos para": "Type the 6-digit code we sent to",
  "Confira também a caixa de spam.": "Check the spam folder too.",
  "Código": "Code",
  "Não chegou?": "Didn't get it?",
  "Voltar": "Back",
  "E-mail confirmado.": "E-mail confirmed.",
  "Definir senha": "Set password",
  "Primeiro acesso": "First access",
  "Escolha a sua senha ({rule}).": "Choose your password ({rule}).",
  "Nova senha": "New password",
  "A senha precisa ter {rule}.": "The password needs {rule}.",
  "As senhas não são iguais.": "The passwords don't match.",
  // Cognito's answers
  "E-mail ou senha incorretos.": "Wrong e-mail or password.",
  "Já existe uma conta com este e-mail. Entre com ela.": "There is already an account with this e-mail. Log in with it.",
  "E-mail inválido.": "Invalid e-mail.",
  "Código incorreto. Confira o e-mail e tente de novo.": "Wrong code. Check the e-mail and try again.",
  "Código expirado: peça um novo.": "Expired code: ask for a new one.",
  "Não foi possível enviar o e-mail. Confira o endereço.": "Couldn't send the e-mail. Check the address.",
  "A senha precisa ter 10 caracteres, com maiúscula, minúscula e número.":
    "The password needs 10 characters, with upper case, lower case and a number.",
  "Muitas tentativas. Espere um pouco.": "Too many attempts. Wait a little.",
  "Não foi possível entrar. Tente de novo.": "Couldn't log in. Try again.",
  "Não foi possível criar a conta. Tente de novo.": "Couldn't create the account. Try again.",
  "Não foi possível confirmar. Tente de novo.": "Couldn't confirm. Try again.",
  "Não foi possível reenviar o código. Tente de novo.": "Couldn't send the code again. Try again.",
  "Saia e entre de novo para continuar.": "Log out and in again to continue.",
  "Senha atual incorreta.": "Wrong current password.",
  "Não foi possível trocar a senha. Tente de novo.": "Couldn't change the password. Try again.",
  "Não foi possível ler a sua conta.": "Couldn't read your account.",
  "Não foi possível salvar. Tente de novo.": "Couldn't save. Try again.",
  // settings
  "Idioma": "Language",
  "O idioma de todas as telas, dos valores e das datas.": "The language of every screen, amount and date.",
  "Idioma alterado.": "Language changed.",
  "Conta": "Account",
  "Modo local, sem login: nome e senha só existem no sistema publicado.":
    "Local mode, no login: name and password only exist in the deployed system.",
  "Salvar nome": "Save name",
  "O e-mail é o seu login e não muda.": "The e-mail is your login and doesn't change.",
  "Nome salvo.": "Name saved.",
  "Alterar senha": "Change password",
  "Senha atual": "Current password",
  "Repita a nova senha": "Repeat the new password",
  "Senha alterada.": "Password changed.",
};
