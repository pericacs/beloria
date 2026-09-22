# Beloria

SaaS de gestão operacional e financeira para negócios de beleza. MVP sem agendamento e sem inteligência artificial. Cada negócio tem seus próprios usuários e dados; há administração da plataforma, gestão da empresa e painel pessoal do especialista.

## Acesso local e os três painéis

Nesta máquina, o ambiente sem Docker usa PostgreSQL 16 portátil em `127.0.0.1:55434`, banco **beloria_dev**, backend em `127.0.0.1:8001` e frontend em **http://127.0.0.1:5174**. Os bancos descartáveis de testes ficam em outro servidor, porta 55433. As configurações/credenciais existentes ficam somente em `.local/dev/config.json`, ignorado pelo Git.

| Acesso | URL local | Quem pode usar |
| --- | --- | --- |
| Login | http://127.0.0.1:5174/login | E-mail e senha; destino determinado pelo backend |
| Cadastro público | http://127.0.0.1:5174/cadastro | Responsável pela nova empresa |
| Painel Beloria | http://127.0.0.1:5174/beloria | Administrador da plataforma |
| Painel cliente | http://127.0.0.1:5174/empresa | Gestor vinculado |
| Painel especialista | http://127.0.0.1:5174/especialista | Especialista aprovado |

Digitar uma URL não concede privilégios. Depois do login, a sessão define o painel permitido. O nome do responsável é o novo campo obrigatório do cadastro público; contato é opcional. Não se solicita tipo de negócio, slug ou código.

Executores locais já preparados nesta máquina, na raiz do repositório:

```powershell
# Inicia PostgreSQL portátil, aplica migrações com backend parado e inicia os dois servidores.
.\.venv\Scripts\python.exe .local/dev/manage.py start
# Para somente os processos deste ambiente e seu PostgreSQL, preservando dados.
.\.venv\Scripts\python.exe .local/dev/manage.py stop
# Cria seu administrador da plataforma com prompts de e-mail e senha no terminal.
.\.venv\Scripts\python.exe .local/dev/platform-admin.py
```

Esses executores/configurações são locais, não versionados. Para outra máquina, use a instalação sem containers descrita adiante. Clientes não precisam executar nenhum desses comandos: basta abrir `/cadastro`.

## Administrador da plataforma

Não existe administrador padrão. Com o backend instalado, migrações aplicadas e `DATABASE_URL` apontando para o banco desejado, execute em `backend/`:

```powershell
..\.venv\Scripts\python.exe -m app.platform_cli
```

O terminal solicita e-mail e senha com confirmação oculta. Cria uma identidade exclusiva com permissão `PlatformAdmin`, sem empresa cliente. Um e-mail existente é recusado: o procedimento não promove gestores nem une contas. O cadastro público nunca atribui essa permissão. Entre pelo login comum para chegar ao Painel Beloria.

O painel mostra empresas, início/fim do trial, validade de assinatura, cobranças, conflitos de vínculos e histórico da plataforma. Bloquear/desbloquear manualmente exige motivo auditado; remover bloqueio **não renova trial e não confirma pagamento**. Não dá acesso aos dados operacionais das empresas.

## Convites e aprovação

1. Gestor abre **Convites e aprovações** e **Gerar convite**. O link da interface vale 7 dias; a API aceita 1 a 30 dias. O token aleatório é mostrado somente na criação e seu hash é armazenado.
2. Use **Copiar link** ou **Compartilhar pelo WhatsApp**. O WhatsApp é aberto para envio manual; nada é enviado automaticamente. O gestor pode revogar o convite.
3. Abra o link em outro perfil/janela privada. O nome da empresa aparece automaticamente. Cadastre o especialista ou use **Já tenho conta — entrar** antes de solicitar o vínculo.
4. O especialista vê apenas **Aguardando aprovação**. Gestor analisa documentos, define especialidades e comissão, e aprova/rejeita. Rejeição exige motivo. A aprovação de vínculo é independente da aprovação de atendimentos.
5. Após aprovação, **Atualizar situação** ou a atualização automática libera o painel próprio. Um convite de outra empresa não transfere vínculo. Reservas e bloqueios transacionais impedem duas solicitações/vínculos simultâneos; vínculos inativos também impedem transferência implícita.

