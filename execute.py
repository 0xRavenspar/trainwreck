import subprocess
import requests
from typing import Tuple

error_endpoint = "https://22fd-14-99-167-142.ngrok-free.app/error"

def run_code(code: str) -> Tuple[bool, str]:
    """
    Executes Python code using subprocess, without writing to disk.
    Returns (success, output or error).
    """
    try:
        result = subprocess.run(
            ["python", "-c", code],
            capture_output=True,
            text=True,
            check=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        post_success_side_effect(result.stdout.strip())
        return True, result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return False, e.stderr.strip()


def post_success_side_effect(result: str):
    """
    Perform any task you want after a successful retry.
    """
    print(f"[INFO] Code succeeded after retry. Result: {result}")
