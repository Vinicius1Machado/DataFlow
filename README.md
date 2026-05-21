# DataFlow

DataFlow e uma plataforma web para transformar arquivos de dados brutos em scripts Python de tratamento prontos para uso, com analise tecnica, validacao de seguranca, empacotamento dos artefatos e historico por usuario.

O sistema recebe arquivos CSV, Parquet, JSON e XML, identifica inconsistencias nos dados e gera automaticamente:

- `script_tratamento.py`
- `README.md`
- `requirements.txt`
- `analysis.json`
- pacote final `resultado.zip`

## Visao Geral

O DataFlow automatiza o caminho entre um arquivo bruto e um pacote de tratamento de dados reutilizavel. O usuario faz login, nomeia um processamento, envia um arquivo pelo frontend e acompanha o status ate receber script, README, requirements, relatorio de analise e pacote ZIP.

O backend armazena o arquivo no MinIO, registra o job no PostgreSQL, impede repeticao do mesmo arquivo por usuario e aciona um workflow n8n. O n8n chama o Worker Python para gerar um perfil tecnico do arquivo, usa IA para gerar artefatos e envia o resultado de volta ao backend.

Antes de salvar o script gerado, o backend executa uma validacao de seguranca para bloquear comandos perigosos como `eval`, `exec`, `subprocess`, `os.system`, `socket`, `requests`, `urllib`, `importlib` e acessos sensiveis.

## Arquitetura

```text
Frontend Next.js
  -> Backend FastAPI
    -> MinIO
    -> PostgreSQL
    -> n8n Webhook
      -> Worker FastAPI /profile
      -> IA / Structured Output
      -> Backend Callback
```

Componentes:

- `apps/frontend`: interface web em Next.js.
- `apps/backend`: API FastAPI, banco, upload, callback, seguranca de script e empacotamento ZIP.
- `services/worker`: API FastAPI para leitura/perfil tecnico dos arquivos.
- `infra`: Docker Compose com PostgreSQL, MinIO, Redis e n8n.
- `docs`: documentacao do workflow n8n e payloads.
- `shared/schemas`: JSON Schema da resposta esperada da IA.

## Fluxo Da Aplicacao

1. O usuario seleciona um arquivo no frontend.
2. O frontend envia `POST /api/files/upload` para o backend.
3. O backend valida extensao, tamanho e conteudo inicial.
4. O backend salva o arquivo no MinIO em `raw/{job_id}/{nome_arquivo}`.
5. O backend cria um registro em `data_jobs`.
6. O backend chama o webhook do n8n com `x-webhook-secret`.
7. O n8n chama o Worker em `POST /profile`.
8. O Worker baixa o arquivo, le com Pandas e retorna `analysis`.
9. O n8n monta o prompt e chama a IA.
10. O n8n valida a resposta estruturada.
11. O n8n chama `POST /api/n8n/callback` no backend.
12. O backend valida o script gerado, cria `resultado.zip` e atualiza o job.
13. O frontend consulta `GET /api/jobs/{job_id}` e exibe status/artefatos.

## Stack Tecnica

- Frontend: Next.js, TypeScript, Tailwind CSS
- Backend: FastAPI, SQLAlchemy, Alembic, Pydantic Settings
- Banco: PostgreSQL 16
- Storage: MinIO compativel com S3
- Orquestracao: n8n
- Worker: FastAPI, Pandas, PyArrow, lxml, xmltodict
- Cache/fila futura: Redis
- Testes backend: pytest
- Execucao local: Docker Compose

## Pre-Requisitos

- Docker e Docker Compose
- Python compatível com o ambiente local do projeto
- Node.js e npm
- VSCode, opcional

No Windows PowerShell, prefira `npm.cmd` quando o comando `npm` for bloqueado por politica de execucao.

## Como Configurar `.env`

Crie o arquivo local a partir do exemplo:

```bash
cp .env.example .env
```

No Windows PowerShell, se `cp` nao estiver disponivel no seu terminal:

```powershell
Copy-Item .env.example .env
```

Variaveis principais:

```env
APP_ENV=docker
BACKEND_PORT=8000
BACKEND_URL=http://backend:8000
BACKEND_CORS_ORIGINS=http://localhost:3000
BACKEND_CALLBACK_URL=http://backend:8000/api/n8n/callback
WORKER_PROFILE_URL=http://worker:8001/profile

NEXT_PUBLIC_API_URL=http://localhost:8000

POSTGRES_DB=data_script_generator
POSTGRES_USER=app_user
POSTGRES_PASSWORD=app_password
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

PGADMIN_PORT=5050
PGADMIN_DEFAULT_EMAIL=admin@local.dev
PGADMIN_DEFAULT_PASSWORD=admin123

MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin123
MINIO_BUCKET=data-generator
MINIO_ENDPOINT=http://minio:9000
MINIO_PUBLIC_ENDPOINT=http://localhost:9000
MINIO_WORKER_ENDPOINT=http://minio:9000

N8N_PORT=5678
N8N_WEBHOOK_URL=http://n8n:5678/webhook/data-analysis
N8N_CALLBACK_URL=http://backend:8000/api/n8n/callback
N8N_WEBHOOK_SECRET=troque_este_segredo

AI_PROVIDER=openai
OPENAI_API_KEY=troque_esta_chave
```