## Trial, assinatura e integração pendente

Cadastros novos recebem exatamente 15 dias calculados no backend, sem cartão. Repetição do cadastro com o mesmo e-mail falha sem renovar prazo. No vencimento, endpoints operacionais retornam 402 mesmo para sessões abertas: gestor vai para `/empresa/assinatura`; especialista vê “Acesso suspenso. Entre em contato com o responsável pela empresa.” Autenticação/logout continuam disponíveis; somente o gestor consulta a própria cobrança.

**Cobrança real indisponível.** Ainda faltam preço, planos, periodicidade, provedor, credenciais, configuração de webhook e regras de inadimplência/renovação/cancelamento após contratação. A interface informa essa situação e não apresenta botão falso de pagamento. Nenhuma cobrança real é criada nesta entrega.

`payment_provider.py` define o contrato do adaptador. Uma integração futura deve autenticar o evento, verificar liquidação com o provedor e retornar período pago confiável. O backend confere referência, valor/moeda e datas, registra eventos idempotentes e atualiza a assinatura apenas após confirmação. Criar checkout, receber retorno do navegador ou ter cobrança pendente nunca libera acesso. Bloqueio administrativo permanece soberano. Testes usam um adaptador HMAC controlado, exclusivamente dentro da suíte; o aplicativo não contém modo de pagamento fictício.

### Migração comercial e contas anteriores

Antes da atualização, pare os serviços, faça backup verificado e execute em `backend/`:

```powershell
..\.venv\Scripts\python.exe -m app.commercial_preflight
..\.venv\Scripts\python.exe -m alembic upgrade head
```

A migração `3be600b16a15` é aditiva. Empresas anteriores mantêm acesso legado identificado como **Legado — revisar contratação**, com datas de trial nulas: não recebem trial novo. O proprietário precisa revisar a contratação individualmente, definir condições reais e, se necessário, aplicar bloqueio manual. Empresas criadas depois da migração não herdam acesso legado.

Identidades com um vínculo de profissional e mais de uma empresa são marcadas para revisão; todos os vínculos e históricos permanecem, mas o acesso operacional dessa identidade é bloqueado. O painel lista os vínculos preservados. A regularização exige decisão administrativa individual e plano de migração específico: não há transferência automática, exclusão de histórico ou escolha do primeiro vínculo. Duplicidades de e-mail continuam separadas, com o tratamento da seção de autenticação abaixo. Gestores antigos nunca viram administradores da plataforma.

O downgrade comercial recusa perda de novos dados de contratação, trial, convites, auditoria ou pagamento. Após uso dessas funções, restaure somente backup validado em ambiente separado ou aplique correção para frente; não tente contornar a proteção removendo dados.

### Testar vencimento sem alterar dados reais

Use um banco **descartável** `beloria_test...` e uma empresa sintética recém-cadastrada. O auxiliar abaixo recusa outros nomes/hosts e altera somente a empresa indicada; nunca use `beloria_dev`:

```powershell
$env:E2E_DATABASE_URL='postgresql+psycopg://USUARIO:SENHA@127.0.0.1:55433/beloria_test_commercial_ui'
.\.venv\Scripts\python.exe backend/tests/expire_e2e_trial.py 'NOME EXATO DA EMPRESA SINTETICA'
```

Mantenha sessões do gestor e especialista abertas e navegue para Atendimentos: o primeiro recebe a tela de assinatura, o segundo a suspensão. Nenhum registro operacional é apagado. A confirmação controlada de pagamento é testada pela suíte PostgreSQL, sem endpoint de simulação público.

### Verificações comerciais

