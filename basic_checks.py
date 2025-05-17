import os
import platform
import sys
import subprocess # For running external commands
import re # For parsing output sometimes

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

def get_os_version_info():
    """Gathers detailed OS version information."""
    print("--- Operating System Version Details ---")
    print(f"System:          {platform.system()}")    # 'Linux', 'Windows', 'Darwin' (macOS)
    print(f"Release:         {platform.release()}")   # Kernel release, e.g., '5.15.0-78-generic' or '10'
    print(f"Version:         {platform.version()}")   # More detailed version string
    if platform.system() == "Windows":
        # For Windows, platform.version() is good.
        # We can also try to get the "marketing" name if needed via other means (more complex)
        # For instance, using 'ver' command or wmic
        try:
            # 'ver' command gives a concise version like "Microsoft Windows [Version 10.0.19045.2728]"
            ver_output = subprocess.check_output("ver", shell=True, text=True, stderr=subprocess.DEVNULL)
            print(f"Windows Full Ver:  {ver_output.strip()}")
        except Exception as e:
            print(f"Could not get full Windows version via 'ver': {e}")

    elif platform.system() == "Darwin": # macOS
        try:
            # sw_vers gives macOS specific version info
            # e.g., ProductName: macOS, ProductVersion: 13.4, BuildVersion: 22F66
            sw_vers_output = subprocess.check_output(["sw_vers"], text=True, stderr=subprocess.DEVNULL)
            print("macOS Specific:")
            for line in sw_vers_output.strip().split('\n'):
                print(f"  {line.strip()}")
        except Exception as e:
            print(f"Could not get macOS version via 'sw_vers': {e}")
    elif platform.system() == "Linux":
        try:
            # Try to get distribution info from /etc/os-release
            with open("/etc/os-release", "r") as f:
                os_release_info = {}
                for line in f:
                    if '=' in line:
                        key, value = line.strip().split('=', 1)
                        os_release_info[key] = value.strip('"')
                print(f"Distribution:    {os_release_info.get('PRETTY_NAME', 'N/A')}")
                print(f"Distro ID:       {os_release_info.get('ID', 'N/A')}")
                print(f"Distro Version:  {os_release_info.get('VERSION_ID', 'N/A')}")
        except FileNotFoundError:
            print("Linux Distribution: /etc/os-release not found (might be a non-standard Linux).")
        except Exception as e:
            print(f"Could not parse /etc/os-release: {e}")

    print(f"Architecture:    {platform.machine()}")
    print(f"Processor:       {platform.processor()}") # Can be generic
    print(f"Hostname:        {platform.node()}")
    print("-" * 30 + "\n")