Nao commite `.env` nem chaves reais.

## Como Subir Ambiente Docker Compose

O ambiente Docker Compose sobe frontend, backend, worker, n8n, PostgreSQL, MinIO, Redis e o container one-shot de criacao de bucket.

```bash
cd infra
docker compose up -d --build
```

Ver servicos:

```bash
docker compose ps
```

Logs uteis:

```bash
docker compose logs -f backend
docker compose logs -f worker
docker compose logs -f n8n
```

Conferir variaveis internas do n8n:

```bash
docker compose exec n8n sh -lc 'printenv | grep -E "N8N_WEBHOOK_SECRET|WORKER_PROFILE_URL|BACKEND_CALLBACK_URL"'
```

Testar comunicacao interna do n8n com worker e backend:

```bash
docker compose exec n8n sh -lc 'wget -qO- http://worker:8001/health'
docker compose exec n8n sh -lc 'wget -qO- http://backend:8000/health'
```

Se `wget` nao existir no container n8n, use `curl` ou Node.js:

```bash
docker compose exec n8n sh -lc 'curl -fsS http://worker:8001/health'
docker compose exec n8n node -e "fetch('http://backend:8000/health').then(r => r.text()).then(console.log)"
```

Parar o ambiente:

```bash
docker compose down
```

Servicos locais:

- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`
- Worker: `http://localhost:8001`
- n8n: `http://localhost:5678`
- pgAdmin: `http://localhost:5050`
- PostgreSQL: `localhost:5432`
- MinIO API: `http://localhost:9000`
- MinIO Console: `http://localhost:9001`
- Redis: `localhost:6379`

Mais detalhes em [docs/docker-compose-setup.md](docs/docker-compose-setup.md).

## Como Rodar Backend

Instalar dependencias:

```bash
cd apps/backend
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

Rodar migrations:

```bash
alembic upgrade head
```

Rodar API:

```bash
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Health check:

```bash
curl http://localhost:8000/health
```

Testes:

```bash
pytest
```

## Como Rodar Worker

Instalar dependencias:

```bash
cd services/worker
python -m pip install -r requirements.txt
```

Rodar Worker:

```bash
python -m uvicorn app.main:app --reload --port 8001
```

Health check:

```bash
curl http://localhost:8001/health
```

Testar profiling manualmente:

```bash
curl -X POST http://localhost:8001/profile ^
  -H "Content-Type: application/json" ^
  -d "{\"job_id\":\"job-test\",\"file_url\":\"http://localhost:9000/data-generator/raw/job-test/arquivo.csv\",\"file_type\":\"csv\"}"
```

## Como Rodar Frontend

Instalar dependencias:

```bash
cd apps/frontend
npm.cmd install
```

Rodar em desenvolvimento:

```bash
npm.cmd run dev
```

Abrir:

```text
http://localhost:3000
```

Build:

```bash
npm.cmd run build
```

## Como Configurar n8n

O workflow deve ser criado manualmente no n8n. A documentacao completa esta em:

- [docs/n8n-workflow.md](docs/n8n-workflow.md)
- [docs/payloads.md](docs/payloads.md)

Nome do workflow:

```text
Gerador de Script Python - Tratamento de Dados
```

Nos esperados:

1. `Webhook Trigger`
2. `IF - Validar x-webhook-secret`
3. `HTTP Request - Chamar Worker /profile`
4. `Code - Montar prompt para IA`
5. `AI Agent ou HTTP Request para provider de IA`
6. `Structured Output Parser para validar JSON`
7. `Code - Montar callback`
8. `HTTP Request - Enviar callback para backend`
9. `Respond to Webhook`

Webhook configurado no backend:

```env
N8N_WEBHOOK_URL=http://n8n:5678/webhook/data-analysis
```

Header obrigatorio:

```text
x-webhook-secret: <N8N_WEBHOOK_SECRET>
```

Callback para o backend:

```text
POST http://backend:8000/api/n8n/callback
```

## Como Testar Ponta A Ponta

Execute a partir da raiz do projeto.

1. Suba o ambiente:

```bash
cd infra
docker compose up -d --build
```

2. Configure e ative o workflow n8n conforme [docs/n8n-workflow.md](docs/n8n-workflow.md).

3. Abra:

```text
http://localhost:3000
```

4. Envie um arquivo `.csv`, `.parquet`, `.json` ou `.xml`.

5. Clique em `Consultar status` ate o job finalizar.

6. Quando `COMPLETED`, a tela exibe script, README, requirements, analise e botoes de download.

Endpoints uteis:

```bash
curl http://localhost:8000/api/jobs
curl http://localhost:8000/api/jobs/{job_id}
curl http://localhost:8000/api/jobs/{job_id}/download
```

## Status Possiveis Do Job

