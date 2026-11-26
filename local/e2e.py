"""Opens the built frontend in a real Chromium, talking to the real API (in-memory database).
Run:  python dev.py e2e   (builds the frontend, then runs this file)

Two passes: `run()` goes through the login screen with a simulated Cognito (like the deployed app) and
then registers a company, a project with its rule, tasks, time, approval and a payment; `run_without_login()`
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


def cognito(route):
    """First access requires a new password, like a user created by the administrator. The token is
    "token-u<DDD + number>": the local server takes the login from it (local/server.py)."""
    target = route.request.headers["x-amz-target"].split(".")[-1]
    body = json.loads(route.request.post_data)
    username = (body.get("AuthParameters") or body.get("ChallengeResponses") or {}).get("USERNAME")
    if username is not None:
        assert re.fullmatch(r"\+55\d{10,11}", username), username
    if target == "InitiateAuth" and body["AuthParameters"].get("PASSWORD") == "wrong":
        return route.fulfill(status=400, content_type="application/x-amz-json-1.1",
                             body=json.dumps({"__type": "NotAuthorizedException"}))
    if target == "InitiateAuth":
        response = {"ChallengeName": "NEW_PASSWORD_REQUIRED", "Session": "session-1"}
    else:
        response = {"AuthenticationResult": {"IdToken": f"token-u{username[3:]}", "AccessToken": "access",
                                             "ExpiresIn": 3600, "RefreshToken": "r"}}
    route.fulfill(status=200, content_type="application/x-amz-json-1.1", body=json.dumps(response))


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
        page = browser.new_page()
        watch(page, errors)
        page.route("https://cognito-idp.sa-east-1.amazonaws.com/", cognito)
        page.goto(url_of(server))

        # login: wrong password, then first access with a new password
        page.fill("#l-phone", "11987654321")
        page.fill("#l-password", "wrong")
        page.click("text=Entrar")
        expect(page.locator(".toast.error").last).to_contain_text("incorretos")
        page.fill("#l-password", "Strong-Password-1")
        page.click("text=Entrar")
        expect(page.locator("text=Primeiro acesso")).to_be_visible()
        page.fill("#l-password", "Another-Password-9")
        page.click("text=Definir senha")
        expect(page.locator(".empty-state")).to_contain_text("Nenhum projeto ainda")
        errors.clear()                  # the browser logged Cognito's 400 for the wrong password, on purpose

        # a company and its project: R$ 100/h, last hour R$ 150/h if approved, only approved are paid
        page.click("nav >> text=Projetos")
        page.click("#new-company")
        page.fill("#c-name", "Etho")
        page.click("dialog >> text=Salvar")
        expect(page.locator("[data-company='Etho']")).to_be_visible()
        page.click("[data-company='Etho'] >> text=Novo projeto")
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
        page = browser.new_page(viewport={"width": 390, "height": 800})               # a phone
        watch(page, errors)
        page.goto(url_of(server))
        expect(page.locator("h1")).to_have_text("Tarefas")
        expect(page.locator("[data-task]")).to_have_count(3)                          # the open demo tasks
        width = page.evaluate("document.documentElement.scrollWidth")
        assert width <= 390, f"the page scrolls sideways on a phone ({width}px)"
        expect(page.locator("#top-bar .local-mode")).to_be_visible()                 # no login here
        expect(page.locator("nav")).to_be_visible()                                   # the bottom bar
        page.click("nav >> text=Projetos")
        expect(page.locator("[data-company]")).to_have_count(2)
        browser.close()
    server.shutdown()
    assert not errors, errors
    print("e2e without login: ok")


if __name__ == "__main__":
    run()
    run_without_login()