def list_installed_applications():
    """
    Attempts to list installed applications.
    This is highly OS-dependent and may not be exhaustive or perfectly accurate.
    """
    print("--- Installed Applications (Attempt) ---")
    print("NOTE: This list is an approximation and may not be complete or perfectly accurate.\n")

    system = platform.system()
    apps = []

    if system == "Windows":
        print("Listing applications for Windows (trying 'wmic' and 'winget'):")
        # Method 1: WMIC (Windows Management Instrumentation) - for MSI installed apps
        try:
            # Adding a timeout to prevent hanging if wmic is slow
            output = subprocess.check_output(
                "wmic product get name, version",
                shell=True, text=True, stderr=subprocess.PIPE, timeout=30
            )
            # Skip header and empty lines, parse "Name Version"
            lines = output.strip().split('\n')
            if len(lines) > 1: # Check if there's more than just the header
                for line in lines[1:]: # Skip header
                    line = line.strip()
                    if line:
                        # Split by two or more spaces to separate name and version
                        parts = re.split(r'\s{2,}', line)
                        app_name = parts[0].strip()
                        app_version = parts[-1].strip() if len(parts) > 1 else "N/A"
                        if app_name and app_name.lower() not in ["name", "version"]: # Filter out headers if any slip through
                             apps.append(f"{app_name} (Version: {app_version})")
        except subprocess.TimeoutExpired:
            print("  WMIC command timed out.")
        except subprocess.CalledProcessError as e:
            print(f"  Error running WMIC: {e.stderr or e}")
        except FileNotFoundError:
            print("  WMIC command not found.")
        except Exception as e:
            print(f"  An unexpected error occurred with WMIC: {e}")

        # Method 2: winget (Windows Package Manager) - for apps installed via winget
        try:
            output = subprocess.check_output(
                "winget list",
                shell=True, text=True, stderr=subprocess.PIPE, timeout=30
            )
            # winget output can be: Name Id Version Available Source
            # We'll take the first part as Name
            lines = output.strip().split('\n')
            if len(lines) > 2: # Skip headers
                for line in lines[2:]:
                    line = line.strip()
                    if line and not line.startswith("----"): # Skip separator lines
                        parts = re.split(r'\s{2,}', line) # Split by 2+ spaces
                        if parts:
                            apps.append(f"{parts[0].strip()} (winget)")
        except subprocess.TimeoutExpired:
            print("  winget command timed out.")
        except subprocess.CalledProcessError as e:
            # winget might not be installed or accessible
            print(f"  Error running winget (or not installed): {e.stderr or e}")
        except FileNotFoundError:
            print("  winget command not found (or not in PATH).")
        except Exception as e:
            print(f"  An unexpected error occurred with winget: {e}")

    elif system == "Darwin": # macOS
        print("Listing applications for macOS (from /Applications and /Users/*/Applications):")
        app_paths = ["/Applications"]
        user_apps_dir = os.path.expanduser("~/Applications")
        if os.path.isdir(user_apps_dir):
            app_paths.append(user_apps_dir)

        for app_dir in app_paths:
            try:
                for item in os.listdir(app_dir):
                    if item.endswith(".app"):
                        apps.append(os.path.join(app_dir, item))
            except FileNotFoundError:
                print(f"  Directory not found: {app_dir}")
            except PermissionError:
                print(f"  Permission denied for directory: {app_dir}")
            except Exception as e:
                print(f"  Error listing apps in {app_dir}: {e}")

        # You could also try to parse `system_profiler SPApplicationsDataType` for more details,
        # but it's more complex (XML output).
        # Example:
        # try:
        #     output = subprocess.check_output(
        #         ["system_profiler", "SPApplicationsDataType", "-xml"],
        #         text=True, stderr=subprocess.DEVNULL
        #     )
        #     # Parse XML output here (e.g., using xml.etree.ElementTree)
        #     print("  (Consider parsing 'system_profiler SPApplicationsDataType -xml' for more details)")
        # except Exception:
        #     pass # Silently ignore if system_profiler fails or is complex

    elif system == "Linux":
        print("Listing applications for Linux (trying common package managers):")
        # Debian/Ubuntu (dpkg)
        try:
            output = subprocess.check_output(
                "dpkg-query -W -f='${Package} (${Version})\n'",
                shell=True, text=True, stderr=subprocess.DEVNULL
            )
            apps.extend([app.strip() for app in output.strip().split('\n') if app.strip()])
            print("  Found apps via dpkg (Debian/Ubuntu).")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("  dpkg not found or failed (not a Debian/Ubuntu based system or dpkg error).")
            # RPM-based (Fedora, CentOS, RHEL)
            try:
                output = subprocess.check_output(
                    "rpm -qa --qf '%{NAME}-%{VERSION}.%{ARCH}\n'",
                    shell=True, text=True, stderr=subprocess.DEVNULL
                )
                apps.extend([app.strip() for app in output.strip().split('\n') if app.strip()])
                print("  Found apps via rpm (RPM-based system).")
            except (subprocess.CalledProcessError, FileNotFoundError):
                print("  rpm not found or failed (not an RPM-based system or rpm error).")
            # Add more for pacman (Arch), etc. if needed
            # e.g. pacman -Q
            try:
                output = subprocess.check_output(
                    "pacman -Q",
                    shell=True, text=True, stderr=subprocess.DEVNULL
                )
                apps.extend([app.strip() for app in output.strip().split('\n') if app.strip()])
                print("  Found apps via pacman (Arch Linux based).")
            except (subprocess.CalledProcessError, FileNotFoundError):
                print("  pacman not found or failed (not an Arch-based system or pacman error).")


    else:
        print(f"Application listing not specifically implemented for OS: {system}")

    if apps:
        # Remove duplicates that might arise from multiple methods
        unique_apps = sorted(list(set(apps)))
        print(f"\nFound {len(unique_apps)} application entries (approximate):")
        for i, app_name in enumerate(unique_apps):
            print(f"  {i+1}. {app_name}")
    else:
        print("  No applications found with the attempted methods or an error occurred.")

    print("-" * 30 + "\n")