Status usados atualmente ou previstos pelo fluxo:

- `UPLOADED`: arquivo recebido.
- `SENT_TO_N8N`: backend enviou o job ao n8n.
- `N8N_ERROR`: arquivo salvo, mas chamada ao n8n falhou.
- `ANALYZING`: worker analisando o arquivo.
- `GENERATING_SCRIPT`: IA gerando script/manual/requirements.
- `VALIDATING_SCRIPT`: backend/n8n validando resposta e seguranca.
- `COMPLETED`: job finalizado com sucesso.
- `FAILED`: job falhou.

Observacao: alguns status intermediarios dependem do workflow n8n ser configurado para envia-los/usa-los.

## Login E Historico

O frontend exige login por nome de usuario e senha. Para o MVP local, o cadastro e feito na propria tela inicial.

No cadastro, o usuario tambem pode informar dados adicionais de perfil:

- nome completo;
- e-mail;
- organizacao;
- funcao.

Depois do login:

- uploads usam o usuario autenticado;
- `GET /api/jobs` retorna apenas o historico do usuario logado;
- `GET /api/jobs/{job_id}` e download retornam `404` se o job pertencer a outro usuario;
- callbacks do n8n continuam localizando o job por `job_id`.
- a tela `Dados do usuario` exibe informacoes de cadastro e um resumo dos processamentos do usuario.
- os dados adicionais de perfil podem ser alterados pela propria tela `Dados do usuario`.

Endpoints principais:

```bash
POST /api/auth/register
POST /api/auth/login
GET /api/auth/me
PATCH /api/auth/me
POST /api/auth/logout
```

## Estrutura De Pastas

```text
DataFlow/
  apps/
    backend/
      alembic/
      app/
        api/
        core/
        db/
        models/
        schemas/
        services/
      scripts/
      tests/
      alembic.ini
      requirements.txt
      requirements-dev.txt
    frontend/
      src/app/
      package.json
      tailwind.config.ts
      tsconfig.json
  services/
    worker/
      app/
        main.py
        profiler.py
        readers.py
        detectors.py
        schemas.py
        script_prompt_builder.py
      requirements.txt
  infra/
    docker-compose.yml
  docs/
    n8n-workflow.md
    payloads.md
  shared/
    schemas/
      generated_script_response.schema.json
  storage/
  .env.example
  .gitignore
  README.md
```

## Problemas Comuns E Solucoes

### `npm` bloqueado no PowerShell

Use:

```bash
npm.cmd install
npm.cmd run dev
```

### Backend nao conecta no banco

Verifique se o Postgres esta rodando:

```bash
docker ps
```

Confira `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER` e `POSTGRES_PASSWORD` no `.env`.

### Acessar PostgreSQL pelo navegador

Use o pgAdmin:

```text
http://localhost:5050
```

Login local padrao:

```text
Email: admin@local.dev
Senha: admin123
```

O servidor `DataFlow PostgreSQL` ja fica pre-cadastrado. Ao conectar, use a senha do banco:

```text
app_password
```

### Migration falha

Rode o comando a partir de `apps/backend`:

```bash
alembic upgrade head
```

### MinIO retorna erro no upload

Verifique:

- MinIO rodando em `http://localhost:9000`
- Console em `http://localhost:9001`
- bucket `data-generator`
- variaveis `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`, `MINIO_BUCKET`

O compose possui um container one-shot para criar o bucket automaticamente.

### n8n retorna erro ou nao recebe job

Verifique:

- workflow ativo
- `N8N_WEBHOOK_URL`
- header `x-webhook-secret`
- mesmo valor de `N8N_WEBHOOK_SECRET` no backend e no n8n

### Callback retorna 401 ou 403

O header `x-webhook-secret` esta ausente ou incorreto.

### Worker nao consegue baixar arquivo

Verifique se a `file_url` e acessivel a partir do ambiente onde o Worker esta rodando. Em Docker, `localhost` dentro de um container nao aponta para a maquina host.

### Script gerado fica bloqueado

O backend bloqueia scripts com padroes perigosos. Verifique `error_message` do job. Exemplos bloqueados:

- `eval`
- `exec`
- `subprocess`
- `os.system`
- `socket`
- `requests`
- `urllib`
- `shutil.rmtree`
- `pathlib.Path.home`
- `open("/etc/...")`
- `open("C:\\...")`
- `importlib`

### Testes falham por import/configuracao

Rode a partir de `apps/backend`:

```bash
pytest
```

O arquivo `tests/conftest.py` define variaveis fake para testes unitarios.

## Proximas Melhorias

- Criar workflow n8n exportavel depois de validar manualmente a configuracao.
- Adicionar polling automatico no frontend.
- Criar testes de integracao com banco e MinIO.
- Adicionar presigned URLs para downloads privados.
- Persistir artefatos separados no MinIO alem do ZIP.
- Adicionar filtros avancados no historico de jobs.
- Validar JSON da IA contra `shared/schemas/generated_script_response.schema.json` dentro do backend ou worker.
