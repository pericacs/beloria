# Beloria

SaaS de gestão operacional e financeira para negócios de beleza. MVP sem agendamento e sem inteligência artificial. Cada negócio tem seus próprios usuários e dados; os perfis são gestor e profissional.

## Requisitos

- Docker Engine/Desktop funcionando e Docker Compose v2.
- Para desenvolvimento sem containers: Python 3.12, PostgreSQL 16, Node.js 22 e npm.
- Nenhuma conta de serviço externo é necessária.

## Iniciar com Docker (PowerShell 7)

Na raiz do repositório:

```powershell
Copy-Item .env.example .env
# Gera uma senha aleatória hexadecimal compatível com a URL de conexão.
$senhaBanco = [Convert]::ToHexString([System.Security.Cryptography.RandomNumberGenerator]::GetBytes(24))
(Get-Content .env -Raw).Replace('POSTGRES_PASSWORD=', "POSTGRES_PASSWORD=$senhaBanco") | Set-Content -Encoding utf8 .env
docker compose up -d --build db backend
docker compose exec backend python -m alembic upgrade head
docker compose exec backend python -m app.cli --business meu-salao --name "Meu Salão" --email gestor@exemplo.com
docker compose up -d web
```

O comando administrativo solicita e confirma a senha do gestor interativamente (12 a 128 caracteres). Não existe senha padrão. Use o identificador `meu-salao`, o e-mail informado e a senha escolhida no login.

Acesse **http://localhost:8080**. Saúde da API: **http://localhost:8080/api/health**. A documentação interativa está em **http://127.0.0.1:8000/docs** no desenvolvimento sem containers; o Nginx não a expõe.

Para Linux/macOS:

```bash
cp .env.example .env
python3 -c 'import pathlib,secrets; p=pathlib.Path(".env"); p.write_text(p.read_text().replace("POSTGRES_PASSWORD=", "POSTGRES_PASSWORD="+secrets.token_hex(24)))'
docker compose up -d --build db backend
docker compose exec backend python -m alembic upgrade head
docker compose exec backend python -m app.cli --business meu-salao --name "Meu Salão" --email gestor@exemplo.com
docker compose up -d web
```

Não execute novamente o gerador de senha sobre um `.env` já configurado. `POSTGRES_PASSWORD` é definido na primeira inicialização do volume. A porta web fica vinculada apenas a loopback. `COOKIE_SECURE=false` é exclusivo para HTTP local. Na implantação futura com HTTPS, use `COOKIE_SECURE=true`, configure domínio, TLS, backups e uma credencial de banco própria. Esta entrega não publica em produção.

## Primeiro fluxo

1. Entre como gestor; cadastre uma especialidade.
2. Cadastre um profissional: contato, vínculo, documento, especialidades, comissão e credenciais individuais.
3. Cadastre um serviço vinculado à especialidade e seu preço. Clientes são opcionais.
4. Entre como profissional e registre um atendimento, com cliente cadastrado ou avulso.
5. Entre como gestor; aprove ou rejeite em **Atendimentos** (motivo obrigatório na rejeição).
6. Em **Comissões**, selecione atendimentos aprovados a pagar e informe a referência do pagamento em **Registrar repasse**.
7. Consulte **Repasses**, **Visão geral** e **Auditoria**.

O repasse é um registro de pagamento já realizado: não transfere dinheiro. A seleção na tela de comissões é restrita à página atual. Não há edição nem exclusão de lançamentos financeiros; erros de atendimentos pendentes podem ser rejeitados e relançados. Estorno de atendimentos já aprovados/pagos não integra esta entrega.

## Desenvolvimento sem containers (PowerShell)

Crie previamente os bancos `beloria_dev` e `beloria_test` no seu PostgreSQL 16 e um usuário com permissões apenas nesses bancos. Substitua a URL abaixo pela sua credencial, com caracteres especiais percent-encoded.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
$env:DATABASE_URL='postgresql+psycopg://USUARIO:SENHA@127.0.0.1:5432/beloria_dev'
$env:COOKIE_SECURE='false'
Set-Location backend
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m app.cli --business meu-salao --name "Meu Salão" --email gestor@exemplo.com
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Em outro terminal, na raiz:

```powershell
Set-Location frontend
npm ci
npm run dev -- --host 127.0.0.1
```

Abra **http://127.0.0.1:5173**. O Vite encaminha `/api` para a porta 8000. A API não habilita CORS: frontend e API usam a mesma origem. Não há dados fictícios pré-carregados.

## Testes e build

Suíte em banco descartável PostgreSQL 16, separada do banco da aplicação:

```powershell
docker compose -f compose.test.yaml up --build --abort-on-container-exit --exit-code-from tests
docker compose -f compose.test.yaml down
```

Execução direta (na raiz), sobre banco exclusivo de testes:

