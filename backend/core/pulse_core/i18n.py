"""The API's error messages in the user's language. The domain raises them in Portuguese (the system's
first language); the HTTP adapter translates the message to English when the request asks for it
(Accept-Language: en). A message without a translation goes out as it is.

A field's message is "<label>: <problem>", so labels and problems are translated apart."""
from __future__ import annotations

import re

SUPPORTED = ("pt-BR", "en")

LABELS = {
    "Nome": "Name", "Observações": "Notes", "Início da regra": "Rule start", "Fim da regra": "Rule end",
    "Valor hora": "Hourly rate", "Valor flat": "Flat rate", "Valor fixo": "Fixed amount", "Bônus": "Bonus",
    "Deadline": "Deadline", "Descrição": "Description", "Início": "Start", "Término": "Finish",
    "ID externo": "External ID", "Repositório": "Repository", "Tempo": "Time", "Tarefas não pagas": "Unpaid tasks",
    "Início do período": "Period start", "Fim do período": "Period end",
    "Data do recebimento": "Date received", "Valor recebido": "Amount received", "Empresa": "Company",
    "Tipo de valor": "Pricing type", "Tarefa concluída": "Finished task", "Tarefa já faturada": "Task already billed",
    "finish": "finish", "paid_only_if_approved": "paid_only_if_approved",
}

MESSAGES = {
    # whole messages
    "não encontrado": "not found",
    "não autenticado": "not signed in",
    "erro interno, tente de novo": "internal error, try again",
    "corpo grande demais": "request body too large",
    "corpo não é um JSON válido": "request body is not valid JSON",
    "o corpo deve ser um objeto JSON": "request body must be a JSON object",
    "empresa não encontrada": "company not found",
    "projeto não encontrado": "project not found",
    "tarefa não encontrada": "task not found",
    "pagamento não encontrado": "payment not found",
    "regra não encontrada": "rule not found",
    "Já existe uma empresa com este nome": "A company with this name already exists",
    "Já existe uma tarefa com este ID externo neste projeto": "A task with this external ID already exists in this project",
    "O fim do período deve ser depois do início": "The period's end must be after its start",
    "Nenhuma tarefa em aberto neste período": "No open tasks in this period",
    "Fim da regra deve ser depois do início": "The rule's end must be after its start",
    "Moeda inválida": "Invalid currency",
    "Status inválido": "Invalid status",
    "Término não pode ser antes do início": "The finish can't be before the start",
    "Para concluir, informe o tempo trabalhado": "To finish it, enter the time worked",
    "Já existe uma regra nesse intervalo: as regras não podem se sobrepor":
        "There is already a rule in this interval: rules can't overlap",
    "A empresa tem projetos: exclua ou mova os projetos antes": "The company has projects: delete or move them first",
    "Há tarefas concluídas nesta regra: ela não pode ser excluída":
        "There are finished tasks under this rule: it can't be deleted",
    "Tarefa já faturada: exclua o pagamento antes": "Task already billed: delete the payment first",
    "state: open, finished ou all": "state: open, finished or all",
    "Já há tarefas concluídas nesta regra: para mudar os valores, crie uma nova regra a partir de agora "
    "(esta é encerrada quando a nova começa)":
        "There are finished tasks under this rule: to change its values, create a new rule from now on "
        "(this one ends when the new one starts)",
    # the part after "<label>: "
    "texto inválido": "invalid text",
    "obrigatório": "required",
    "obrigatória": "required",
    "valor inválido (centavos, inteiro)": "invalid amount (cents, whole number)",
    "deve ser maior que zero": "must be greater than zero",
    "minutos inválidos": "invalid minutes",
    "data inválida (AAAA-MM-DD)": "invalid date (YYYY-MM-DD)",
    "data e hora inválidas (AAAA-MM-DDTHH:MM)": "invalid date and time (YYYY-MM-DDTHH:MM)",
    "deve ser true ou false": "must be true or false",
    "escolha valor hora ou valor fixo": "choose hourly or fixed",
    "lista inválida": "invalid list",
    "item inválido": "invalid item",
    "número de tarefas inválido": "invalid number of tasks",
    "cada faixa precisa de um número de tarefas diferente": "each tier needs a different number of tasks",
    "alguma não está em aberto neste período": "one of them is not open in this period",
    "informe quando terminou": "enter when it finished",
    "informe o tempo trabalhado": "enter the time worked",
    "só nome, ID, repositório e descrição podem mudar": "only its name, ID, repository and description can change",
    "o tempo não muda mais": "its time can't change any more",
    "informe quantos minutos trabalhou": "enter how many minutes you worked",
    "total grande demais": "total too large",
}

PATTERNS = [            # messages with a number or a date inside
    (re.compile(r"^no máximo (\d+) caracteres$"), "at most {0} characters"),
    (re.compile(r"^Período de no máximo (\d+) dias$"), "A period of at most {0} days"),
    (re.compile(r"^Limite de (\d+) empresas$"), "Limit of {0} companies"),
    (re.compile(r"^Limite de (\d+) projetos$"), "Limit of {0} projects"),
    (re.compile(r"^Limite de (\d+) regras por projeto$"), "Limit of {0} rules per project"),
    (re.compile(r"^Limite de (\d+) tarefas por projeto$"), "Limit of {0} tasks per project"),
    (re.compile(r"^Já há tarefa concluída nesta regra em (\S+): o fim deve ser depois disso$"),
     "There is a task finished under this rule at {0}: the end must be after that"),
]


def language(accept_language: str | None) -> str:
    """"pt-BR", "pt-BR,pt;q=0.9" -> "pt-BR"; anything else (or nothing) -> "en", the default."""
    first = (accept_language or "").split(",")[0].strip().lower()
    return "pt-BR" if first.startswith("pt") else "en"


def _part(text: str) -> str:
    if text in MESSAGES:
        return MESSAGES[text]
    for pattern, english in PATTERNS:
        match = pattern.match(text)
        if match:
            return english.format(*match.groups())
    return text


def translate(message: str, lang: str) -> str:
    if lang != "en":
        return message
    whole = _part(message)
    if whole != message or ": " not in message:
        return whole
    label, problem = message.split(": ", 1)
    return f"{LABELS.get(label, label)}: {_part(problem)}"
