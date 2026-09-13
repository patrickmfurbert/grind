import subprocess
import tempfile
import time
from pathlib import Path

from ..config import get_settings

COMMANDS = {"python": ["python3"], "javascript": ["node"], "bash": ["bash"]}
EXTENSIONS = {"python": ".py", "javascript": ".js", "bash": ".sh"}


def execute(language: str, code: str) -> dict:
    if language not in COMMANDS:
        return {"output": "", "error": f"Unsupported language: {language}", "execution_time": 0}
    started = time.monotonic()
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / f"main{EXTENSIONS[language]}"
        path.write_text(code)
        try:
            result = subprocess.run(
                [*COMMANDS[language], str(path)], capture_output=True, text=True,
                timeout=get_settings().code_execution_timeout, cwd=directory,
            )
            return {"output": result.stdout, "error": result.stderr, "execution_time": round(time.monotonic() - started, 3)}
        except subprocess.TimeoutExpired:
            return {"output": "", "error": "Execution timed out", "execution_time": round(time.monotonic() - started, 3)}
