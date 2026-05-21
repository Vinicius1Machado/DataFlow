# Workflow n8n: Gerador de Script Python - Tratamento de Dados

Este documento descreve como montar manualmente no n8n o workflow `Gerador de Script Python - Tratamento de Dados`.

O objetivo do workflow e receber um job criado pelo backend, chamar o Worker Python para perfilar o arquivo, montar um prompt para IA, validar a resposta estruturada e enviar o callback final para o backend.

## Variaveis Esperadas

Configure estes valores no ambiente do n8n ou como credenciais internas do workflow:

```text
N8N_WEBHOOK_SECRET=<mesmo valor do backend>
WORKER_PROFILE_URL=http://worker:8001/profile
BACKEND_CALLBACK_URL=http://backend:8000/api/n8n/callback
```

No cenario Docker Compose, use sempre os nomes dos servicos nas chamadas internas.

## Payload Recebido Do Backend

O backend chama o webhook do n8n com `POST` e o header `x-webhook-secret`.

```json
{
  "job_id": "8fd9283c-5eb5-4f77-87aa-5d3125d1c31d",
  "user_id": "dev-user",
  "file_name": "clientes.csv",
  "file_type": "csv",
  "file_size": 2048,
  "file_url": "http://minio:9000/data-generator/raw/8fd9283c-5eb5-4f77-87aa-5d3125d1c31d/clientes.csv",
  "callback_url": "http://backend:8000/api/n8n/callback"
}
```

## Nos Do Workflow

### 1. Webhook Trigger

Nome do no: `Webhook Trigger`

Configuracao:

- HTTP Method: `POST`
- Path: `data-analysis`
- Authentication: `None`
- Response Mode: `Using Respond to Webhook node`

URL esperada em ambiente local:

```text
http://localhost:5678/webhook/data-analysis
```

Campos usados pelos proximos nos:

```text
{{$json.body.job_id}}
{{$json.body.user_id}}
{{$json.body.file_name}}
{{$json.body.file_type}}
{{$json.body.file_size}}
{{$json.body.file_url}}
{{$json.body.callback_url}}
{{$json.headers["x-webhook-secret"]}}
```

### 2. IF - Validar x-webhook-secret

Nome do no: `IF - Validar x-webhook-secret`

Objetivo: bloquear chamadas sem segredo correto.

Configuracao:

- Type: `String`
- Value 1:

```text
{{$json.headers["x-webhook-secret"]}}
```

- Operation: `Equals`
- Value 2:

```text
{{$env.N8N_WEBHOOK_SECRET}}
```

Fluxos:

- True: continua para o Worker.
- False: vai direto para `Respond to Webhook` com erro `401`.

Resposta sugerida no caminho False:

```json
{
  "ok": false,
  "error": "invalid webhook secret"
}
```

### 3. HTTP Request - Chamar Worker /profile

Nome do no: `HTTP Request - Chamar Worker /profile`

Configuracao:

- Method: `POST`
- URL:

```text
{{$env.WORKER_PROFILE_URL || "http://worker:8001/profile"}}
```

- Send Body: `JSON`
- Body:

```json
{
  "job_id": "={{$json.body.job_id}}",
  "file_url": "={{$json.body.file_url}}",
  "file_type": "={{$json.body.file_type}}"
}
```

Resposta esperada do Worker:

```json
{
  "job_id": "8fd9283c-5eb5-4f77-87aa-5d3125d1c31d",
  "analysis": {
    "rows": 120,
    "columns": 5,
    "schema": [
      {
        "name": "idade",
        "dtype": "object"
      }
    ],
    "issues": [
      {
        "type": "possible_numeric_text_column",
        "severity": "info",
        "column": "idade"
      }
    ],
    "sample": [
      {
        "idade": "29"
      }
    ]
  }
}
```

### 4. Code - Montar prompt para IA

Nome do no: `Code - Montar prompt para IA`

Objetivo: montar um prompt deterministico a partir da analise.

Modo: `Run Once for Each Item`

Codigo sugerido:

```javascript
const analysis = $json.analysis;
const fileType = $node["Webhook Trigger"].json.body.file_type;

const prompt = `
Voce e uma IA geradora de codigo Python para tratamento de dados.

Responda exclusivamente em JSON valido.

