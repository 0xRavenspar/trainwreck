import os
import platform
import subprocess
import re

# Ensure psutil is available
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    # print("INFO: psutil module not found. Process information gathering will be limited.")

# Keywords and specific process names often associated with security functions.
# This list should be expanded significantly for better coverage.
# We'll categorize them for slightly better context.
# Process names should be lowercase for case-insensitive matching.
SECURITY_PROCESS_INDICATORS = {
    "Antivirus/AntiMalware/EDR": [
        "msmpeng", "windefend", "nissrv", "savservice", "sophos", "avast", "avg", "bitdefender",
        "kaspersky", "mcafee", "norton", "symantec", "f-secure", "trendmicro",
        "clamav", "clamd", "freshclam", "carbonblack", "sentinel", "crowdstrike",
        "falcon", "cybereason", "cylance", "fireeye", "defender", "wdsecurityhealthservice",
        "securityhealthservice", "sense", "healthservice", "mpcmdrun", "amsi" # Anti-Malware Scan Interface
    ],
    "Firewall": [
        "firewall", "wf.msc", "ipfw", "iptables", "nftables", "ufw", "pfsense", # some are commands/tools
        "littlesnitch", "netfilter"
    ],
    "VPN/Proxy/Tunneling": [
        "vpn", "openvpn", "wireguard", "tunnel", "proxy", "privoxy", "ssh", "stunnel",
        "zerotier", "tailscale", "globalprotect", "forticlient", "ciscoconnect", "anyconnect"
    ],
    "System Security/Authentication/Auditing": [
        "lsass", "winlogon", "csrss", "smss", "consent", "uac", # Windows core
        "loginwindow", "opendirectoryd", "authorizationhost", "rapportd", # macOS core
        "sshd", "pam", "auditd", "logind", "polkitd", "gdm", "kdm", "lightdm", # Linux core/display managers
        "osquery", "sysmon", "auditpol", "wevtutil", "journalctl", "rsyslog", "syslog-ng"
    ],
    "Encryption/Integrity": [
        "gpg-agent", "veracrypt", "bitlocker", "truecrypt", "luks", "dm-crypt", "aide", "tripwire"
    ],
    # "Generic Security Terms (use with caution - higher false positive risk)": [
    #     "agent", "service", "daemon", "monitor", "guard", "shield", "protect", "scan",
    #     "secure", "threat", "ids", "ips", "hips", "waf"
    # ]
}


def get_security_related_processes():
    """
    Fetches running processes that might be related to security operations
    based on a list of keywords and known process names.

    Returns:
        list: A list of dictionaries, where each dictionary contains:
              'pid': Process ID
              'name': Process name
              'cmdline': Process command line (if available)
              'category': The category of security indicator matched
              'matched_keyword': The keyword that caused the match
    """
    print("--- Scanning for Security-Related Processes ---")
    print("NOTE: This is heuristic. Results may include false positives or miss some processes.\n")

    security_processes_found = []
    all_processes = []

    if PSUTIL_AVAILABLE:
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'exe']):
                try:
                    pinfo = proc.info
                    # Sometimes cmdline can be None or empty list, handle it.
                    cmdline_str = ' '.join(pinfo['cmdline']) if pinfo['cmdline'] else ''
                    # Normalize name: take basename of exe if available, otherwise use name
                    proc_name = os.path.basename(pinfo['exe']).lower() if pinfo['exe'] else pinfo['name'].lower()
                    if not proc_name: # Skip if process name is empty
                        continue
                    all_processes.append({
                        "pid": pinfo['pid'],
                        "name": proc_name,
                        "cmdline": cmdline_str,
                        "raw_name": pinfo['name'].lower(), # Keep original psutil name too
                        "raw_cmdline": pinfo['cmdline'] or []
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue # Process might have terminated, or we don't have access
                except Exception as e:
                    # print(f"  Skipping process due to error: {e}") # Optional: for debugging
                    continue
        except Exception as e:
            print(f"  Error iterating processes with psutil: {e}")
            # No fallback here as process iteration is central to psutil's strength
            if not all_processes: # if psutil failed early
                print("  psutil failed to list processes. Aborting this check.")
                return []
    else:
        print("  psutil module not found. This check is severely limited without it.")
        print("  Please install psutil: pip install psutil")
        return [] # Cannot reliably get process info cross-platform without psutil

    if not all_processes:
        print("  No processes were retrieved. Cannot perform security check.")
        return []

    # --- Perform matching ---
    matched_pids = set() # To avoid duplicate entries if multiple keywords match one process

    for category, keywords in SECURITY_PROCESS_INDICATORS.items():
        for keyword in keywords:
            kw_lower = keyword.lower()
            for proc_info in all_processes:
                if proc_info['pid'] in matched_pids:
                    continue # Already matched this process

                # Check against normalized process name
                if kw_lower in proc_info['name']:
                    security_processes_found.append({
                        "pid": proc_info['pid'],
                        "name": proc_info['raw_name'], # Report original name for clarity
                        "cmdline": proc_info['cmdline'],
                        "category": category,
                        "matched_keyword": keyword,
                        "match_location": "process_name"
                    })
                    matched_pids.add(proc_info['pid'])
                    continue # Move to next process after a match in name

                # Check against command line arguments (more prone to false positives with generic terms)
                # Be more careful with generic keywords in cmdline
                is_generic_category = "Generic Security Terms" in category
                if not is_generic_category or len(kw_lower) > 4 : # Apply generic keywords if they are reasonably specific
                    if kw_lower in proc_info['cmdline'].lower():
                        security_processes_found.append({
                            "pid": proc_info['pid'],
                            "name": proc_info['raw_name'],
                            "cmdline": proc_info['cmdline'],
                            "category": category,
                            "matched_keyword": keyword,
                            "match_location": "command_line"
                        })
                        matched_pids.add(proc_info['pid'])


    if security_processes_found:
        print(f"Found {len(security_processes_found)} potential security-related process(es):")
        # Sort by PID for consistent output
        for item in sorted(security_processes_found, key=lambda x: x['pid']):
            print(f"  - PID: {item['pid']}, Name: {item['name']}, Category: {item['category']}")
            print(f"    Matched Keyword: '{item['matched_keyword']}' (in {item['match_location']})")
            if item['cmdline']:
                print(f"    Cmdline: {item['cmdline'][:150]}{'...' if len(item['cmdline']) > 150 else ''}")
            else:
                print(f"    Cmdline: N/A")
    else:
        print("  No processes matched the known security-related indicators.")
        print("  This does NOT guarantee no security processes are running.")

    print("-" * 30 + "\n")
    return security_processes_found

# Example of how to use it:
if __name__ == "__main__":
    if not PSUTIL_AVAILABLE:
        print("psutil is required for this script to function effectively.")
        print("Please install it using: pip install psutil")
    else:
        print("=================================================")
        print("   Scan for Security-Related Running Processes   ")
        print("=================================================\n")

        found_procs = get_security_related_processes()

        if found_procs:
            print(f"\nSummary: Identified {len(found_procs)} potential security-related process(es).")
        else:
            print("\nSummary: No processes matched the current list of security indicators.")

        print("\nScan complete.")