def check_virtual_machine():
    """
    Attempts to detect if the script is running in a virtual machine.
    Returns a tuple: (is_vm_bool, detected_hypervisor_string_or_list)
    """
    print("--- Virtual Machine Check ---")
    vm_indicators = []
    detected_hypervisor = "Unknown or Physical"
    is_vm = False

    system = platform.system()

    # --- Common keywords indicating virtualization ---
    vm_keywords = [
        "vmware", "virtualbox", "vbox", "qemu", "kvm", "xen",
        "hyper-v", "microsoft virtual", "parallels", "virtual", "bhyve"
    ]
    # Specific process names for guest tools (lowercase)
    guest_tool_processes = {
        # Hypervisor: [list of process names]
        "VMware": ["vmtoolsd.exe", "vmtoolsd", "vgauthservice.exe"],
        "VirtualBox": ["vboxservice.exe", "vboxtray.exe", "vboxclient"],
        "QEMU/KVM": ["qemu-ga.exe", "qemu-ga", "spice-vdagent.exe", "spice-vdagent"],
        "Hyper-V": ["vmms.exe", "vmicrvp.exe", "vmwp.exe"], # Note: vmms is host, others guest
        "Parallels": ["prl_tools_service.exe", "prl_tools.exe", "prl_disp_service.exe"]
    }


    if system == "Linux":
        # 1. systemd-detect-virt (very reliable if systemd is used)
        try:
            output = subprocess.check_output("systemd-detect-virt", shell=False, text=True, stderr=subprocess.DEVNULL).strip().lower()
            if output != "none" and output != "container": # Exclude containers
                vm_indicators.append(f"systemd-detect-virt: {output}")
                is_vm = True
        except (FileNotFoundError, subprocess.CalledProcessError):
            pass # Command not found or failed

        # 2. Check DMI/SMBIOS information from /sys
        dmi_paths = {
            "product_name": "/sys/class/dmi/id/product_name",
            "sys_vendor": "/sys/class/dmi/id/sys_vendor",
            "board_vendor": "/sys/class/dmi/id/board_vendor",
            "chassis_asset_tag": "/sys/class/dmi/id/chassis_asset_tag", # Sometimes contains 'Virtual Asset'
        }
        for key, path in dmi_paths.items():
            try:
                with open(path, "r") as f:
                    content = f.read().strip().lower()
                    for kw in vm_keywords:
                        if kw in content:
                            vm_indicators.append(f"DMI {key}: {content.split()[0] if content else 'N/A'} (matched '{kw}')")
                            is_vm = True
                            break # Found a keyword for this path
            except (FileNotFoundError, PermissionError, OSError): # OSError for non-readable files
                pass

        # 3. Check /proc/cpuinfo for hypervisor flag
        try:
            with open("/proc/cpuinfo", "r") as f:
                cpuinfo_content = f.read().lower()
                if "hypervisor" in cpuinfo_content:
                    vm_indicators.append("CPU hypervisor flag")
                    is_vm = True
                # Some KVM setups might show 'KVMKVMKVM' as vendor_id
                if "vendor_id" in cpuinfo_content and "kvmkvmkvm" in cpuinfo_content:
                    vm_indicators.append("CPU vendor_id: KVMKVMKVM")
                    is_vm = True
        except FileNotFoundError:
            pass

        # 4. Check loaded kernel modules (e.g., virtio, vboxguest)
        try:
            output = subprocess.check_output("lsmod", shell=False, text=True, stderr=subprocess.DEVNULL).lower()
            module_keywords = ["virtio", "vboxguest", "vmwgfx", "xen_netfront", "hv_vmbus"]
            for mod_kw in module_keywords:
                if mod_kw in output:
                    vm_indicators.append(f"Kernel module: {mod_kw}")
                    is_vm = True
        except (FileNotFoundError, subprocess.CalledProcessError):
            pass

    elif system == "Windows":
        # 1. WMIC checks for BIOS manufacturer and system model
        try:
            bios_manufacturer = subprocess.check_output(
                "wmic bios get manufacturer", shell=True, text=True, stderr=subprocess.DEVNULL
            ).strip().lower()
            # Get the actual manufacturer name after the header "Manufacturer"
            bios_m_val = bios_manufacturer.split('\n')[-1].strip()

            system_model = subprocess.check_output(
                "wmic computersystem get model", shell=True, text=True, stderr=subprocess.DEVNULL
            ).strip().lower()
            system_m_val = system_model.split('\n')[-1].strip()

            for kw in vm_keywords:
                if kw in bios_m_val:
                    vm_indicators.append(f"BIOS Manufacturer: {bios_m_val} (matched '{kw}')")
                    is_vm = True
                if kw in system_m_val or "virtual machine" in system_m_val: # Common explicit model
                    vm_indicators.append(f"System Model: {system_m_val} (matched '{kw or 'virtual machine'}')")
                    is_vm = True
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass # WMIC not available or failed

        # 2. Check for common environment variables (less common now)
        if os.environ.get("PROCESSOR_IDENTIFIER") and "virtual" in os.environ["PROCESSOR_IDENTIFIER"].lower():
             vm_indicators.append("Processor Identifier (env var)")
             is_vm = True

        # 3. Registry checks (more advanced, can be error-prone without care)
        # Example: HKEY_LOCAL_MACHINE\HARDWARE\DESCRIPTION\System "SystemBiosVersion" might contain "VBOX" or "VMWARE"
        # This is more involved to do robustly in Python without external libraries for registry access,
        # so we'll skip direct registry reads for a "basic" script but mention it.
        # print("  (Skipping direct registry checks for simplicity in this basic script)")


    elif system == "Darwin": # macOS
        try:
            # system_profiler SPHardwareDataType often gives clues
            output = subprocess.check_output(
                ["system_profiler", "SPHardwareDataType"], text=True, stderr=subprocess.DEVNULL
            ).lower()

            model_identifier = ""
            serial_number = ""

            for line in output.splitlines():
                line = line.strip()
                if "model identifier:" in line:
                    model_identifier = line.split(":", 1)[1].strip()
                elif "serial number (system):" in line:
                    serial_number = line.split(":", 1)[1].strip()

            for kw in vm_keywords:
                if kw in model_identifier:
                    vm_indicators.append(f"Model Identifier: {model_identifier} (matched '{kw}')")
                    is_vm = True
            # Parallels VMs often have serial numbers starting with "vm" or "vz"
            if serial_number.startswith("vm") or serial_number.startswith("vz"):
                vm_indicators.append(f"Serial Number: {serial_number} (Parallels pattern)")
                is_vm = True
            # VMware Fusion might put 'VMware' in the model identifier.
            # VirtualBox on Mac is harder to detect reliably this way, model often mimics real Mac.
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass # system_profiler not found or failed

        # `ioreg` can also be used but parsing its output is more complex.
        # Example: `ioreg -l | grep -e Manufacturer -e ProductName`
        # For simplicity, we stick to system_profiler for this basic check.

    # --- Generic checks (e.g., guest tools processes, if psutil is available) ---
    if PSUTIL_AVAILABLE:
        running_processes = {p.info['name'].lower() for p in psutil.process_iter(['name'])}
        for hypervisor, tools in guest_tool_processes.items():
            for tool_proc in tools:
                if tool_proc in running_processes:
                    vm_indicators.append(f"Guest Tool Process: {tool_proc} ({hypervisor})")
                    is_vm = True
    elif system == "Windows": # Fallback for Windows tasklist if psutil not available
        try:
            tasklist_output = subprocess.check_output("tasklist", shell=True, text=True, stderr=subprocess.DEVNULL).lower()
            for hypervisor, tools in guest_tool_processes.items():
                for tool_proc in tools:
                    if tool_proc in tasklist_output:
                        vm_indicators.append(f"Guest Tool Process (tasklist): {tool_proc} ({hypervisor})")
                        is_vm = True
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

    # Consolidate findings
    if vm_indicators:
        # Try to guess the specific hypervisor from indicators
        # This is a simple heuristic
        unique_indicators = sorted(list(set(vm_indicators)))
        detected_hypervisor_candidates = []
        for ind_str in unique_indicators:
            ind_str_lower = ind_str.lower()
            if "vmware" in ind_str_lower: detected_hypervisor_candidates.append("VMware")
            elif "virtualbox" in ind_str_lower or "vbox" in ind_str_lower: detected_hypervisor_candidates.append("VirtualBox")
            elif "qemu" in ind_str_lower or "kvm" in ind_str_lower: detected_hypervisor_candidates.append("QEMU/KVM")
            elif "hyper-v" in ind_str_lower or "microsoft" in ind_str_lower and "virtual" in ind_str_lower: detected_hypervisor_candidates.append("Hyper-V")
            elif "xen" in ind_str_lower: detected_hypervisor_candidates.append("Xen")
            elif "parallels" in ind_str_lower: detected_hypervisor_candidates.append("Parallels")
            elif "bhyve" in ind_str_lower: detected_hypervisor_candidates.append("Bhyve")
            elif "systemd-detect-virt:" in ind_str_lower:
                detected_hypervisor_candidates.append(ind_str.split(":")[-1].strip().capitalize())


        if detected_hypervisor_candidates:
            # Count occurrences to find the most likely
            from collections import Counter
            hypervisor_counts = Counter(detected_hypervisor_candidates)
            detected_hypervisor = hypervisor_counts.most_common(1)[0][0]
        else:
            detected_hypervisor = "Generic VM (indicators: " + ", ".join(unique_indicators) + ")"

        print(f"Result: Likely running in a Virtual Machine.")
        print(f"Detected Hypervisor/Platform (best guess): {detected_hypervisor}")
        print("Indicators found:")
        for indicator in unique_indicators:
            print(f"  - {indicator}")
    else:
        print("Result: Likely running on a Physical Machine (or VM not detected by these checks).")

    print("-" * 30 + "\n")
    return is_vm, detected_hypervisor



if __name__ == "__main__":
    print("===================================")
    print("     OS Version & App Check        ")
    print("===================================\n")

    get_os_version_info()
    list_installed_applications()

    print("===================================")    
    print("        VM Detection Test          ")
    print("===================================\n")

    # You would typically call other functions like get_os_info() here too
    # from your previous script. For this example, just VM check.

    is_virtual, hypervisor_name = check_virtual_machine()

    if is_virtual:
        print(f"Script concludes: This is a VM (Hypervisor: {hypervisor_name})")
    else:
        print("Script concludes: This is likely a Physical Machine.")


    print("Check complete.")