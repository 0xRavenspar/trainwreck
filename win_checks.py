from __future__ import annotations

import platform
import re
import subprocess
from typing import Dict, List, Tuple

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

###############################################################################
# Generic helpers
###############################################################################

def _run(cmd: str) -> str:
    """Run *cmd* using PowerShell, returning trimmed stdout (suppressing console)."""
    try:
        creation_flags = subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
        return subprocess.check_output(
            ["powershell", "-NoLogo", "-NoProfile", "-Command", cmd],
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=20,
            creationflags=creation_flags,
        ).strip()
    except Exception:
        return ""

###############################################################################
# Core system enumeration (ported from basic_checks.py)
###############################################################################

def get_os_version_info() -> Dict[str, str]:
    os_info: Dict[str, str] = {
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "architecture": platform.machine(),
        "processor": platform.processor(),
        "hostname": platform.node(),
    }

    if platform.system() == "Windows":
        ver_output = _run("ver")
        if ver_output:
            os_info["windows_full_version"] = ver_output
    return os_info


def list_installed_applications() -> List[str]:
    apps: List[str] = []
    # WMIC
    output = _run("wmic product get name, version")
    lines = output.splitlines()[1:] if output else []
    for line in lines:
        parts = re.split(r"\s{2,}", line.strip())
        if parts:
            name = parts[0].strip()
            ver = parts[-1].strip() if len(parts) > 1 else "N/A"
            apps.append(f"{name} (Version: {ver})")
    # winget
    output = _run("winget list")
    lines = output.splitlines()[2:] if output else []
    for line in lines:
        if line.strip():
            parts = re.split(r"\s{2,}", line.strip())
            apps.append(f"{parts[0]} (winget)")
    return sorted(set(apps))


def check_virtual_machine() -> Tuple[bool, str]:
    is_vm = False
    hypervisor = "Physical"
    if PSUTIL_AVAILABLE:
        running = {p.info["name"].lower() for p in psutil.process_iter(["name"]) if p.info["name"]}
        for hint in ["vbox", "vmware", "qemu", "hyper-v", "kvm", "xen"]:
            if any(hint in name for name in running):
                is_vm = True
                hypervisor = hint
                break
    out = _run("systemd-detect-virt")
    if out and out != "none":
        is_vm = True
        hypervisor = out
    return is_vm, hypervisor

###############################################################################
# Windows‑specific additions
###############################################################################

def get_installed_hotfixes() -> List[str]:
    return _run("Get-HotFix | Select-Object -ExpandProperty HotFixID").splitlines()


def get_running_services() -> List[str]:
    return sorted(_run("Get-Service | Where-Object {$_.Status -eq 'Running'} | Select -Expand Name").splitlines())


def get_firewall_profiles():
    import json
    fw = _run("Get-NetFirewallProfile | Select Name,Enabled | ConvertTo-Json")
    try:
        return json.loads(fw) if fw else []
    except json.JSONDecodeError:
        return fw


def get_network_interfaces():
    import json
    nics = _run("Get-NetIPAddress -AddressFamily IPv4 | Select InterfaceAlias,IPAddress | ConvertTo-Json")
    try:
        return json.loads(nics) if nics else []
    except json.JSONDecodeError:
        return nics


def get_logged_on_users() -> list[str]:
    try:
        creation_flags = subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
        raw = subprocess.check_output(
            ["qwinsta"], text=True, stderr=subprocess.DEVNULL, timeout=5,
            creationflags=creation_flags
        )
    except Exception:
        return []

    users: set[str] = set()
    for line in raw.splitlines()[1:]:
        parts = re.sub(r"\s{2,}", " ", line).strip().split(" ")
        if len(parts) >= 3:
            _, username, state = parts[0], parts[1], parts[2]
            if state.lower().startswith(("active", "disc")):
                users.add(username)

    return sorted(users)


def get_environment() -> dict:
    import os
    try:
        return dict(os.environ)
    except Exception:
        return {}
