import os
import platform
import subprocess
import re

# Optional: psutil for better process and service listing
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    # print("INFO: psutil module not found. Process/service checks will be limited.")

# --- Data for known AV/EDR products ---
# This is a sample list. It's far from exhaustive and needs to be expanded/maintained.
# Format: "Product Name": {"processes": [], "services": [], "paths": [], "wmi_keywords": []}

KNOWN_SECURITY_SOFTWARE = {
    # Windows Examples
    "Windows Defender": {
        "processes": ["msmpeng.exe", "nissrv.exe", "windefend.exe"],
        "services": ["windefend", "wcncsvc", "wdboot", "wdfilter", "wdnisdrv", "wdnissvc"],
        "wmi_keywords": ["windows defender"], # Keywords to look for in WMI displayName
        "paths": [ # Note: System paths, harder to use as primary indicators
            os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "Windows Defender"),
            os.path.join(os.environ.get("ProgramData", "C:\\ProgramData"), "Microsoft\\Windows Defender")
        ]
    },
    "CrowdStrike Falcon": {
        "processes": ["csfalconservice.exe", "csfalcondc.exe", "csfalconcontainer.exe"],
        "services": ["csfalconservice"],
        "paths": [os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "CrowdStrike")]
    },
    "SentinelOne": {
        "processes": ["sentinelagent.exe", "sentinelui.exe", "sentinelstaticengine.exe"],
        "services": ["sentinelagent", "sentinelstaticservice"],
        "paths": [os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "SentinelOne")]
    },
    "Carbon Black Cloud Sensor": {
        "processes": ["cb.exe", "carbonsensor.exe", "repsrv.exe"], # Varies by version
        "services": ["cbcarbonblack", "carbonblack"], # Varies
        "paths": [os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "Confer")]
    },
    "McAfee Endpoint Security": {
        "processes": ["masvc.exe", "mfemms.exe", "mfevtps.exe", "mfetp.exe", "mmsinfo.exe"],
        "services": ["mfemms", "mfetp", "mcafeeframework"],
        "wmi_keywords": ["mcafee"],
        "paths": [os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "McAfee")]
    },
    "Symantec Endpoint Protection": {
        "processes": ["ccsvchst.exe", "sepui.exe", "smc.exe"],
        "services": ["symantec endpoint protection", "sepmasterservice", "smcservice"],
        "wmi_keywords": ["symantec"],
        "paths": [
            os.path.join(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"), "Symantec"),
            os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "Symantec")
        ]
    },
    "Sophos Endpoint": {
        "processes": ["sophosfilescanner.exe", "sophoshealth.exe", "savservice.exe", "almon.exe"],
        "services": ["sophos anti-virus", "sophos health service", "savservice"],
        "wmi_keywords": ["sophos"],
        "paths": [os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "Sophos")]
    },
    "Bitdefender Endpoint Security": {
        "processes": ["bdagent.exe", "epsecurityservice.exe", "epupdateservice.exe", "epconsole.exe"],
        "services": ["bdredline", "epsecurityservice", "epupdateservice"],
        "wmi_keywords": ["bitdefender"],
        "paths": [os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "Bitdefender", "Endpoint Security")]
    },
    # macOS Examples
    "Jamf Protect": {
        "processes": ["protectagent"],
        "paths": ["/Library/Application Support/JamfProtect/"]
        # LaunchDaemons: com.jamf.protect.daemon.plist
    },
    "Sophos Anti-Virus (Mac)": {
        "processes": ["sophosscanmanager", "sophosui", "intercheck"],
        "paths": ["/Applications/Sophos Anti-Virus.app"]
    },
    "Little Snitch": { # Network monitor, often considered security software
        "processes": ["littlesnitchd", "littlesnitchagent"],
        "paths": ["/Applications/Little Snitch.app", "/Library/Little Snitch/"]
    },
    # Linux Examples
    "ClamAV": {
        "processes": ["clamd", "freshclam"],
        "services": ["clamav-daemon", "clamav-freshclam"], # systemd service names
        "paths": ["/usr/sbin/clamd", "/etc/clamav/"]
    },
    "Falcon Sensor (Linux)": { # CrowdStrike for Linux
        "processes": ["falcon-sensor"],
        "services": ["falcon-sensor"],
        "paths": ["/opt/CrowdStrike/"]
    },
    "Osquery": { # Often used by EDR solutions or for host monitoring
        "processes": ["osqueryd"],
        "services": ["osqueryd"],
        "paths": ["/usr/bin/osqueryd", "/opt/osquery"]
    }
}

