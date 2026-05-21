import tempfile
from pathlib import Path

import httpx
import pandas as pd


SUPPORTED_FILE_TYPES = {"csv", "parquet", "json", "xml"}
MAX_DOWNLOAD_SIZE_BYTES = 100 * 1024 * 1024
DOWNLOAD_CHUNK_SIZE_BYTES = 1024 * 1024


class ReaderError(Exception):
    pass


def normalize_file_type(file_type: str) -> str:
    normalized = file_type.lower().strip().lstrip(".")
    if normalized not in SUPPORTED_FILE_TYPES:
        supported = ", ".join(sorted(SUPPORTED_FILE_TYPES))
        raise ReaderError(f"Unsupported file type '{file_type}'. Supported types: {supported}.")
    return normalized


def download_to_temp_file(file_url: str, file_type: str) -> str:
    normalized_type = normalize_file_type(file_type)
    temp_file = tempfile.NamedTemporaryFile(prefix="dsg-worker-", suffix=f".{normalized_type}", delete=False)
    temp_path = temp_file.name
    downloaded_size = 0

    try:
        with temp_file:
            with httpx.stream("GET", file_url, timeout=httpx.Timeout(60.0, connect=10.0)) as response:
                response.raise_for_status()
                for chunk in response.iter_bytes(chunk_size=DOWNLOAD_CHUNK_SIZE_BYTES):
                    if not chunk:
                        continue
                    downloaded_size += len(chunk)
                    if downloaded_size > MAX_DOWNLOAD_SIZE_BYTES:
                        raise ReaderError("Downloaded file exceeds the maximum worker limit of 100 MB.")
                    temp_file.write(chunk)
    except ReaderError:
        Path(temp_path).unlink(missing_ok=True)
        raise
    except httpx.TimeoutException as exc:
        Path(temp_path).unlink(missing_ok=True)
        raise ReaderError("Timed out while downloading the source file.") from exc
    except httpx.HTTPStatusError as exc:
        Path(temp_path).unlink(missing_ok=True)
        raise ReaderError(f"Source file download failed with HTTP {exc.response.status_code}.") from exc
    except httpx.RequestError as exc:
        Path(temp_path).unlink(missing_ok=True)
        raise ReaderError("Could not download the source file.") from exc
    except Exception as exc:
        Path(temp_path).unlink(missing_ok=True)
        raise ReaderError("Unexpected error while downloading the source file.") from exc

    if downloaded_size == 0:
        Path(temp_path).unlink(missing_ok=True)
        raise ReaderError("Downloaded file is empty.")

    return temp_path


def read_dataframe(file_path: str, file_type: str) -> pd.DataFrame:
    normalized_type = normalize_file_type(file_type)

    try:
        if normalized_type == "csv":
            dataframe = pd.read_csv(file_path, sep=None, engine="python")
        elif normalized_type == "parquet":
            dataframe = pd.read_parquet(file_path)
        elif normalized_type == "json":
            dataframe = pd.read_json(file_path)
        elif normalized_type == "xml":
            dataframe = pd.read_xml(file_path)
        else:
            raise ReaderError(f"Unsupported file type '{file_type}'.")
    except ValueError as exc:
        raise ReaderError(f"Could not read {normalized_type.upper()} file.") from exc
    except Exception as exc:
        raise ReaderError(f"Unexpected error while reading {normalized_type.upper()} file.") from exc

    if not isinstance(dataframe, pd.DataFrame):
        dataframe = pd.DataFrame(dataframe)

    return dataframe
