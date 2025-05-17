# Modified basic_checks.py
import os
import platform
import subprocess
import re

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

def get_os_version_info():
    os_info = {
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "architecture": platform.machine(),
        "processor": platform.processor(),
        "hostname": platform.node()
    }

    if platform.system() == "Windows":
        try:
            ver_output = subprocess.check_output("ver", shell=True, text=True, stderr=subprocess.DEVNULL)
            os_info["windows_full_version"] = ver_output.strip()
        except Exception as e:
            os_info["windows_full_version_error"] = str(e)

    elif platform.system() == "Darwin":
        try:
            sw_vers_output = subprocess.check_output(["sw_vers"], text=True, stderr=subprocess.DEVNULL)
            mac_info = {}
            for line in sw_vers_output.strip().split('\n'):
                k, v = line.split(":", 1)
                mac_info[k.strip()] = v.strip()
            os_info["mac_info"] = mac_info
        except Exception as e:
            os_info["mac_info_error"] = str(e)

    elif platform.system() == "Linux":
        try:
            with open("/etc/os-release", "r") as f:
                os_release_info = {}
                for line in f:
                    if '=' in line:
                        key, value = line.strip().split('=', 1)
                        os_release_info[key] = value.strip('"')
                os_info["distribution"] = {
                    "pretty_name": os_release_info.get("PRETTY_NAME", "N/A"),
                    "id": os_release_info.get("ID", "N/A"),
                    "version_id": os_release_info.get("VERSION_ID", "N/A")
                }
        except Exception as e:
            os_info["linux_info_error"] = str(e)

    return os_info

def list_installed_applications():
    apps = []
    system = platform.system()

    if system == "Windows":
        try:
            output = subprocess.check_output("wmic product get name, version", shell=True, text=True, stderr=subprocess.PIPE, timeout=30)
            lines = output.strip().split('\n')[1:]
            for line in lines:
                parts = re.split(r'\s{2,}', line.strip())
                if parts:
                    app_name = parts[0].strip()
                    app_version = parts[-1].strip() if len(parts) > 1 else "N/A"
                    apps.append(f"{app_name} (Version: {app_version})")
        except Exception:
            pass

        try:
            output = subprocess.check_output("winget list", shell=True, text=True, stderr=subprocess.PIPE, timeout=30)
            lines = output.strip().split('\n')[2:]
            for line in lines:
                if line.strip():
                    parts = re.split(r'\s{2,}', line.strip())
                    apps.append(f"{parts[0]} (winget)")
        except Exception:
            pass

    elif system == "Darwin":
        app_paths = ["/Applications", os.path.expanduser("~/Applications")]
        for app_dir in app_paths:
            try:
                for item in os.listdir(app_dir):
                    if item.endswith(".app"):
                        apps.append(os.path.join(app_dir, item))
            except Exception:
                pass

    elif system == "Linux":
        try:
            output = subprocess.check_output("dpkg-query -W -f='${Package} (${Version})\n'", shell=True, text=True)
            apps.extend(output.strip().split('\n'))
        except Exception:
            pass

        try:
            output = subprocess.check_output("rpm -qa --qf '%{NAME}-%{VERSION}.%{ARCH}\n'", shell=True, text=True)
            apps.extend(output.strip().split('\n'))
        except Exception:
            pass

        try:
            output = subprocess.check_output("pacman -Q", shell=True, text=True)
            apps.extend(output.strip().split('\n'))
        except Exception:
            pass

    return sorted(list(set(apps)))

def check_virtual_machine():
    is_vm = False
    indicators = []
    hypervisor = "Unknown or Physical"

    if PSUTIL_AVAILABLE:
        running_processes = {p.info['name'].lower() for p in psutil.process_iter(['name'])}
        for hint in ["vbox", "vmware", "qemu", "hyper-v", "kvm", "xen"]:
            for name in running_processes:
                if hint in name:
                    is_vm = True
                    indicators.append(f"Matched {hint} in process: {name}")

    if platform.system() == "Linux":
        try:
            output = subprocess.check_output("systemd-detect-virt", shell=True, text=True).strip()
            if output and output != "none":
                is_vm = True
                hypervisor = output
                indicators.append(f"systemd-detect-virt: {output}")
        except Exception:
            pass

    return is_vm, hypervisor