A suíte PostgreSQL inclui cadastro sem privilégios, três destinos de login, convites válidos/expirados/revogados, pendência, aprovação/rejeição isolada, vínculos concorrentes, expiração com sessão aberta, pagamento pendente, assinatura de evento, idempotência e preservação de migração/histórico. Os testes operacionais anteriores de atendimento, comissão e repasse permanecem.

`frontend/commercial-e2e.mjs` testa cadastro, convites, aprovação, painéis desktop/mobile e vencimento em banco descartável. Requer `E2E_BASE_URL` local, `E2E_DATABASE_URL`, `E2E_PYTHON` e `E2E_PLATFORM_CONFIG` apontando para JSON **ignorado pelo Git** contendo e-mail/senha de administrador sintético previamente criado no banco de testes. Execute `node commercial-e2e.mjs` em `frontend/`. O fluxo operacional anterior permanece em `frontend/e2e.mjs`; capturas ficam em `frontend/test-results/`, ignorado.

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
docker compose up -d web
```

Clientes criam sua empresa em **Criar conta**, pelo navegador, sem comandos administrativos. Senhas têm 12 a 128 caracteres; não há senha padrão. Login pede **somente e-mail e senha**.

Acesse **http://localhost:8080**. Saúde da API: **http://localhost:8080/api/health**. A documentação interativa está em **http://127.0.0.1:8000/docs** no desenvolvimento sem containers; o Nginx não a expõe.

Para Linux/macOS:

```bash
cp .env.example .env
python3 -c 'import pathlib,secrets; p=pathlib.Path(".env"); p.write_text(p.read_text().replace("POSTGRES_PASSWORD=", "POSTGRES_PASSWORD="+secrets.token_hex(24)))'
docker compose up -d --build db backend
docker compose exec backend python -m alembic upgrade head
docker compose up -d web
```

Não execute novamente o gerador de senha sobre um `.env` já configurado. `POSTGRES_PASSWORD` é definido na primeira inicialização do volume. A porta web fica vinculada apenas a loopback. `COOKIE_SECURE=false` é exclusivo para HTTP local. Na implantação futura com HTTPS, use `COOKIE_SECURE=true`, configure domínio, TLS, backups e uma credencial de banco própria. Esta entrega não publica em produção.

## Login, vínculos e atualização de instalações existentes

Uma identidade de gestor pode ter vários vínculos explícitos. Especialistas ficam restritos a uma única empresa, inclusive quando o vínculo em outra empresa seria de gestor. Um vínculo ativo entra diretamente; vários exibem **Escolha seu negócio**, com nomes e papéis, antes de liberar os dados. No painel, **Trocar negócio** permite selecionar outro vínculo autorizado. Slug, código e tipo de negócio não participam do login nem da definição de permissões.

A migração `e71f_identity_memberships` cria **uma identidade por conta antiga**, preservando IDs de usuários/vínculos, hashes de senha, profissionais, auditoria e registros financeiros. E-mails são normalizados para minúsculas, sem espaços nas extremidades. Contas que colidem após normalização permanecem separadas e com login bloqueado, mesmo quando as senhas coincidem. A resposta pública é genérica, sem revelar negócios ou contas. Contas sem conflito continuam entrando com a senha anterior.

As sessões antigas são revogadas. Antes de atualizar uma instalação com dados, tenha um backup validado e interrompa backend e frontend: não execute versões antigas e novas simultaneamente. Não há compatibilidade de escrita com a versão anterior nesta janela.

```powershell
docker compose stop web backend
docker compose build backend web
docker compose run --rm backend python -m alembic upgrade head
docker compose up -d backend web
```

No ambiente direto, pare o Uvicorn, configure `DATABASE_URL`, execute `python -m alembic upgrade head` em `backend/` e reinicie o servidor com o código atualizado. O frontend deve ser atualizado junto.

Regularização por um administrador com acesso ao servidor, **após verificar a titularidade de cada conta**:

```powershell
docker compose exec backend python -m app.cli --list-conflicts
# Substitua o ID pelo exibido acima e forneça um e-mail exclusivo dessa pessoa.
docker compose exec backend python -m app.cli --identity-id 123 --set-email pessoa@exemplo.com
```

Esse comando mantém a senha e o vínculo da identidade escolhida, atualiza o e-mail e revoga suas sessões; não junta contas. Cada identidade conflitante deve ser regularizada explicitamente. A última pode conservar o e-mail original quando ele já estiver livre, passando-o a `--set-email`.

Novas criações com e-mail já utilizado são rejeitadas sem reutilizar identidade automaticamente. Para conceder um novo vínculo, use o **ID explícito** de uma identidade habilitada, somente após confirmar a titularidade e a autorização do novo negócio:

```powershell
# Criar outro negócio para uma identidade existente (o ID é informado na criação administrativa).
docker compose exec backend python -m app.cli --business segunda-unidade --name "Segunda unidade" --identity-id 123
# Ou conceder papel de gestor em um negócio já existente.
docker compose exec backend python -m app.cli --identity-id 123 --link-business segunda-unidade
```

Execute apenas o comando adequado ao caso: o mesmo vínculo não pode ser criado duas vezes. Para um vínculo de profissional, acrescente `--role profissional --professional-id ID`; o profissional deve pertencer ao negócio e ainda não possuir conta vinculada. O comando não move nem une contas já existentes.

O gestor de um negócio não pode alterar e-mail/senha de uma identidade compartilhada com outros negócios nem desbloquear identidades conflitantes. Pode editar os dados e ativar/desativar o vínculo do seu próprio negócio. Os endpoints continuam validando sessão, negócio e papel em cada requisição; uma sessão aguardando seleção não acessa cadastros, financeiro ou dashboard.

Rollback da migração antiga de identidade, somente se a migração comercial puder ser revertida sem perda (veja abaixo): com os serviços parados, execute `python -m alembic downgrade ddd468014c2d` usando o código novo e só depois restaure a versão anterior de backend/frontend. As colunas legadas de credenciais são mantidas sincronizadas para isso. Sessões são revogadas novamente; contas por negócio e histórico permanecem. O agrupamento global dos vínculos não existe no schema antigo: uma nova migração volta a tratar cada conta separadamente e bloqueia duplicidades para regularização. Não faça downgrade se precisar manter esse agrupamento; restaure o backup validado ou corrija para frente.

## Primeiro fluxo

1. Em **Criar conta**, cadastre empresa, responsável, e-mail e senha. O trial de 15 dias começa no servidor. Entre e cadastre uma especialidade.
2. Em **Convites e aprovações**, gere e compartilhe um convite. O especialista preenche os dados e cria sua própria senha; o gestor analisa, define especialidades/comissão e aprova o vínculo. O cadastro administrativo direto de profissionais permanece disponível.
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
$env:E2E_EMAIL='gestor-do-teste@exemplo.com'
$env:E2E_PASSWORD=Read-Host 'Senha temporária do gestor de teste'
$env:E2E_BASE_URL='http://127.0.0.1:5173'
node e2e.mjs
```

