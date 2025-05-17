
from typing import Any, Dict, List

import win_checks

def collect_windows_recon() -> Dict[str, Any]:
    data: Dict[str, Any] = {}

    # Core info & virtualization check
    data["os_info"] = win_checks.get_os_version_info()
    # Additional recon
    data["installed_hotfixes"] = win_checks.get_installed_hotfixes()
    data["running_services"] = win_checks.get_running_services()
    data["firewall_profiles"] = win_checks.get_firewall_profiles()
    data["network_interfaces"] = win_checks.get_network_interfaces()
    data["logged_on_users"] = win_checks.get_logged_on_users()
    data["env"] = win_checks.get_environment()

    return data


def flatten(obj: Any, prefix: str = "") -> List[str]:

    items: List[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            items.extend(flatten(v, f"{prefix}{k}."))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            items.extend(flatten(v, f"{prefix}{i}."))
    else:
        # Convert values to safe strings:
        val_str = str(obj).replace("\\", "/").replace("|", "/").replace("\n", "\\n")
        # Remove trailing dot from prefix
        key = prefix[:-1] if prefix.endswith(".") else prefix
        items.append(f"{key}={val_str}")
    return items



def build_continuous_report() -> str:
    recon = collect_windows_recon()
    return "|".join(flatten(recon))

