import { chromium } from "playwright";
import assert from "node:assert/strict";
import fs from "node:fs/promises";
const config = process.env.E2E_CONFIG
  ? JSON.parse(await fs.readFile(process.env.E2E_CONFIG, "utf8"))
  : {
      email: process.env.E2E_EMAIL,
      password: process.env.E2E_PASSWORD,
      managerName: process.env.E2E_MANAGER_NAME,
      professionalName: process.env.E2E_PROFESSIONAL_NAME,
    };
if (
  !config.email ||
  !config.password ||
  !config.managerName ||
  !config.professionalName
)
  throw Error(
    "Informe uma identidade de teste com dois vínculos (gestor e profissional), e os nomes dos negócios.",
  );
const browser = await chromium.launch();
const page = await browser.newPage({
  viewport: { width: 1280, height: 900 },
  locale: "pt-BR",
});
const errors = [];
page.on("pageerror", (error) => errors.push(error.message));
const requests = [];
page.on("request", (request) => {
  if (request.url().includes("/api/")) requests.push(request.url());
});
try {
  await page.goto(process.env.E2E_BASE_URL || "http://127.0.0.1:5173");
  await page.getByRole("heading", { name: "Bem-vindo ao Beloria" }).waitFor();
  assert.equal(await page.locator("form input").count(), 2);
  await page.getByLabel("E-mail", { exact: true }).fill(config.email);
  await page.getByLabel("Senha", { exact: true }).fill(config.password);
  const sent = page.waitForRequest((r) => r.url().endsWith("/api/auth/login"));
  await page.getByRole("button", { name: "Entrar", exact: true }).click();
  assert.deepEqual(Object.keys((await sent).postDataJSON()).sort(), [
    "email",
    "password",
  ]);
  await page.getByRole("heading", { name: "Escolha seu negócio" }).waitFor();
  assert.equal(
    requests.some((url) => url.includes("/api/dashboard")),
    false,
  );
  await page.reload();
  await page.getByRole("heading", { name: "Escolha seu negócio" }).waitFor();
  await page
    .getByRole("button")
    .filter({ hasText: config.managerName })
    .click();
  await page
    .getByRole("heading", { name: "Visão geral", exact: true })
    .waitFor();
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Profissionais", exact: true })
    .waitFor();
  await page
    .getByRole("button", { name: "Trocar negócio", exact: true })
    .click();
  await page
    .getByRole("button")
    .filter({ hasText: config.professionalName })
    .click();
  await page
    .getByRole("heading", { name: "Visão geral", exact: true })
    .waitFor();
  assert.equal(
    await page
      .getByRole("navigation")
      .getByRole("button", { name: "Profissionais", exact: true })
      .count(),
    0,
  );
  await page
    .getByRole("button", { name: "Trocar negócio", exact: true })
    .click();
  await page.setViewportSize({ width: 390, height: 844 });
  assert.equal(
    await page.evaluate(
      () => document.documentElement.scrollWidth > innerWidth,
    ),
    false,
  );
  await fs.mkdir("test-results", { recursive: true });
  await page.screenshot({
    path: "test-results/business-selection-mobile.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Sair", exact: true }).click();
  await page.getByRole("heading", { name: "Bem-vindo ao Beloria" }).waitFor();
  assert.deepEqual(errors, []);
  console.log(
    "PASS: login somente e-mail/senha, seleção persistente, troca de negócio, permissões distintas, mobile e logout.",
  );
} finally {
  await browser.close();
}
