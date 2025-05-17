# main.py

import json
from net_env import get_network_environment
from basic_checks import get_os_version_info, list_installed_applications, check_virtual_machine
from security_processes import get_security_related_processes

def run_system_diagnostics():
    # Network environment info
    net_env = get_network_environment()

    # OS info
    import io
    import sys

    def capture_output(func):
        captured = io.StringIO()
        sys_stdout = sys.stdout
        sys.stdout = captured
        try:
            func()
        finally:
            sys.stdout = sys_stdout
        return captured.getvalue().strip()

    os_info = capture_output(get_os_version_info)
    installed_apps_output = capture_output(list_installed_applications)

    # Virtual machine detection
    is_vm, hypervisor = check_virtual_machine()

    # Security processes
    security_procs = get_security_related_processes()

    result = {
        "network_environment": net_env,
        "os_info": os_info,
        "installed_applications": installed_apps_output,
        "vm_detection": {
            "is_vm": is_vm,
            "hypervisor": hypervisor
        },
        "security_processes": security_procs
    }

    return result

if __name__ == "__main__":
    data = run_system_diagnostics()

    # Print as JSON (or send via POST)
    print(json.dumps(data, indent=2))
