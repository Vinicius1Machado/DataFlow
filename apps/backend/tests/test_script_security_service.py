from app.services.script_security_service import ScriptSecurityService


def test_script_security_service_allows_safe_script() -> None:
    script = """
import argparse
import logging
import pandas as pd

def read_file(path):
    return pd.read_csv(path)
"""

    result = ScriptSecurityService().validate_script(script)

    assert result["is_safe"] is True
    assert result["blocked_patterns"] == []


def test_script_security_service_blocks_eval() -> None:
    script = """
def clean_dataframe(df):
    eval("1 + 1")
    return df
"""

    result = ScriptSecurityService().validate_script(script)

    assert result["is_safe"] is False
    assert "eval" in result["blocked_patterns"]


def test_script_security_service_blocks_subprocess() -> None:
    script = """
import subprocess

def main():
    subprocess.run(["echo", "bad"])
"""

    result = ScriptSecurityService().validate_script(script)

    assert result["is_safe"] is False
    assert "subprocess" in result["blocked_patterns"]
