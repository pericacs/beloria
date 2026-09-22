import { chromium } from "playwright";
import assert from "node:assert/strict";
import fs from "node:fs/promises";
import crypto from "node:crypto";
import { execFileSync } from "node:child_process";
const base = process.env.E2E_BASE_URL;
if (!base || !/^http:\/\/(127\.0\.0\.1|localhost):\d+$/.test(base))
  throw Error("E2E_BASE_URL local obrigatório");
if (!process.env.E2E_DATABASE_URL?.includes("/beloria_test"))
  throw Error("Banco descartável obrigatório");
const platform = JSON.parse(
  await fs.readFile(process.env.E2E_PLATFORM_CONFIG, "utf8"),
);
const password = crypto.randomBytes(24).toString("base64url");
const suffix = Date.now().toString(36),
  name = "E2E Empresa " + suffix,
  email = `company-${suffix}@example.com`;
const browser = await chromium.launch();
const errors = [];
async function page(width = 1440) {
  const context = await browser.newContext({
    viewport: { width, height: width === 1440 ? 1000 : 844 },
  });
  const p = await context.newPage();
  p.on("pageerror", (e) => errors.push(e.message));
  return p;
}
async function login(p, creds) {
  await p.goto(base + "/login");
  await p.getByLabel("E-mail", { exact: true }).fill(creds.email);
  await p.getByLabel("Senha", { exact: true }).fill(creds.password);
  await p.getByRole("button", { name: "Entrar", exact: true }).click();
}
async function screenshot(p, label) {
  assert.equal(
    await p.evaluate(() => document.documentElement.scrollWidth > innerWidth),
    false,
    "Overflow " + label,
  );
  await p.screenshot({
    path: `test-results/commercial-${label}.png`,
    fullPage: true,
  });
}
try {
  await fs.mkdir("test-results", { recursive: true });
  const manager = await page();
  await manager.goto(base + "/login");
  assert.equal(await manager.getByLabel("Identificador do negócio").count(), 0);
  await manager.getByRole("link", { name: "Criar conta", exact: true }).click();
  await screenshot(manager, "signup-desktop");
  await manager.getByLabel("Nome da empresa", { exact: true }).fill(name);
  await manager.getByLabel("Nome do responsável").fill("Responsavel E2E");
  await manager.getByLabel("E-mail", { exact: true }).fill(email);
  await manager.getByLabel("Senha", { exact: true }).fill(password);
  await manager.getByRole("button", { name: "Começar meus 15 dias" }).click();
  await manager
    .getByRole("heading", { name: "Visão geral", exact: true })
    .waitFor();
  assert.equal(new URL(manager.url()).pathname, "/empresa");
  await manager.locator(".loading").waitFor({ state: "hidden" });
  await screenshot(manager, "client-desktop");
  // Seed an actual specialty via the same authorized API; approval remains a browser flow.
  const me = await (await manager.request.get(base + "/api/auth/me")).json();
  const specialty = await manager.request.post(base + "/api/specialties", {
    data: { name: "Especialidade E2E" },
    headers: { "X-CSRF-Token": me.csrf_token },
  });
  assert.equal(specialty.status(), 201);
  await manager
    .getByRole("navigation")
    .getByRole("button", { name: "Convites e aprovações", exact: true })
    .click();
  await manager.getByRole("button", { name: "Gerar convite" }).click();
  await manager.getByLabel("Link do convite").waitFor();
  const link = await manager.getByLabel("Link do convite").inputValue();
  assert.ok(
    (
      await manager
        .getByRole("link", { name: "Compartilhar pelo WhatsApp" })
        .getAttribute("href")
    ).startsWith("https://wa.me/?text="),
  );
  await manager
    .getByRole("button", { name: "Copiar link", exact: true })
    .click();
  const pro = await page(390);
  await pro.goto(link);
  await pro.getByRole("heading", { name, exact: true }).waitFor();
  await screenshot(pro, "invitation-mobile");
  await pro.getByLabel("Nome completo").fill("Especialista E2E");
  await pro.getByLabel("CPF", { exact: true }).fill("52998224725");
  await pro
    .getByLabel("E-mail", { exact: true })
    .fill(`specialist-${suffix}@example.com`);
  await pro.getByLabel("Senha", { exact: true }).fill(password);
  await pro.getByRole("button", { name: "Solicitar vínculo" }).click();
  await pro.getByRole("heading", { name: "Aguardando aprovação" }).waitFor();
  assert.equal((await pro.request.get(base + "/api/dashboard")).status(), 403);
  await screenshot(pro, "pending-mobile");
  await manager.getByRole("button", { name: "Atualizar", exact: true }).click();
  await manager.getByRole("button", { name: "Aprovar vínculo" }).click();
  await manager.getByLabel("Comissão (%)").fill("35");
  await manager.getByLabel("Especialidade E2E").check();
  await manager.getByRole("button", { name: "Confirmar análise" }).click();
  await manager.getByRole("dialog").waitFor({ state: "hidden" });
  await pro.getByRole("button", { name: "Atualizar situação" }).click();
  await pro
    .getByRole("heading", { name: "Seu trabalho, seus resultados." })
    .waitFor();
  await pro.locator(".loading").waitFor({ state: "hidden" });
  await screenshot(pro, "specialist-mobile");
  assert.equal(
    await pro
      .getByRole("button", { name: "Profissionais", exact: true })
      .count(),
    0,
  );
  await pro
    .getByRole("navigation")
    .getByRole("button", { name: "Atendimentos", exact: true })
    .click();
  await pro
    .getByRole("heading", { name: "Atendimentos", exact: true })
    .waitFor();
  await screenshot(pro, "specialist-attendances-mobile");
  await pro
    .getByRole("navigation")
    .getByRole("button", { name: "Início", exact: true })
    .click();
  await pro.setViewportSize({ width: 1440, height: 1000 });
  await pro.locator(".loading").waitFor({ state: "hidden" });
  await screenshot(pro, "specialist-desktop");
  await manager.setViewportSize({ width: 390, height: 844 });
  await screenshot(manager, "invites-mobile");
  await manager
    .getByRole("button", { name: "Abrir menu", exact: true })
    .click();
  await manager
    .getByRole("navigation")
    .getByRole("button", { name: "Visão geral", exact: true })
    .click();
  await manager.locator(".loading").waitFor({ state: "hidden" });
  await screenshot(manager, "client-mobile");
  const admin = await page();
  await login(admin, platform);
  await admin.getByRole("heading", { name: "Empresas e acesso" }).waitFor();
  assert.equal(new URL(admin.url()).pathname, "/beloria");
  await admin.locator(".loading").waitFor({ state: "hidden" });
  await screenshot(admin, "platform-desktop");
  await admin.setViewportSize({ width: 390, height: 844 });
  await screenshot(admin, "platform-mobile");
  execFileSync(
    process.env.E2E_PYTHON || "python",
    ["../backend/tests/expire_e2e_trial.py", name],
    { env: process.env },
  );
  // The next operational request must enforce expiration on an already open session.
  await manager
    .getByRole("button", { name: "Abrir menu", exact: true })
    .click();
  await manager
    .getByRole("navigation")
    .getByRole("button", { name: "Atendimentos", exact: true })
    .click();
  await manager.getByText(/Pagamento indisponível: planos/).waitFor();
  assert.equal(new URL(manager.url()).pathname, "/empresa/assinatura");
  assert.equal(
    await manager.getByRole("button", { name: /Pagar|checkout/i }).count(),
    0,
  );
  await screenshot(manager, "expired-manager-mobile");
  await pro
    .getByRole("navigation")
    .getByRole("button", { name: "Atendimentos", exact: true })
    .click();
  await pro
    .getByText(
      "Acesso suspenso. Entre em contato com o responsável pela empresa.",
      { exact: true },
    )
    .waitFor();
  await pro.waitForURL("**/especialista/suspenso");
  await screenshot(pro, "suspended-specialist");
  await manager.getByRole("button", { name: "Sair", exact: true }).click();
  await manager.getByRole("button", { name: "Entrar", exact: true }).waitFor();
  assert.deepEqual(errors, [], "Browser errors");
  console.log(
    "PASS: cadastro público, três painéis desktop/mobile, convite, aprovação, especialista isolado, trial vencido com sessões abertas e ausência de pagamento fictício.",
  );
} finally {
  await browser.close();
}
