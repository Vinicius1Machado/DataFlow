# Docker Compose Setup

## Cenario A: tudo dentro do Docker Compose

Neste cenario, frontend, backend, worker, n8n, PostgreSQL, MinIO e Redis rodam na mesma rede interna criada pelo Docker Compose.

Use `localhost` apenas quando a chamada parte do navegador ou da sua maquina. Dentro dos containers, use o nome do servico.

URLs internas obrigatorias para o workflow n8n:

```text
WORKER_PROFILE_URL=http://worker:8001/profile
BACKEND_CALLBACK_URL=http://backend:8000/api/n8n/callback
N8N_WEBHOOK_URL=http://n8n:5678/webhook/data-analysis
```

URLs externas para acessar pelo navegador:

```text
Frontend: http://localhost:3000
Backend: http://localhost:8000
Worker: http://localhost:8001
n8n: http://localhost:5678
MinIO API: http://localhost:9000
MinIO Console: http://localhost:9001
PostgreSQL: localhost:5432
```

## Configurar `.env`

Crie o arquivo local a partir do exemplo:

```bash
cp .env.example .env
```

No PowerShell:

```powershell
Copy-Item .env.example .env
```

Troque pelo menos:

```env
N8N_WEBHOOK_SECRET=troque_este_segredo
OPENAI_API_KEY=troque_esta_chave
```

Para desenvolvimento local, o Compose ja possui defaults seguros apenas para ambiente de maquina local. Nao use esses valores em producao.

## Subir todos os servicos

Execute a partir da raiz do projeto:

```bash
cd infra
docker compose up -d --build
docker compose ps
```

O backend executa `alembic upgrade head` antes de iniciar o Uvicorn, criando a tabela `data_jobs` quando o banco estiver pronto.

## Ver logs

```bash
docker compose logs -f backend
docker compose logs -f worker
docker compose logs -f n8n
```

## Healthcheck do backend

Pelo host:

```bash
curl http://localhost:8000/health
```

De dentro do container n8n:

```bash
docker compose exec n8n sh -lc 'wget -qO- http://backend:8000/health'
```

## Healthcheck do worker

Pelo host:

```bash
curl http://localhost:8001/health
```

De dentro do container n8n:

```bash
docker compose exec n8n sh -lc 'wget -qO- http://worker:8001/health'
```

Se `wget` nao existir no container n8n, tente:

```bash
docker compose exec n8n sh -lc 'curl -fsS http://worker:8001/health'
docker compose exec n8n sh -lc 'curl -fsS http://backend:8000/health'
```

Ou usando Node.js, que faz parte da imagem do n8n:

```bash
docker compose exec n8n node -e "fetch('http://worker:8001/health').then(r => r.text()).then(console.log)"
docker compose exec n8n node -e "fetch('http://backend:8000/health').then(r => r.text()).then(console.log)"
```

## Acessar o n8n

Abra:

```text
http://localhost:5678
```

Credenciais locais padrao:

```text
usuario: admin
senha: admin123
```

Essas credenciais sao apenas para desenvolvimento local.

## Conferir variaveis dentro do n8n

```bash
docker compose exec n8n sh -lc 'printenv | grep -E "N8N_WEBHOOK_SECRET|WORKER_PROFILE_URL|BACKEND_CALLBACK_URL"'
```

O resultado deve mostrar:

```text
WORKER_PROFILE_URL=http://worker:8001/profile
BACKEND_CALLBACK_URL=http://backend:8000/api/n8n/callback
```

O segredo nao deve ser publicado em documentacao ou logs externos.

## Testar comunicacao interna n8n -> worker

```bash
docker compose exec n8n sh -lc 'wget -qO- http://worker:8001/health'
```

Resposta esperada:

```json
{"status":"ok"}
```

## Testar comunicacao interna n8n -> backend

```bash
docker compose exec n8n sh -lc 'wget -qO- http://backend:8000/health'
```

Resposta esperada:

```json
{"status":"ok"}
```

## URLs para usar dentro do workflow n8n

No node `HTTP Request - Chamar Worker /profile`, use:

```text
{{$env.WORKER_PROFILE_URL}}
```

No node `HTTP Request - Enviar callback para backend`, use:

```text
{{$env.BACKEND_CALLBACK_URL}}
```

Ao validar o segredo do webhook, compare o header recebido com:

```text
{{$env.N8N_WEBHOOK_SECRET}}
```

O backend chama o webhook do n8n por:

```text
http://n8n:5678/webhook/data-analysis
```

## Observacoes de rede

- `NEXT_PUBLIC_API_URL=http://localhost:8000` porque o frontend chama o backend a partir do navegador.
- `MINIO_PUBLIC_ENDPOINT=http://localhost:9000` e salvo no job para acesso externo/local.
- `MINIO_WORKER_ENDPOINT=http://minio:9000` e usado no payload enviado ao n8n para o worker baixar arquivos pela rede interna.
- O bucket `data-generator` e criado automaticamente pelo container `minio-create-bucket`.
- O bucket recebe permissao anonima de download apenas para facilitar o MVP local.
