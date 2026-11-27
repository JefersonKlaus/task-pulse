"""Opens the built frontend in a real Chromium, talking to the real API (in-memory database).
Run:  python dev.py e2e   (builds the frontend, then runs this file)

Two passes: `run()` creates an account (sign-up, the e-mailed code), logs out and in by e-mail with a
simulated Cognito (like the deployed app) and then registers a company, a project with its rule, tasks, time, approval and a payment; `run_without_login()`
checks the local server's default mode, which has no login and opens with the demo data, on a phone.

The texts used in the selectors ("Entrar", "Salvar", ...) are the app's labels, which are in Portuguese."""
import json
import re
import threading
from datetime import date

from playwright.sync_api import expect, sync_playwright

import server as local_server


def url_of(server):
    """Each test's server listens on a free port the system picked (start(0))."""
    return f"http://127.0.0.1:{server.server_address[1]}/"


class FakeCognito:
    """Plays Cognito for the browser: sign-up sends the code "123456" (no e-mail), the account logs in only
    after it is confirmed. The token is "token-<e-mail>": the local server takes the login from it."""
    CODE = "123456"

    def __init__(self):
        self.users = {}                                   # e-mail -> {"password", "confirmed"}

    def reply(self, route, status, body):
        route.fulfill(status=status, content_type="application/x-amz-json-1.1", body=json.dumps(body))

    def error(self, route, kind):
        self.reply(route, 400, {"__type": kind})

    def __call__(self, route):
        target = route.request.headers["x-amz-target"].split(".")[-1]
        body = json.loads(route.request.post_data)
        if target == "SignUp":
            email = body["Username"]
            assert email == email.strip().lower(), email          # the site sends it normalized
            if email in self.users:
                return self.error(route, "UsernameExistsException")
            attributes = {a["Name"]: a["Value"] for a in body.get("UserAttributes", [])}
            self.users[email] = {"password": body["Password"], "confirmed": False, "attributes": attributes}
            return self.reply(route, 200, {"UserConfirmed": False,
                                           "CodeDeliveryDetails": {"Destination": email[0] + "***@" + email.split("@")[1]}})
        if target == "ResendConfirmationCode":
            return self.reply(route, 200, {})
        if target == "ConfirmSignUp":
            if body["ConfirmationCode"] != self.CODE:
                return self.error(route, "CodeMismatchException")
            self.users[body["Username"]]["confirmed"] = True
            return self.reply(route, 200, {})
        if target in ("GetUser", "UpdateUserAttributes", "ChangePassword"):
            user = self.users[body["AccessToken"][len("access-"):]]
            if target == "GetUser":
                return self.reply(route, 200, {"UserAttributes": [{"Name": k, "Value": v}
                                                                   for k, v in user["attributes"].items()]})
            if target == "UpdateUserAttributes":
                user["attributes"].update({a["Name"]: a["Value"] for a in body["UserAttributes"]})
                return self.reply(route, 200, {})
            if body["PreviousPassword"] != user["password"]:
                return self.error(route, "NotAuthorizedException")
            user["password"] = body["ProposedPassword"]
            return self.reply(route, 200, {})
        assert target == "InitiateAuth", target
        email, password = body["AuthParameters"]["USERNAME"], body["AuthParameters"]["PASSWORD"]
        user = self.users.get(email)
        if not user or user["password"] != password:
            return self.error(route, "NotAuthorizedException")
        if not user["confirmed"]:
            return self.error(route, "UserNotConfirmedException")
        self.reply(route, 200, {"AuthenticationResult": {"IdToken": f"token-{email}", "AccessToken": f"access-{email}",
                                                         "ExpiresIn": 3600, "RefreshToken": "r"}})


def watch(page, errors):
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda m: m.type == "error" and errors.append(m.text))