def check_security_software():
    """
    Attempts to detect known AV/EDR software.
    Returns a set of detected product names.
    """
    print("--- Security Software Check ---")
    print("NOTE: This check is heuristic-based and may not be complete or require admin rights for full accuracy.\n")
    detected_products = set()
    system = platform.system()

    running_processes_names = set()
    running_services_names = set() # For Windows

    # --- Gather current system state ---
    if PSUTIL_AVAILABLE:
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                if proc.info['name']: # Ensure name is not None
                    running_processes_names.add(proc.info['name'].lower())
            if system == "Windows":
                for service in psutil.win_service_iter():
                    sinfo = service.as_dict()
                    running_services_names.add(sinfo['name'].lower())
                    running_services_names.add(sinfo['display_name'].lower()) # Also check display name
        except psutil.Error as e:
            print(f"  psutil error: {e} (some checks might be skipped)")
            # Fallbacks if psutil fails or is not fully functional
            if system == "Windows":
                try:
                    # Tasklist for processes
                    output = subprocess.check_output("tasklist /NH /FO CSV", shell=True, text=True, stderr=subprocess.DEVNULL)
                    for line in output.strip().split('\n'):
                        parts = line.split('","')
                        if parts and parts[0]:
                            running_processes_names.add(parts[0].strip('"').lower())
                    # sc query for services (can be slow and needs parsing)
                    # output_svc = subprocess.check_output("sc query state= all", shell=True, text=True, stderr=subprocess.DEVNULL)
                    # Could parse this, but it's more complex. psutil is much preferred.
                except (subprocess.CalledProcessError, FileNotFoundError):
                    print("  Could not use tasklist/sc fallback for Windows.")
            elif system in ["Linux", "Darwin"]:
                try:
                    output = subprocess.check_output("ps -Ao comm=", shell=True, text=True, stderr=subprocess.DEVNULL)
                    for line in output.strip().split('\n'):
                        running_processes_names.add(os.path.basename(line.strip()).lower())
                except (subprocess.CalledProcessError, FileNotFoundError):
                    print(f"  Could not use 'ps' fallback for {system}.")

    else: # No psutil, rely on subprocess fallbacks
        if system == "Windows":
            try:
                output = subprocess.check_output("tasklist /NH /FO CSV", shell=True, text=True, stderr=subprocess.DEVNULL)
                for line in output.strip().split('\n'):
                    parts = line.split('","')
                    if parts and parts[0]:
                        running_processes_names.add(parts[0].strip('"').lower())
                # Note: Reliable service listing without psutil or admin rights for `sc` is harder
                print("  INFO: psutil not found. Windows service checks will be very limited or skipped.")
            except (subprocess.CalledProcessError, FileNotFoundError):
                print("  Could not run tasklist (process check limited).")
        elif system in ["Linux", "Darwin"]:
            try:
                output = subprocess.check_output("ps -Ao comm=", shell=True, text=True, stderr=subprocess.DEVNULL) # comm gives just the command name
                for line in output.strip().split('\n'):
                    running_processes_names.add(os.path.basename(line.strip()).lower())
            except (subprocess.CalledProcessError, FileNotFoundError):
                print(f"  Could not run 'ps' on {system} (process check limited).")


    # --- Check against known products ---
    for product_name, checks in KNOWN_SECURITY_SOFTWARE.items():
        found_indicator = False

        # 1. Check processes
        for proc_pattern in checks.get("processes", []):
            if proc_pattern.lower() in running_processes_names:
                detected_products.add(f"{product_name} (Process: {proc_pattern})")
                found_indicator = True
                break
        if found_indicator: continue # Move to next product if already found

        # 2. Check services (Windows primarily, Linux systemd can be added)
        if system == "Windows":
            for svc_pattern in checks.get("services", []):
                if svc_pattern.lower() in running_services_names:
                    detected_products.add(f"{product_name} (Service: {svc_pattern})")
                    found_indicator = True
                    break
        elif system == "Linux" and PSUTIL_AVAILABLE: # Basic systemd check if psutil is there
            # This is a simplified check; full systemd introspection is more complex
            for svc_pattern in checks.get("services", []): # Assuming "services" for Linux are systemd unit names
                try:
                    # This is a very basic check. A proper check would involve `systemctl is-active servicename`
                    # But for a simple heuristic, if a process matches a service name, it might be it.
                    if svc_pattern.lower() in running_processes_names: # Crude but can work
                         detected_products.add(f"{product_name} (Potential Service/Process: {svc_pattern})")
                         found_indicator = True
                         break
                except Exception:
                    pass # Ignore errors if systemd tools aren't available or psutil method fails
        if found_indicator: continue

        # 3. Check file paths
        for path_pattern in checks.get("paths", []):
            # Expand environment variables in paths if any (e.g. %ProgramFiles%)
            expanded_path = os.path.expandvars(path_pattern)
            if os.path.exists(expanded_path):
                detected_products.add(f"{product_name} (Path: {expanded_path})")
                found_indicator = True
                break
        if found_indicator: continue

        # 4. WMI checks (Windows only)
        if system == "Windows" and checks.get("wmi_keywords"):
            try:
                # Check AntivirusProduct
                # PowerShell equivalent: Get-WmiObject -Namespace "root\SecurityCenter2" -Class AntiVirusProduct
                # Using WMIC as it's more likely to be available without extra modules.
                # This requires admin rights on some systems for SecurityCenter2
                output_av = subprocess.check_output(
                    'wmic /namespace:\\\\root\\SecurityCenter2 path AntiVirusProduct get displayName /format:csv',
                    shell=True, text=True, stderr=subprocess.DEVNULL, timeout=10
                )
                for line in output_av.strip().split('\n'):
                    if not line or line.lower().startswith("node,displayname"): continue # Skip header
                    display_name = line.split(',')[-1].strip().lower()
                    for wmi_kw in checks["wmi_keywords"]:
                        if wmi_kw.lower() in display_name:
                            detected_products.add(f"{product_name} (WMI AntiVirusProduct: {display_name})")
                            found_indicator = True
                            break
                    if found_indicator: break
                if found_indicator: continue

                # Check FirewallProduct (some EDRs might register here)
                # output_fw = subprocess.check_output(
                #    'wmic /namespace:\\\\root\\SecurityCenter2 path FirewallProduct get displayName /format:csv',
                #    shell=True, text=True, stderr=subprocess.DEVNULL, timeout=10
                # )
                # ... similar logic for FirewallProduct if needed ...

            except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
                # print(f"  WMI check failed or timed out: {e} (requires admin rights or WMI service running)")
                pass # Silently continue if WMI fails (common without admin)
            except Exception as e: # Catch any other unexpected error from WMI
                # print(f"  Unexpected WMI error: {e}")
                pass
            if found_indicator: continue


    if detected_products:
        print("Detected potential security software:")
        for item in sorted(list(detected_products)):
            print(f"  - {item}")
    else:
        print("No known security software detected based on the current list and checks.")
        print("  This does NOT guarantee no security software is present.")

    print("-" * 30 + "\n")
    return detected_products


# Example of how to use it:
if __name__ == "__main__":
    print("===================================")
    print("   Security Software Scan Test     ")
    print("===================================\n")

    # You would typically call other functions like get_os_info(), check_virtual_machine() here
    # from your previous script. For this example, just the security check.

    found_software = check_security_software()

    if found_software:
        print(f"\nSummary: Found {len(found_software)} potential security product(s)/indicators.")
    else:
        print("\nSummary: No specific security products identified from the known list.")

    print("\nScan complete.")