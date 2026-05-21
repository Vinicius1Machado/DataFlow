from uuid import uuid4

from app.schemas.job import DataJobCreate, N8NCallbackPayload


def test_data_job_create_accepts_valid_payload() -> None:
    payload = DataJobCreate(
        user_id="dev-user",
        job_name="Tratamento clientes",
        file_name="clientes.csv",
        file_fingerprint="a" * 64,
        file_type="csv",
        file_size=1024,
        raw_file_url="http://localhost:9000/data-generator/raw/job/clientes.csv",
    )

    assert payload.user_id == "dev-user"
    assert payload.job_name == "Tratamento clientes"
    assert payload.status == "pending"
    assert payload.file_type == "csv"


def test_n8n_callback_payload_accepts_valid_payload() -> None:
    job_id = uuid4()

    payload = N8NCallbackPayload(
        job_id=job_id,
        status="COMPLETED",
        analysis={"rows": 10, "columns": 3, "issues": []},
        script_code="print('ok')",
        manual_content="# Uso",
        requirements_txt="pandas",
        result_package_url="http://localhost:9000/data-generator/results/job/resultado.zip",
    )

    assert payload.job_id == job_id
    assert payload.status == "COMPLETED"
    assert payload.analysis == {"rows": 10, "columns": 3, "issues": []}