Gere:
1. script_tratamento.py
2. README.md
3. requirements.txt
4. lista de inconsistencias tratadas

Regras:
- O script deve aceitar --input e --output.
- Deve suportar CSV, Parquet, JSON e XML.
- Deve usar pandas.
- Deve conter logging e tratamento de excecoes.
- Deve incluir read_file, clean_dataframe, write_file e main.
- Nao pode usar eval, exec, subprocess, os.system, socket, requests ou chamadas externas.
- Nao pode apagar colunas sem justificar.
- Deve preservar formato de saida quando possivel.
- Deve comentar os principais tratamentos.

Tipo do arquivo: ${fileType}
Analise:
${JSON.stringify(analysis, null, 2)}

Retorne exatamente:
{
  "script_name": "script_tratamento.py",
  "script_code": "...",
  "manual_name": "README.md",
  "manual_content": "...",
  "requirements_txt": "...",
  "detected_issues": [],
  "execution_command": "...",
  "output_format": "${fileType}",
  "confidence_score": 0.0
}
`;

return [
  {
    json: {
      job_id: $json.job_id,
      analysis,
      prompt
    }
  }
];
```

Observacao: o worker tambem possui um builder equivalente em `services/worker/app/script_prompt_builder.py`, que pode ser usado como referencia para manter o prompt alinhado.

### 5. AI Agent ou HTTP Request para provider de IA

Nome do no: `AI Agent ou HTTP Request para provider de IA`

Opcao A: AI Agent

- System prompt: instrua a IA a responder apenas JSON valido.
- User message:

```text
{{$json.prompt}}
```

Opcao B: HTTP Request para provider de IA

- Method: `POST`
- URL: endpoint do provider escolhido.
- Headers: configure credenciais pelo mecanismo seguro do n8n, nunca hardcoded.
- Body: envie o prompt e solicite resposta JSON.

Requisito importante: a resposta final deve ser compatível com `shared/schemas/generated_script_response.schema.json`.

### 6. Structured Output Parser para validar JSON

Nome do no: `Structured Output Parser para validar JSON`

Objetivo: garantir que a resposta da IA tenha os campos esperados.

Schema esperado:

```json
{
  "script_name": "script_tratamento.py",
  "script_code": "string",
  "manual_name": "README.md",
  "manual_content": "string",
  "requirements_txt": "string",
  "detected_issues": [],
  "execution_command": "string",
  "output_format": "csv",
  "confidence_score": 0.8
}
```

Use como referencia o arquivo:

```text
shared/schemas/generated_script_response.schema.json
```

Se o parser falhar, direcione para um callback com `status: "FAILED"` e `error_message`.

### 7. Code - Montar callback

Nome do no: `Code - Montar callback`

Objetivo: converter a resposta validada no contrato aceito pelo backend.

Codigo sugerido:

```javascript
const backendPayload = $node["Webhook Trigger"].json.body;
const workerResult = $node["HTTP Request - Chamar Worker /profile"].json;
const generated = $json;

return [
  {
    json: {
      callback_url: backendPayload.callback_url,
      job_id: backendPayload.job_id,
      status: "COMPLETED",
      analysis: workerResult.analysis,
      script_code: generated.script_code,
      manual_content: generated.manual_content,
      requirements_txt: generated.requirements_txt,
      result_package_url: null,
      error_message: null
    }
  }
];
```

Payload esperado pelo backend:

```json
{
  "job_id": "8fd9283c-5eb5-4f77-87aa-5d3125d1c31d",
  "status": "COMPLETED",
  "analysis": {
    "rows": 120,
    "columns": 5,
    "issues": []
  },
  "script_code": "import argparse\nimport logging\n...",
  "manual_content": "# Como usar\n...",
  "requirements_txt": "pandas\npyarrow\nlxml\n",
  "result_package_url": null,
  "error_message": null
}
```

### 8. HTTP Request - Enviar callback para backend

Nome do no: `HTTP Request - Enviar callback para backend`

Configuracao:

- Method: `POST`
- URL:

```text
{{$json.callback_url || $env.BACKEND_CALLBACK_URL}}
```

- Send Headers:

```text
x-webhook-secret: {{$env.N8N_WEBHOOK_SECRET}}
Content-Type: application/json
```

- Send Body: `JSON`
- Body:

