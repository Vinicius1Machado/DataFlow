import ast
from typing import Any


BLOCKED_IMPORT_ROOTS = {"subprocess", "socket", "requests", "urllib", "importlib"}
BLOCKED_CALLS = {"eval", "exec"}
BLOCKED_ATTRIBUTE_CALLS = {
    "os.system",
    "shutil.rmtree",
    "pathlib.Path.home",
    "subprocess",
    "socket",
    "requests",
    "urllib",
    "importlib",
}


class ScriptSecurityService:
    def validate_script(self, script_code: str) -> dict[str, Any]:
        blocked_patterns: set[str] = set()
        warnings: list[str] = []

        try:
            tree = ast.parse(script_code)
        except SyntaxError:
            return {
                "is_safe": False,
                "blocked_patterns": ["syntax_error"],
                "warnings": ["Script could not be parsed as valid Python."],
            }

        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                blocked_patterns.update(self._blocked_imports(node))

            if isinstance(node, ast.Call):
                blocked_call = self._blocked_call(node)
                if blocked_call:
                    blocked_patterns.add(blocked_call)

        self._append_textual_warnings(script_code, warnings)

        sorted_blocked_patterns = sorted(blocked_patterns)
        return {
            "is_safe": not sorted_blocked_patterns,
            "blocked_patterns": sorted_blocked_patterns,
            "warnings": warnings,
        }

    def _blocked_imports(self, node: ast.Import | ast.ImportFrom) -> set[str]:
        blocked: set[str] = set()

        if isinstance(node, ast.Import):
            module_names = [alias.name for alias in node.names]
        else:
            module_names = [node.module or ""]

        for module_name in module_names:
            root_name = module_name.split(".", 1)[0]
            if root_name in BLOCKED_IMPORT_ROOTS:
                blocked.add(root_name)

        return blocked

    def _blocked_call(self, node: ast.Call) -> str | None:
        call_name = self._call_name(node.func)

        if call_name in BLOCKED_CALLS:
            return call_name

        if call_name == "open":
            return self._blocked_open_call(node)

        for blocked_name in BLOCKED_ATTRIBUTE_CALLS:
            if call_name == blocked_name or call_name.startswith(f"{blocked_name}."):
                return blocked_name

        return None

    def _blocked_open_call(self, node: ast.Call) -> str | None:
        if not node.args:
            return None

        first_arg = node.args[0]
        if not isinstance(first_arg, ast.Constant) or not isinstance(first_arg.value, str):
            return None

        path_value = first_arg.value
        if path_value.startswith("/etc/"):
            return "open(/etc)"
        if path_value.startswith("C:\\"):
            return "open(C:\\)"

        return None

    def _call_name(self, node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id

        if isinstance(node, ast.Attribute):
            parent_name = self._call_name(node.value)
            if parent_name:
                return f"{parent_name}.{node.attr}"
            return node.attr

        if isinstance(node, ast.Call):
            return self._call_name(node.func)

        return ""

    def _append_textual_warnings(self, script_code: str, warnings: list[str]) -> None:
        lowered_script = script_code.lower()
        if "__import__" in lowered_script:
            warnings.append("Script references __import__; review dynamic import behavior manually.")
        if "compile(" in lowered_script:
            warnings.append("Script references compile(); review dynamic code behavior manually.")
