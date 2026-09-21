import { chromium } from "playwright";
import assert from "node:assert/strict";
import fs from "node:fs/promises";
const config = process.env.E2E_CONFIG
  ? JSON.parse(await fs.readFile(process.env.E2E_CONFIG, "utf8"))
  : {
      business: process.env.E2E_BUSINESS,
      email: process.env.E2E_EMAIL,
      password: process.env.E2E_PASSWORD,
    };
if (!config.password)
  throw Error(
    "Defina E2E_BUSINESS, E2E_EMAIL e E2E_PASSWORD para um banco descartável.",
  );
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
const errors = [];
page.on("pageerror", (e) => errors.push(e.message));
const base = process.env.E2E_BASE_URL || "http://127.0.0.1:5173";
const suffix = Date.now().toString(36);
const professionalEmail = `professional-${suffix}@example.com`;
async function clickNav(name) {
  await page
    .getByRole("navigation")
    .getByRole("button", { name, exact: true })
    .click();
}
async function login(email = config.email) {
  await page.getByLabel("Identificador do negócio").fill(config.business);
  await page.getByLabel("E-mail", { exact: true }).fill(email);
  await page.getByLabel("Senha", { exact: true }).fill(config.password);
  await page.getByRole("button", { name: "Entrar", exact: true }).click();
  await page
    .getByRole("heading", { name: "Visão geral", exact: true })
    .waitFor();
}
async function save() {
  await page
    .getByRole("button", { name: "Salvar cadastro", exact: true })
    .click();
  await page.getByRole("dialog").waitFor({ state: "hidden" });
}
try {
  await page.goto(base);
  await login();
  await clickNav("Especialidades");
  await page.getByRole("button", { name: "Novo cadastro" }).click();
  await page.getByLabel("Nome", { exact: true }).fill("Cabelo " + suffix);
  await save();
  await clickNav("Profissionais");
  await page.getByRole("button", { name: "Novo cadastro" }).click();
  await page.getByLabel("Nome", { exact: true }).fill("Ana " + suffix);
  await page.getByLabel("Contato", { exact: true }).fill("11 99999-0000");
  await page.getByLabel("Comissão (%)").fill("40");
  await page.getByLabel("CPF", { exact: true }).fill("52998224725");
  await page.getByLabel("Cabelo " + suffix, { exact: true }).check();
  await page.getByLabel("E-mail de acesso").fill(professionalEmail);
  await page.getByLabel("Senha de acesso").fill(config.password);
  await save();
  await clickNav("Serviços");
  await page.getByRole("button", { name: "Novo cadastro" }).click();
  await page.getByLabel("Nome", { exact: true }).fill("Corte " + suffix);
  await page
    .getByLabel("Especialidade", { exact: true })
    .selectOption({ label: "Cabelo " + suffix });
  await page.getByLabel("Preço (R$)").fill("50");
  await save();
  await clickNav("Clientes");
  await page.getByRole("button", { name: "Novo cadastro" }).click();
  await page.getByLabel("Nome", { exact: true }).fill("Maria " + suffix);
  await page.getByLabel("Contato", { exact: true }).fill("11 98888-0000");
  await save();
  await page.getByRole("button", { name: "Sair", exact: true }).click();
  await login(professionalEmail);
  assert.equal(
    await page
      .getByRole("navigation")
      .getByRole("button", { name: "Profissionais", exact: true })
      .count(),
    0,
  );
  await clickNav("Atendimentos");
  await page.getByRole("button", { name: "Novo atendimento" }).click();
  await page
    .getByLabel("Serviço", { exact: true })
    .selectOption({ label: "Corte " + suffix + " · R$ 50,00" });
  await page
    .getByRole("button", { name: "Registrar atendimento", exact: true })
    .click();
  await page.getByRole("dialog").waitFor({ state: "hidden" });
  await page.getByText("Pendente", { exact: true }).waitFor();
  await page.getByRole("button", { name: "Sair", exact: true }).click();
  await login();
  await clickNav("Atendimentos");
  const row = page.getByRole("row").filter({ hasText: "Corte " + suffix });
  await row.getByRole("button", { name: "Aprovar", exact: true }).click();
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Confirmar", exact: true })
    .click();
  await page.getByRole("dialog").waitFor({ state: "hidden" });
  await row.getByText("Aprovado", { exact: true }).waitFor();
  await clickNav("Comissões");
  await page
    .getByRole("row")
    .filter({ hasText: "Corte " + suffix })
    .getByRole("checkbox")
    .check();
  await page.getByRole("button", { name: /Registrar repasse/ }).click();
  await page
    .getByLabel("Referência do pagamento")
    .fill("comprovante-" + suffix);
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Confirmar", exact: true })
    .click();
  await page.getByRole("dialog").waitFor({ state: "hidden" });
  await page
    .getByRole("row")
    .filter({ hasText: "Corte " + suffix })
    .getByText("Pago", { exact: true })
    .waitFor();
  await clickNav("Repasses");
  await page.getByText("comprovante-" + suffix, { exact: true }).waitFor();
  await clickNav("Auditoria");
  await page.getByText("Repasse registrado", { exact: true }).first().waitFor();
  await clickNav("Visão geral");
  await page.getByText("Movimento do negócio", { exact: true }).waitFor();
  await page.locator(".loading").waitFor({ state: "hidden" });
  await fs.mkdir("test-results", { recursive: true });
  await page.screenshot({ path: "test-results/desktop.png", fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  assert.equal(
    await page.evaluate(
      () => document.documentElement.scrollWidth > window.innerWidth,
    ),
    false,
    "Mobile page overflow",
  );
  await page.getByRole("button", { name: "Abrir menu", exact: true }).click();
  await clickNav("Comissões");
  await page.locator(".loading").waitFor({ state: "hidden" });
  assert.equal(
    await page.evaluate(
      () => document.documentElement.scrollWidth > window.innerWidth,
    ),
    false,
    "Mobile commissions overflow",
  );
  await page.getByRole("button", { name: "Abrir menu", exact: true }).click();
  await clickNav("Visão geral");
  await page.locator(".loading").waitFor({ state: "hidden" });
  await page.waitForFunction(
    () => document.querySelector(".sidebar").getBoundingClientRect().right <= 1,
  );
  await page.screenshot({
    path: "test-results/mobile.png",
    fullPage: true,
    animations: "disabled",
  });
  assert.deepEqual(errors, [], "Browser runtime errors");
  console.log(
    "PASS: cadastros, login profissional, cliente avulso, atendimento, aprovação, repasse, auditoria, dashboard e mobile (390px).",
  );
} finally {
  await browser.close();
}
