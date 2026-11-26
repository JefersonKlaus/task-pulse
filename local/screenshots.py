"""Takes the README's screenshots (docs/screenshots/*.png) of the built frontend with the demo data.
Run:  python dev.py screenshots   (builds the frontend, then runs this file; needs internet for the fonts)

Phones first (390 x 844, at 2x), then a wide screen (1280 x 800). The demo data is dated around today,
so the dates on the pictures are the day they were taken."""
import threading
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

import server as local_server

OUT = Path(__file__).resolve().parent.parent / "docs" / "screenshots"
PHONE = {"width": 390, "height": 844}
WIDE = {"width": 1280, "height": 800}


def shoot(page, name, whole=False):
    """`whole`: the whole page, by making the window as tall as it (so the menu stays at the bottom,
    which a full-page screenshot would leave in the middle)."""
    page.evaluate("document.fonts.ready.then(() => true)")
    size = page.viewport_size
    if whole:
        page.set_viewport_size({"width": size["width"],
                                "height": page.evaluate("document.documentElement.scrollHeight")})
    page.wait_for_timeout(300)                      # let the last render settle
    page.screenshot(path=str(OUT / f"{name}.png"))
    page.set_viewport_size(size)
    print("  ", f"docs/screenshots/{name}.png")


def go(page, menu):
    page.click(f"nav >> text={menu}")


def screens(page, prefix):
    page.goto(url)
    expect(page.locator("[data-task]").first).to_be_visible()
    shoot(page, f"{prefix}-tasks")

    go(page, "Faturamento")
    expect(page.locator("#billing-tasks")).to_be_visible()
    page.locator("#billing-tasks tbody input[type=checkbox]").first.uncheck()   # one the company won't pay
    shoot(page, f"{prefix}-billing", whole=True)

    go(page, "Empresas")
    page.locator("[data-company]").first.click()                                 # a company and its projects
    expect(page.locator("#company-projects")).to_be_visible()
    shoot(page, f"{prefix}-company")

    go(page, "Projetos")
    page.locator("[data-project='Code review']").click()                         # a project with a flat last hour
    expect(page.locator("#rules")).to_be_visible()
    shoot(page, f"{prefix}-project")


def run():
    global url
    OUT.mkdir(parents=True, exist_ok=True)
    app = local_server.start(0, demo_data=True)
    login = local_server.start(0, require_login=True)
    for server in (app, login):
        threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{app.server_address[1]}/"
    with sync_playwright() as p:
        browser = p.chromium.launch()
        phone = browser.new_page(viewport=PHONE, device_scale_factor=2, color_scheme="light", locale="pt-BR")
        screens(phone, "phone")
        phone.goto(f"http://127.0.0.1:{login.server_address[1]}/")
        expect(phone.locator("#l-email")).to_be_visible()
        shoot(phone, "phone-login")
        phone.click("text=Criar conta")
        phone.fill("#s-name", "Ana Lima")
        phone.fill("#s-email", "ana@exemplo.com")
        expect(phone.locator("#s-repeat")).to_be_visible()
        shoot(phone, "phone-signup", whole=True)

        settings_page = browser.new_page(viewport=PHONE, device_scale_factor=2, color_scheme="light", locale="pt-BR")
        settings_page.goto(url)
        settings_page.click("#top-bar .settings-link")
        expect(settings_page.locator("#settings-language")).to_be_visible()
        shoot(settings_page, "phone-settings")

        english = browser.new_page(viewport=PHONE, device_scale_factor=2, color_scheme="light", locale="en-US")
        english.goto(url)
        expect(english.locator("[data-task]").first).to_be_visible()
        shoot(english, "phone-tasks-en")

        dark = browser.new_page(viewport=PHONE, device_scale_factor=2, color_scheme="dark", locale="pt-BR")
        dark.goto(url)
        expect(dark.locator("[data-task]").first).to_be_visible()
        shoot(dark, "phone-tasks-dark")

        wide = browser.new_page(viewport=WIDE, color_scheme="light", locale="pt-BR")
        wide.goto(url)
        expect(wide.locator("[data-task]").first).to_be_visible()
        shoot(wide, "wide-tasks")
        go(wide, "Faturamento")
        expect(wide.locator("#billing-tasks")).to_be_visible()
        shoot(wide, "wide-billing")
        browser.close()
    for server in (app, login):
        server.shutdown()


if __name__ == "__main__":
    run()
