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
            check=True
        )
        return True, result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return False, e.stderr.strip()


def run_with_retry(
    code: str,
    max_retries: int = 1,
    post_url: str = error_endpoint,
) -> Tuple[bool, str]:
    """
    Runs the Python code using subprocess. On failure, POST error and retry.
    On success after retry, perform another task.
    """
    success, output = run_code(code)
    attempts_left = max_retries

    while not success and attempts_left > 0:
        # 1. Report failure
        try:
            requests.post(post_url, json={"payload": code, "error_log": output})
        except Exception as post_exc:
            print(f"[Warning] Could not report failure: {post_exc}")

        # 2. Retry
        attempts_left -= 1
        success, output = run_code(code)

        # 3. Post-success task
        if success:
            post_success_side_effect(output)

    return success, output


def post_success_side_effect(result: str):
    """
    Perform any task you want after a successful retry.
    """
    print(f"[INFO] Code succeeded after retry. Result: {result}")
