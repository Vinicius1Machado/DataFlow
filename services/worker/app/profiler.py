import math
from typing import Any

import pandas as pd

from app.detectors import detect_issues


def profile_dataframe(dataframe: pd.DataFrame) -> dict[str, Any]:
    rows = int(len(dataframe))
    columns = int(len(dataframe.columns))
    null_counts = _null_counts(dataframe)
    null_percentages = _null_percentages(dataframe, rows)

    analysis: dict[str, Any] = {
        "rows": rows,
        "columns": columns,
        "schema": _schema(dataframe),
        "null_counts": null_counts,
        "null_percentages": null_percentages,
        "unique_counts": _unique_counts(dataframe),
        "duplicate_rows": _duplicate_rows(dataframe),
        "empty_rows": _empty_rows(dataframe),
        "issues": detect_issues(dataframe, null_percentages),
        "sample": _sample(dataframe),
    }
    return analysis


def _schema(dataframe: pd.DataFrame) -> list[dict[str, str]]:
    return [{"name": str(column), "dtype": str(dtype)} for column, dtype in dataframe.dtypes.items()]


def _null_counts(dataframe: pd.DataFrame) -> dict[str, int]:
    return {str(column): int(value) for column, value in dataframe.isna().sum().items()}


def _null_percentages(dataframe: pd.DataFrame, rows: int) -> dict[str, float]:
    if rows == 0:
        return {str(column): 0.0 for column in dataframe.columns}

    return {str(column): round(float(value) / rows, 4) for column, value in dataframe.isna().sum().items()}


def _unique_counts(dataframe: pd.DataFrame) -> dict[str, int]:
    counts: dict[str, int] = {}
    for column in dataframe.columns:
        series = dataframe[column]
        try:
            counts[str(column)] = int(series.nunique(dropna=True))
        except TypeError:
            counts[str(column)] = int(series.astype(str).nunique(dropna=True))
    return counts


def _duplicate_rows(dataframe: pd.DataFrame) -> int:
    try:
        return int(dataframe.duplicated().sum())
    except TypeError:
        return int(dataframe.astype(str).duplicated().sum())


def _empty_rows(dataframe: pd.DataFrame) -> int:
    if dataframe.empty:
        return 0
    return int(dataframe.isna().all(axis=1).sum())


def _sample(dataframe: pd.DataFrame) -> list[dict[str, Any]]:
    sample_dataframe = dataframe.head(20)
    rows: list[dict[str, Any]] = []

    for row in sample_dataframe.to_dict(orient="records"):
        rows.append({str(key): _to_json_safe(value) for key, value in row.items()})

    return rows


def _to_json_safe(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, dict):
        return {str(key): _to_json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_json_safe(item) for item in value]
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    if isinstance(value, (str, int, float, bool)):
        return value
    if hasattr(value, "item"):
        try:
            return _to_json_safe(value.item())
        except (TypeError, ValueError):
            pass
    return str(value)