```powershell
$env:TEST_DATABASE_URL='postgresql+psycopg://USUARIO:SENHA@127.0.0.1:5432/beloria_test'
Set-Location backend
..\.venv\Scripts\python.exe -m pytest -q
Set-Location ../frontend
npm ci
npm run build
```

**A suíte apaga os dados e reverte migrações do banco de testes.** Ela exige explicitamente `TEST_DATABASE_URL` e um nome de banco começando com `beloria_test`. Não aponte para dados reais.

Testes cobrem isolamento de dois negócios (API e restrições SQL), permissões, CSRF, logout, limite de tentativas de login, desativação, documentos, arredondamento e snapshots, aprovação/rejeição, idempotência, concorrência de lançamentos e repasses, totais grandes, paginação e migrações de ida/volta com verificação do schema.

Teste de navegador contra uma instância **descartável** em execução, com um negócio e gestor já criados:

```powershell
Set-Location frontend
npx playwright install chromium
$env:E2E_BUSINESS='identificador-do-negocio-de-teste'
$env:E2E_EMAIL='gestor-do-teste@exemplo.com'
$env:E2E_PASSWORD=Read-Host 'Senha temporária do gestor de teste'
$env:E2E_BASE_URL='http://127.0.0.1:5173'
node e2e.mjs
```

O teste cria cadastros identificados por um sufixo único, registra atendimento pelo profissional, aprova e repassa pelo gestor, confere auditoria e testa mobile (390 px). Capturas são gravadas em `frontend/test-results/`, ignorado no Git.

GitHub Actions executa testes com PostgreSQL 16 e build React a cada push/PR. O teste de navegador é executável localmente com os comandos acima.

## Arquitetura e regras

- `backend/app/auth.py`: Argon2id, sessão opaca de 12 horas com hash do token no banco, cookie HttpOnly/SameSite=Strict, proteção CSRF e limite de tentativas compartilhado pelo banco. Senhas alteradas invalidam sessões do profissional.
- `catalog.py`: cadastros, conta individual e relações com especialidades. CPF para autônomos/CLT e CNPJ para MEI. CPF opcional adicional para MEI. Validação do dígito verificador não consulta situação cadastral.
- `finance.py`: snapshots de preço e comissão, aprovação, repasses transacionais. Centavos inteiros, comissão em pontos-base (100 = 1%), arredondamento metade para cima. Bloqueios PostgreSQL e unicidade impedem duplicatas mesmo com requisições concorrentes.
- `reporting.py`: indicadores reais. Período usa a data do atendimento em `America/Sao_Paulo`; repasses filtrados mostram a parcela referente aos atendimentos do filtro. Profissional vê somente sua própria produção e valores.
- `models.py` e `alembic/versions`: relações compostas por negócio, restrições e migrações versionadas. Alterações relevantes geram auditoria com usuário e data na mesma transação.
- `frontend/src`: telas e componentes React separados. UI em português, diálogos nativos acessíveis, estados de carregamento/erro/vazio/sucesso e layout responsivo.
- `compose.yaml`: PostgreSQL 16, FastAPI/Python 3.12, React/Vite e Nginx, sem Redis ou filas.

Endpoints financeiros de criação exigem `Idempotency-Key` (8 a 100 caracteres); repetir a mesma chave e corpo retorna o registro original, mudar o corpo gera conflito. Toda escrita autenticada exige `X-CSRF-Token` retornado pelo login ou `/api/auth/me`. O cliente não envia `business_id`: o negócio vem exclusivamente da sessão. Listagens retornam `items`, `total`, `page`, `page_size` (máximo 100).

Algoritmo de CNPJ numérico/alfanumérico conforme [manual da Receita Federal](https://www.gov.br/receitafederal/pt-br/centrais-de-conteudo/publicacoes/documentos-tecnicos/cnpj/manual-dv-cnpj.pdf): conversão ASCII − 48 e módulo 11.

## Verificação desta entrega e limitações

- 25 testes backend executados e aprovados em PostgreSQL 16.15; a primeira bateria de 21 também passou no PostgreSQL 18.
- Build TypeScript/Vite executado com sucesso.
- Teste ponta a ponta executado em Chromium: cadastros, sessão de profissional, atendimento avulso, aprovação, repasse, auditoria, dashboard e mobile de 390 px; sem erros JavaScript.
- Docker Desktop desta máquina falhou ao iniciar seu componente interno de inferência. Por isso o PostgreSQL 16 usado na verificação foi uma distribuição portátil isolada; a execução completa dos containers permanece sem validação local.
- As referências falharam na ferramenta de navegação inicial, mas foram acessadas depois pelo Chromium local. A interface preserva a identidade solicitada: Beloria, verde escuro, menu lateral, cards, gráfico à esquerda, resumo à direita e últimos atendimentos abaixo; mobile em coluna.
- Recuperação de senha por e-mail, estorno após aprovação/pagamento, transferência bancária, agendamento e IA não foram implementados. O gestor pode redefinir a senha de profissionais no cadastro. A criação inicial do gestor usa o comando administrativo.