```json
{
  "job_id": "={{$json.job_id}}",
  "status": "={{$json.status}}",
  "analysis": "={{$json.analysis}}",
  "script_code": "={{$json.script_code}}",
  "manual_content": "={{$json.manual_content}}",
  "requirements_txt": "={{$json.requirements_txt}}",
  "result_package_url": "={{$json.result_package_url}}",
  "error_message": "={{$json.error_message}}"
}
```

### 9. Respond to Webhook

Nome do no: `Respond to Webhook`

Configuracao no caminho de sucesso:

- Response Code: `200`
- Body:

```json
{
  "ok": true,
  "job_id": "={{$node['Webhook Trigger'].json.body.job_id}}",
  "message": "Job accepted by n8n"
}
```

Configuracao no caminho de erro:

- Response Code: `500` ou `401`, conforme o caso.
- Body:

```json
{
  "ok": false,
  "job_id": "={{$node['Webhook Trigger'].json.body.job_id}}",
  "error": "Workflow failed"
}
```

## Como Testar O Webhook

Com n8n rodando em `localhost:5678`, use:

```bash
curl -X POST http://localhost:5678/webhook/data-analysis ^
  -H "Content-Type: application/json" ^
  -H "x-webhook-secret: seu-segredo-local" ^
  -d "{\"job_id\":\"8fd9283c-5eb5-4f77-87aa-5d3125d1c31d\",\"user_id\":\"dev-user\",\"file_name\":\"clientes.csv\",\"file_type\":\"csv\",\"file_size\":2048,\"file_url\":\"http://minio:9000/data-generator/raw/8fd9283c-5eb5-4f77-87aa-5d3125d1c31d/clientes.csv\",\"callback_url\":\"http://backend:8000/api/n8n/callback\"}"
```

Para testar o Worker isoladamente:

```bash
curl -X POST http://localhost:8001/profile ^
  -H "Content-Type: application/json" ^
  -d "{\"job_id\":\"8fd9283c-5eb5-4f77-87aa-5d3125d1c31d\",\"file_url\":\"http://localhost:9000/data-generator/raw/8fd9283c-5eb5-4f77-87aa-5d3125d1c31d/clientes.csv\",\"file_type\":\"csv\"}"
```

Para testar o callback isoladamente:

```bash
curl -X POST http://localhost:8000/api/n8n/callback ^
  -H "Content-Type: application/json" ^
  -H "x-webhook-secret: seu-segredo-local" ^
  -d "{\"job_id\":\"8fd9283c-5eb5-4f77-87aa-5d3125d1c31d\",\"status\":\"COMPLETED\",\"analysis\":{\"rows\":10,\"columns\":3,\"issues\":[]},\"script_code\":\"print('ok')\",\"manual_content\":\"# Uso\",\"requirements_txt\":\"pandas\",\"result_package_url\":null,\"error_message\":null}"
```

## Debug De Erros Comuns

### 401 ou 403 no backend callback

Causa comum: header `x-webhook-secret` ausente ou diferente do valor configurado no backend.

Verifique:

```text
N8N_WEBHOOK_SECRET
```

O mesmo valor deve existir no backend e no n8n.

### Worker retorna erro 422

Causas comuns:

- `file_url` inacessivel para o container do Worker.
- Arquivo vazio.
- `file_type` fora de `csv`, `parquet`, `json`, `xml`.
- Arquivo com extensao correta, mas conteudo invalido.

Se tudo roda em Docker, prefira URLs acessiveis entre containers, nao necessariamente `localhost`.

### MinIO retorna 403 ou 404

Causas comuns:

- Bucket `data-generator` nao existe.
- URL publica do MinIO nao esta acessivel para o Worker.
- Objeto salvo em chave diferente da enviada no payload.

Confirme o objeto no console:

```text
http://localhost:9001
```

### IA retorna texto fora de JSON

Use o Structured Output Parser e reforce no prompt:

```text
Responda exclusivamente em JSON valido. Nao use Markdown.
```

### Parser estruturado falha

Compare a resposta da IA com:

```text
shared/schemas/generated_script_response.schema.json
```

Campos obrigatorios ausentes devem ser tratados como falha e enviados ao backend com:

```json
{
  "status": "FAILED",
  "error_message": "AI response did not match expected schema"
}
```
