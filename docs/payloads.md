# Payloads Do Data Script Generator

Este arquivo documenta os payloads trocados entre backend, n8n e worker.

## 1. Payload Backend -> n8n

Enviado pelo backend para o webhook configurado em `N8N_WEBHOOK_URL`.

Headers:

```text
Content-Type: application/json
x-webhook-secret: <N8N_WEBHOOK_SECRET>
```

Body:

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

## 2. Payload n8n -> Worker

Enviado pelo n8n para `POST /profile` no Worker.

```json
{
  "job_id": "8fd9283c-5eb5-4f77-87aa-5d3125d1c31d",
  "file_url": "http://minio:9000/data-generator/raw/8fd9283c-5eb5-4f77-87aa-5d3125d1c31d/clientes.csv",
  "file_type": "csv"
}
```

## 3. Payload Worker -> n8n

Resposta do Worker para o n8n.

```json
{
  "job_id": "8fd9283c-5eb5-4f77-87aa-5d3125d1c31d",
  "analysis": {
    "rows": 120,
    "columns": 5,
    "schema": [
      {
        "name": "nome",
        "dtype": "object"
      },
      {
        "name": "idade",
        "dtype": "object"
      }
    ],
    "null_counts": {
      "nome": 0,
      "idade": 3
    },
    "null_percentages": {
      "nome": 0,
      "idade": 0.025
    },
    "unique_counts": {
      "nome": 118,
      "idade": 42
    },
    "duplicate_rows": 2,
    "empty_rows": 0,
    "issues": [
      {
        "type": "possible_numeric_text_column",
        "severity": "info",
        "message": "Column may contain numeric values stored as text.",
        "column": "idade",
        "confidence": 0.98
      }
    ],
    "sample": [
      {
        "nome": "Ana",
        "idade": "29"
      }
    ]
  }
}
```

## 4. Payload n8n -> Backend Callback

Enviado pelo n8n para `POST /api/n8n/callback`.

Headers:

```text
Content-Type: application/json
x-webhook-secret: <N8N_WEBHOOK_SECRET>
```

Body de sucesso:

```json
{
  "job_id": "8fd9283c-5eb5-4f77-87aa-5d3125d1c31d",
  "status": "COMPLETED",
  "analysis": {
    "rows": 120,
    "columns": 5,
    "issues": [
      {
        "type": "possible_numeric_text_column",
        "severity": "info",
        "column": "idade"
      }
    ]
  },
  "script_code": "import argparse\nimport logging\nimport pandas as pd\n\n...",
  "manual_content": "# Como usar\n\nExecute o script com --input e --output.",
  "requirements_txt": "pandas\npyarrow\nlxml\n",
  "result_package_url": null,
  "error_message": null
}
```

Body de falha:

```json
{
  "job_id": "8fd9283c-5eb5-4f77-87aa-5d3125d1c31d",
  "status": "FAILED",
  "analysis": null,
  "script_code": null,
  "manual_content": null,
  "requirements_txt": null,
  "result_package_url": null,
  "error_message": "AI response did not match expected schema"
}
```
