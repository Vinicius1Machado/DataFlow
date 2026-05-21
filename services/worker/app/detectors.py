from typing import Any

import pandas as pd


MANY_NULLS_THRESHOLD = 0.4
DETECTION_SUCCESS_THRESHOLD = 0.8


def detect_issues(dataframe: pd.DataFrame, null_percentages: dict[str, float]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    issues.extend(_detect_columns_with_outer_spaces(dataframe))
    issues.extend(_detect_possible_date_columns(dataframe))
    issues.extend(_detect_possible_numeric_text_columns(dataframe))
    issues.extend(_detect_many_null_columns(null_percentages))
    return issues


def _detect_columns_with_outer_spaces(dataframe: pd.DataFrame) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    columns = [str(column) for column in dataframe.columns if str(column) != str(column).strip()]

    if columns:
        issues.append(
            {
                "type": "column_name_outer_spaces",
                "severity": "warning",
                "message": "Columns contain leading or trailing spaces.",
                "columns": columns,
            }
        )

    return issues


def _detect_possible_date_columns(dataframe: pd.DataFrame) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []

    for column in dataframe.columns:
        series = dataframe[column]
        if not _is_text_like(series):
            continue

        values = _clean_text_values(series)
        if values.empty:
            continue

        parsed = pd.to_datetime(values, errors="coerce", utc=False)
        success_ratio = float(parsed.notna().mean())
        if success_ratio >= DETECTION_SUCCESS_THRESHOLD:
            issues.append(
                {
                    "type": "possible_date_column",
                    "severity": "info",
                    "message": "Column may contain date values stored as text.",
                    "column": str(column),
                    "confidence": round(success_ratio, 4),
                }
            )

    return issues


def _detect_possible_numeric_text_columns(dataframe: pd.DataFrame) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []

    for column in dataframe.columns:
        series = dataframe[column]
        if not _is_text_like(series):
            continue

        values = _clean_text_values(series).str.replace(",", ".", regex=False)
        if values.empty:
            continue

        parsed = pd.to_numeric(values, errors="coerce")
        success_ratio = float(parsed.notna().mean())
        if success_ratio >= DETECTION_SUCCESS_THRESHOLD:
            issues.append(
                {
                    "type": "possible_numeric_text_column",
                    "severity": "info",
                    "message": "Column may contain numeric values stored as text.",
                    "column": str(column),
                    "confidence": round(success_ratio, 4),
                }
            )

    return issues


def _detect_many_null_columns(null_percentages: dict[str, float]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []

    for column, null_percentage in null_percentages.items():
        if null_percentage >= MANY_NULLS_THRESHOLD:
            issues.append(
                {
                    "type": "many_null_values",
                    "severity": "warning",
                    "message": "Column has a high percentage of null values.",
                    "column": column,
                    "null_percentage": round(null_percentage, 4),
                }
            )

    return issues


def _is_text_like(series: pd.Series) -> bool:
    return pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series)


def _clean_text_values(series: pd.Series) -> pd.Series:
    return series.dropna().astype(str).str.strip().replace("", pd.NA).dropna()