O teste cria cadastros identificados por um sufixo único, registra atendimento pelo profissional, aprova e repassa pelo gestor, confere auditoria e testa mobile (390 px). Capturas são gravadas em `frontend/test-results/`, ignorado no Git.

Para testar o seletor no navegador, use uma identidade descartável que seja gestora em um negócio e profissional em outro:

```powershell
$env:E2E_MANAGER_NAME='Nome do negócio como gestor'
$env:E2E_PROFESSIONAL_NAME='Nome do negócio como profissional'
# E2E_EMAIL, E2E_PASSWORD e E2E_BASE_URL configurados como acima.
node auth-e2e.mjs
```

Esse teste confirma que o formulário e a requisição contêm apenas e-mail/senha, persiste a seleção no recarregamento, troca de papel/negócio e verifica logout e mobile. Foi executado com sucesso no Chromium, junto com `e2e.mjs`.

GitHub Actions executa testes com PostgreSQL 16 e build React a cada push/PR. O teste de navegador é executável localmente com os comandos acima.

## Arquitetura e regras

- `backend/app/auth.py`: Argon2id, sessão opaca de 12 horas com hash do token no banco, cookie HttpOnly/SameSite=Strict, proteção CSRF e limite de tentativas compartilhado pelo banco. A identidade global autentica e-mail/senha; `users` contém os vínculos com negócio, papel e profissional. Alterações de credenciais revogam todas as sessões da identidade.
- `catalog.py`: cadastros, conta individual e relações com especialidades. CPF para autônomos/CLT e CNPJ para MEI. CPF opcional adicional para MEI. Validação do dígito verificador não consulta situação cadastral.
- `finance.py`: snapshots de preço e comissão, aprovação, repasses transacionais. Centavos inteiros, comissão em pontos-base (100 = 1%), arredondamento metade para cima. Bloqueios PostgreSQL e unicidade impedem duplicatas mesmo com requisições concorrentes.
- `reporting.py`: indicadores reais. Período usa a data do atendimento em `America/Sao_Paulo`; repasses filtrados mostram a parcela referente aos atendimentos do filtro. Profissional vê somente sua própria produção e valores.
- `models.py` e `alembic/versions`: relações compostas por negócio, restrições e migrações versionadas. Alterações relevantes geram auditoria com usuário e data na mesma transação.
- `frontend/src`: telas e componentes React separados. UI em português, diálogos nativos acessíveis, estados de carregamento/erro/vazio/sucesso e layout responsivo.
- `compose.yaml`: PostgreSQL 16, FastAPI/Python 3.12, React/Vite e Nginx, sem Redis ou filas.