def run():
    server = local_server.start(0, require_login=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    errors = []
    month = date.today().strftime("%Y-%m")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(locale="pt-BR")             # the system's first language
        cognito = FakeCognito()
        watch(page, errors)
        page.route("https://cognito-idp.sa-east-1.amazonaws.com/", cognito)
        page.goto(url_of(server))

        # sign up: a weak password, then a good one; the e-mailed code, first wrong, then right
        expect(page.locator("h2")).to_have_text("Entrar")
        page.click("text=Criar conta")
        page.fill("#s-name", "Ana Lima")
        page.fill("#s-email", " Ana@Exemplo.com ")
        page.fill("#s-password", "fraca")
        page.fill("#s-repeat", "fraca")
        page.click("button:text('Criar conta')")
        expect(page.locator(".toast.error").last).to_contain_text("A senha precisa ter")
        page.fill("#s-password", "Strong-Password-1")
        page.fill("#s-repeat", "Strong-Password-1")
        page.click("button:text('Criar conta')")
        expect(page.locator("h2")).to_have_text("Confirme o seu e-mail")
        expect(page.locator("form")).to_contain_text("ana@exemplo.com")
        page.fill("#c-code", "000000")
        page.click("button:text('Confirmar')")
        expect(page.locator(".toast.error").last).to_contain_text("Código incorreto")
        page.fill("#c-code", FakeCognito.CODE)
        page.click("button:text('Confirmar')")
        expect(page.locator(".empty-state")).to_contain_text("Nenhum projeto ainda")

        # log out, then in by e-mail and password: a wrong password first
        page.click("#side-account .logout")
        page.fill("#l-email", "ana@exemplo.com")
        page.fill("#l-password", "wrong")
        page.click("button:text('Entrar')")
        expect(page.locator(".toast.error").last).to_contain_text("incorretos")
        page.fill("#l-password", "Strong-Password-1")
        page.click("button:text('Entrar')")
        expect(page.locator(".empty-state")).to_contain_text("Nenhum projeto ainda")
        errors.clear()                  # the browser logged Cognito's 400s (weak code, wrong password), on purpose

        # a company (its own page, under Empresas) and two projects of it. Portal: R$ 100/h, last hour
        # R$ 150/h if approved, only approved are paid; Aplicativo: R$ 350 per task
        page.click("nav >> text=Projetos")
        expect(page.locator(".empty-state")).to_contain_text("Cadastre a empresa primeiro")
        page.click("nav >> text=Empresas")
        page.click("#new-company")
        page.fill("#c-name", "Etho")
        page.click("dialog >> text=Salvar")
        expect(page.locator("h1")).to_have_text("Etho")                  # the company's page
        page.click("#new-project")
        page.fill("#p-name", "Aplicativo")
        page.click("dialog label.choice:has-text('Valor fixo')")
        expect(page.locator("#r-hourly")).to_be_hidden()                  # fixed value: no hourly fields
        expect(page.locator("#r-flat")).to_be_hidden()
        page.fill("#r-fixed", "350")
        page.click("dialog >> text=Salvar")
        expect(page.locator("#company-projects [data-project]")).to_have_count(1)
        page.click("#new-project")
        page.fill("#p-name", "Portal")
        page.fill("#r-starts", f"{month}-01T00:00")
        page.fill("#r-hourly", "abc")
        page.click("dialog >> text=Salvar")
        expect(page.locator(".toast.error").last).to_contain_text("Valor hora")
        page.fill("#r-hourly", "100,00")
        page.fill("#r-flat", "150")
        page.check("#r-approved")
        page.click("dialog >> text=+ Faixa de bônus")
        page.fill(".tier-row input[type=number]", "2")
        page.fill(".tier-row input[aria-label='Valor do bônus']", "50")
        page.click("dialog >> text=Salvar")
        expect(page.locator("#company-projects [data-project]")).to_have_count(2)   # one company, many projects
        page.click("nav >> text=Empresas")
        expect(page.locator("[data-company='Etho']")).to_contain_text("2 projeto(s)")
        # the well-known companies: one tap adds one (with who runs it), and it leaves the list
        page.click("#known-companies [data-known='Outlier']")
        expect(page.locator("[data-company='Outlier']")).to_contain_text("Plataforma da Scale AI.")
        expect(page.locator("#known-companies [data-known='Outlier']")).to_have_count(0)
        expect(page.locator("#known-companies [data-known='Alignerr']")).to_be_visible()
        page.click("#new-company")                                         # Nova empresa suggests them too
        page.fill("#c-name", "mindrift")
        expect(page.locator("#c-notes")).to_have_value("Plataforma da Toloka.")
        page.click("dialog >> text=Cancelar")
        page.click("nav >> text=Projetos")
        expect(page.locator("#project-list [data-project]")).to_have_count(2)
        page.click("[data-project='Portal']")
        expect(page.locator("h1")).to_have_text("Portal")
        expect(page.locator("#rules .rule.current")).to_contain_text("R$ 100,00/h")
        expect(page.locator("#rules .rule.current")).to_contain_text("2+ aprovadas = R$ 50,00")

        # tasks: one created already concluded, one open that takes time and is concluded on the list
        page.click("nav >> text=Tarefas")
        page.click("#new-task")
        page.fill("#t-name", "Tela de login")
        page.fill("#t-external", "ETH-1")
        page.fill("#t-repository", "etho/portal")
        page.fill("#t-started", f"{month}-01T09:00")
        page.select_option("#t-status", "APPROVED")
        page.fill("#t-minutes", "2:00")
        page.fill("#t-finished", f"{month}-01T18:00")
        page.click("dialog >> text=Salvar")
        page.click("#new-task")
        page.fill("#t-name", "Página de faturas")
        page.fill("#t-started", f"{month}-01T09:00")
        page.click("dialog >> text=Salvar")
        task = page.locator("[data-task='Página de faturas']")
        expect(task).to_contain_text("Fazendo")
        task.locator(".quick-time input").fill("0:30")
        task.locator("text=+ Tempo").click()
        expect(page.locator("[data-task='Página de faturas']")).to_contain_text("0:30")
        page.locator("[data-task='Página de faturas'] >> text=Concluir").click()
        page.fill("#finish-time", "0:15")
        page.fill("#finish-at", f"{month}-01T17:00")
        page.click("dialog >> button:text('Concluir')")
        expect(page.locator("[data-task]")).to_have_count(0)                    # nothing open anymore
        page.click("[role=tab]:text('Concluídas')")
        expect(page.locator("[data-task]")).to_have_count(2)
        page.locator("[data-task='Página de faturas'] .kebab").click()
        page.click("[role=menuitem]:text('Aprovar')")
        expect(page.locator("[data-task='Página de faturas']")).to_contain_text("Aprovada")

        # billing: 1h x 100 + 1h x 150 = 250; 0:45 all at the flat = 112,50; bonus 50 -> 412,50
        page.click("nav >> text=Faturamento")
        expect(page.locator("#billing-totals")).to_contain_text("R$ 412,50")
        page.locator("[data-task='Página de faturas'] input[type=checkbox]").uncheck()   # the company won't pay it
        expect(page.locator("#to-receive")).to_have_text(re.compile(r"R\$\s300,00"))
        page.fill("#pay-received", "280,00")
        page.click("text=Registrar pagamento >> nth=-1")
        expect(page.locator("#billing-totals")).to_contain_text("diferença -R$ 20,00")
        expect(page.locator("[data-task='Página de faturas']")).to_contain_text("Não paga")
        expect(page.locator("#pay-form")).to_have_count(0)

        page.click("nav >> text=Pagamentos")
        expect(page.locator("#payments-table tbody tr")).to_have_count(1)
        expect(page.locator("#payments-totals")).to_contain_text("não pagas: R$ 112,50")

        # Configurações: apart from the menu. Name, password, then the language (saved in the login too)
        page.click("#side-account .settings-link")
        expect(page.locator("h1")).to_have_text("Configurações")
        expect(page.locator("nav [aria-current=page]")).to_have_count(0)
        expect(page.locator("#set-email")).to_have_value("ana@exemplo.com")
        expect(page.locator("#set-name")).to_have_value("Ana Lima")
        page.fill("#set-name", "Ana Souza")
        page.click("text=Salvar nome")
        expect(page.locator(".toast").last).to_contain_text("Nome salvo")
        page.fill("#set-current", "wrong-Password-1")
        page.fill("#set-new", "Newer-Password-2")
        page.fill("#set-repeat", "Newer-Password-2")
        page.click("button:text('Alterar senha')")
        expect(page.locator(".toast.error").last).to_contain_text("Senha atual incorreta")
        page.fill("#set-current", "Strong-Password-1")
        page.click("button:text('Alterar senha')")
        expect(page.locator(".toast").last).to_contain_text("Senha alterada")
        page.click("#settings-language >> text=English")
        expect(page.locator("h1")).to_have_text("Settings")
        expect(page.locator("nav")).to_contain_text("Tasks")
        user = cognito.users["ana@exemplo.com"]
        assert user["attributes"]["name"] == "Ana Souza" and user["attributes"]["locale"] == "en", user
        assert user["password"] == "Newer-Password-2"

        # in English: money, dates and the API's own messages too
        page.click("nav >> text=Payments")
        expect(page.locator("#payments-totals")).to_contain_text("not paid: R$112.50")
        page.click("nav >> text=Companies")
        page.click("#new-company")
        page.fill("#c-name", "etho")
        page.click("dialog >> text=Save")
        expect(page.locator(".toast.error").last).to_have_text("A company with this name already exists")
        errors.clear()                  # the browser logged the API's 400 and Cognito's, on purpose
        browser.close()
    server.shutdown()
    assert not errors, errors
    print("e2e with login: ok")


def run_without_login():
    server = local_server.start(0, demo_data=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 800}, locale="pt-BR")   # a phone
        watch(page, errors)
        page.goto(url_of(server))
        expect(page.locator("h1")).to_have_text("Tarefas")
        expect(page.locator("[data-task]")).to_have_count(3)                          # the open demo tasks
        width = page.evaluate("document.documentElement.scrollWidth")
        assert width <= 390, f"the page scrolls sideways on a phone ({width}px)"
        expect(page.locator("#top-bar .local-mode")).to_be_visible()                 # no login here
        expect(page.locator("nav")).to_be_visible()                                   # the bottom bar
        page.click("nav >> text=Empresas")
        expect(page.locator("[data-company]")).to_have_count(2)
        expect(page.locator("#known-companies [data-known='Alignerr']")).to_have_count(0)   # registered already
        expect(page.locator("#known-companies [data-known='Outlier']")).to_be_visible()
        page.click("nav >> text=Projetos")
        expect(page.locator("#project-list [data-project]")).to_have_count(3)
        page.click("#top-bar .settings-link")                                      # Configurações, on a phone
        expect(page.locator("#settings-local")).to_be_visible()                      # no name or password here
        page.click("#settings-language >> text=English")
        expect(page.locator("nav")).to_contain_text("Projects")
        page.reload()                                                                 # the choice is kept
        expect(page.locator("h1")).to_have_text("Tasks")
        width = page.evaluate("document.documentElement.scrollWidth")
        assert width <= 390, f"the page scrolls sideways on a phone ({width}px)"
        browser.close()
    server.shutdown()
    assert not errors, errors
    print("e2e without login: ok")


if __name__ == "__main__":
    run()
    run_without_login()
