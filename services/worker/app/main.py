from pathlib import Path

from fastapi import FastAPI, HTTPException, status

from app.profiler import profile_dataframe
from app.readers import ReaderError, download_to_temp_file, read_dataframe
from app.schemas import ProfileRequest, ProfileResponse


app = FastAPI(title="Data Script Generator Worker", version="0.1.0")


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/profile", response_model=ProfileResponse)
def profile_file(payload: ProfileRequest) -> ProfileResponse:
    temp_path: str | None = None

    try:
        temp_path = download_to_temp_file(payload.file_url, payload.file_type)
        dataframe = read_dataframe(temp_path, payload.file_type)
        analysis = profile_dataframe(dataframe)
    except ReaderError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected worker profiling error.",
        ) from exc
    finally:
        if temp_path is not None:
            Path(temp_path).unlink(missing_ok=True)

    return ProfileResponse(job_id=payload.job_id, analysis=analysis)