Endpoints financeiros de criação exigem `Idempotency-Key` (8 a 100 caracteres); repetir a mesma chave e corpo retorna o registro original, mudar o corpo gera conflito. Toda escrita autenticada exige `X-CSRF-Token` retornado pelo login ou `/api/auth/me`. O login aceita apenas `email` e `password`. `/api/auth/me` restaura a sessão, inclusive a etapa de seleção. `/api/auth/select-business` recebe `membership_id` depois da autenticação, verifica o vínculo ativo, rotaciona cookie/CSRF e aplica o negócio e o papel desse vínculo. O cliente não fornece `business_id` para autorizar acesso: o negócio vem exclusivamente do vínculo selecionado na sessão. Listagens retornam `items`, `total`, `page`, `page_size` (máximo 100).

Algoritmo de CNPJ numérico/alfanumérico conforme [manual da Receita Federal](https://www.gov.br/receitafederal/pt-br/centrais-de-conteudo/publicacoes/documentos-tecnicos/cnpj/manual-dv-cnpj.pdf): conversão ASCII − 48 e módulo 11.

## Verificação desta entrega e limitações

- 36 testes backend executados e aprovados em PostgreSQL 16.15, incluindo identidade/vínculos, e-mails duplicados, seleção e migração com histórico.
- Build TypeScript/Vite executado com sucesso.
- Teste ponta a ponta executado em Chromium: cadastros, sessão de profissional, atendimento avulso, aprovação, repasse, auditoria, dashboard e mobile de 390 px; sem erros JavaScript.
- Docker Desktop desta máquina falhou ao iniciar seu componente interno de inferência. Por isso o PostgreSQL 16 usado na verificação foi uma distribuição portátil isolada; a execução completa dos containers permanece sem validação local.
- As referências falharam na ferramenta de navegação inicial, mas foram acessadas depois pelo Chromium local. A interface preserva a identidade solicitada: Beloria, verde escuro, menu lateral, cards, gráfico à esquerda, resumo à direita e últimos atendimentos abaixo; mobile em coluna.
- Recuperação de senha por e-mail, estorno após aprovação/pagamento, transferência bancária, agendamento e IA não foram implementados. O gestor pode redefinir a senha de profissionais com identidade exclusiva do seu negócio; identidades compartilhadas exigem administração no servidor. A criação inicial do gestor usa o comando administrativo.
