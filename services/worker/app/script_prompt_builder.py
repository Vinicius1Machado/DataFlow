import json
from typing import Any, Mapping


SUPPORTED_FILE_TYPES = {"csv", "parquet", "json", "xml"}
FORBIDDEN_CODE_PATTERNS = ["eval", "exec", "subprocess", "os.system", "socket", "requests"]


class ScriptPromptBuilderError(ValueError):
    pass


def build_script_generation_prompt(analysis_json: Mapping[str, Any], file_type: str) -> str:
    normalized_file_type = _normalize_file_type(file_type)
    compact_analysis = json.dumps(analysis_json, ensure_ascii=True, sort_keys=True, default=str, indent=2)
    forbidden_patterns = ", ".join(FORBIDDEN_CODE_PATTERNS)

    return f"""Voce e uma IA geradora de codigo Python para tratamento de dados.

Responda exclusivamente com JSON valido, sem Markdown, sem comentarios fora do JSON e sem blocos ```json.

Objetivo:
Gerar um pacote de tratamento para um arquivo do tipo {normalized_file_type.upper()} contendo:
1. script_tratamento.py
2. README.md
3. requirements.txt
4. lista de inconsistencias tratadas

Analise tecnica do arquivo:
{compact_analysis}

Regras obrigatorias para o script Python:
- Deve aceitar argumentos de linha de comando --input e --output usando argparse.
- Deve suportar leitura e escrita de CSV, Parquet, JSON e XML.
- Deve preservar o formato de saida quando possivel, usando o tipo do arquivo de entrada quando aplicavel.
- Deve usar pandas como biblioteca principal.
- Deve conter logging com mensagens de progresso e erro.
- Deve conter tratamento de excecoes claro, com mensagens uteis.
- Deve incluir as funcoes read_file, clean_dataframe, write_file e main.
- Nao pode usar: {forbidden_patterns}.
- Nao pode executar codigo gerado dinamicamente.
- Nao pode fazer chamadas externas de rede.
- Nao pode apagar colunas sem justificar no README.md e em detected_issues.
- Deve comentar os principais tratamentos diretamente no codigo.
- Deve manter os dados originais tanto quanto possivel e aplicar tratamentos conservadores.

Tratamentos esperados:
- Use a analise para decidir tratamentos para nulos, duplicadas, linhas vazias, nomes de colunas, datas e numeros armazenados como texto.
- Explique cada decisao em detected_issues.
- Quando a analise nao for suficiente para uma correcao segura, apenas registre a inconsistencia e evite alterar agressivamente.

Formato JSON obrigatorio da resposta:
{{
  "script_name": "script_tratamento.py",
  "script_code": "codigo Python completo como string",
  "manual_name": "README.md",
  "manual_content": "manual de uso do script como string",
  "requirements_txt": "dependencias como texto, uma por linha",
  "detected_issues": [
    {{
      "type": "tipo_da_inconsistencia",
      "description": "descricao clara",
      "columns": ["coluna_exemplo"],
      "treatment": "tratamento aplicado ou justificativa para nao aplicar",
      "severity": "info|warning|error"
    }}
  ],
  "execution_command": "python script_tratamento.py --input caminho/entrada.{normalized_file_type} --output caminho/saida.{normalized_file_type}",
  "output_format": "{normalized_file_type}",
  "confidence_score": 0.0
}}

Regras para confidence_score:
- Use numero entre 0 e 1.
- Reduza a confianca quando houver muitas ambiguidades na analise.
"""


def _normalize_file_type(file_type: str) -> str:
    normalized = file_type.lower().strip().lstrip(".")
    if normalized not in SUPPORTED_FILE_TYPES:
        supported = ", ".join(sorted(SUPPORTED_FILE_TYPES))
        raise ScriptPromptBuilderError(f"Unsupported file type '{file_type}'. Supported types: {supported}.")
    return normalized
