import platform
import subprocess
import re
import socket # For hostname and basic connectivity test

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    # print("INFO: psutil module not found. Network information will be limited.")

def get_network_environment():
    """
    Gathers information about the system's network environment.
    """
    print("--- Network Environment Check ---")
    network_info = {}
    system = platform.system()

    # 1. Hostname
    try:
        hostname = socket.gethostname()
        network_info['hostname'] = hostname
        print(f"Hostname: {hostname}")
        try:
            full_hostname = socket.getfqdn()
            if full_hostname != hostname:
                network_info['fqdn'] = full_hostname
                print(f"Fully Qualified Domain Name (FQDN): {full_hostname}")
        except socket.gaierror:
            print("  Could not resolve FQDN.")
    except Exception as e:
        print(f"Could not get hostname: {e}")
        network_info['hostname'] = "N/A"

    # 2. Network Interfaces, IP Addresses, MAC Addresses
    if PSUTIL_AVAILABLE:
        try:
            net_if_addrs = psutil.net_if_addrs()
            net_if_stats = psutil.net_if_stats() # For interface status (isup)
            interfaces_data = {}

            for iface_name, snic_addrs in net_if_addrs.items():
                iface_detail = {"ipv4_addresses": [], "ipv6_addresses": [], "mac_address": "N/A", "status": "N/A"}
                for snic_addr in snic_addrs:
                    if snic_addr.family == socket.AF_INET: # IPv4
                        iface_detail["ipv4_addresses"].append({
                            "address": snic_addr.address,
                            "netmask": snic_addr.netmask,
                            "broadcast": snic_addr.broadcast
                        })
                    elif snic_addr.family == socket.AF_INET6: # IPv6
                         iface_detail["ipv6_addresses"].append({
                            "address": snic_addr.address,
                            "netmask": snic_addr.netmask
                            # IPv6 doesn't typically have a broadcast like IPv4
                        })
                    elif hasattr(psutil, 'AF_LINK') and snic_addr.family == psutil.AF_LINK: # MAC Address (psutil specific)
                        iface_detail["mac_address"] = snic_addr.address
                    elif system == "Windows" and snic_addr.family == -1 : # AF_LINK on windows might be -1 or other value
                        # Trying to guess MAC based on typical psutil behavior on Windows
                        if re.match(r"([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})", snic_addr.address):
                             iface_detail["mac_address"] = snic_addr.address


                # Get interface status (up/down)
                if iface_name in net_if_stats:
                    iface_detail["status"] = "up" if net_if_stats[iface_name].isup else "down"
                    iface_detail["speed_mbps"] = net_if_stats[iface_name].speed
                    iface_detail["mtu"] = net_if_stats[iface_name].mtu


                # Fallback for MAC if not found via psutil.AF_LINK (e.g., older psutil or specific OS)
                if iface_detail["mac_address"] == "N/A" and system == "Linux":
                    try:
                        with open(f"/sys/class/net/{iface_name}/address", "r") as f:
                            iface_detail["mac_address"] = f.read().strip()
                    except FileNotFoundError:
                        pass # Interface might not have a MAC or be virtual
                elif iface_detail["mac_address"] == "N/A" and system == "Darwin": # macOS
                    try:
                        # Example: ifconfig en0 | awk '/ether/{print $2}'
                        output = subprocess.check_output(f"ifconfig {iface_name}", shell=True, text=True, stderr=subprocess.DEVNULL)
                        match = re.search(r"ether\s+([0-9a-fA-F:]+)", output)
                        if match:
                            iface_detail["mac_address"] = match.group(1)
                    except (subprocess.CalledProcessError, FileNotFoundError):
                        pass


                if iface_detail["ipv4_addresses"] or iface_detail["ipv6_addresses"] or iface_detail["mac_address"] != "N/A":
                    interfaces_data[iface_name] = iface_detail

            network_info['interfaces'] = interfaces_data
            print("\nNetwork Interfaces:")
            for name, data in interfaces_data.items():
                print(f"  Interface: {name} (Status: {data.get('status', 'N/A')}, Speed: {data.get('speed_mbps', 'N/A')} Mbps, MTU: {data.get('mtu', 'N/A')})")
                print(f"    MAC Address: {data['mac_address']}")
                if data["ipv4_addresses"]:
                    print("    IPv4 Addresses:")
                    for addr in data["ipv4_addresses"]:
                        print(f"      - IP: {addr['address']}, Netmask: {addr['netmask']}, Broadcast: {addr.get('broadcast', 'N/A')}")
                if data["ipv6_addresses"]:
                    print("    IPv6 Addresses:")
                    for addr in data["ipv6_addresses"]:
                        print(f"      - IP: {addr['address']}, Netmask: {addr['netmask']}")
        except Exception as e:
            print(f"Error getting interface details with psutil: {e}")
            network_info['interfaces'] = "Error"
    else:
        print("psutil not available. Interface information will be very limited.")
        # Basic fallback for IP using socket (only gets one IP, often the primary one)
        try:
            primary_ip = socket.gethostbyname(hostname) # This can be unreliable for multiple NICs
            print(f"  Primary IP (via socket, may not be primary NIC): {primary_ip}")
            network_info['primary_ip_fallback'] = primary_ip
        except socket.gaierror:
            print("  Could not resolve primary IP via socket.")


    # 3. Default Gateway
    # psutil doesn't have a direct cross-platform way to get the default gateway easily.
    # We rely on OS-specific commands.
    default_gateway = "N/A"
    print("\nDefault Gateway:")
    if system == "Linux":
        try:
            # ip route | grep default
            output = subprocess.check_output("ip route show default", shell=True, text=True, stderr=subprocess.DEVNULL)
            match = re.search(r"default via (\S+)", output)
            if match:
                default_gateway = match.group(1)
        except (subprocess.CalledProcessError, FileNotFoundError, AttributeError):
            pass # Command failed or no default route
    elif system == "Windows":
        try:
            # route print -4 | findstr " 0.0.0.0"
            # Or netstat -rn | findstr "0.0.0.0"
            output = subprocess.check_output("route print -4", shell=True, text=True, stderr=subprocess.DEVNULL)
            # Look for line: 0.0.0.0 0.0.0.0 <gateway_ip> <interface_ip> <metric>
            # The gateway is the third non-empty field on such a line typically
            # This regex is a bit fragile, depends on 'route print' output format
            match = re.search(r"^\s*0\.0\.0\.0\s+0\.0\.0\.0\s+(\S+)\s+", output, re.MULTILINE)
            if match:
                default_gateway = match.group(1)
        except (subprocess.CalledProcessError, FileNotFoundError, AttributeError):
            pass
    elif system == "Darwin": # macOS
        try:
            # netstat -rn | grep default
            output = subprocess.check_output("netstat -rn | grep default", shell=True, text=True, stderr=subprocess.DEVNULL)
            match = re.search(r"default\s+(\S+)", output)
            if match:
                default_gateway = match.group(1)
        except (subprocess.CalledProcessError, FileNotFoundError, AttributeError):
            pass
    print(f"  {default_gateway}")
    network_info['default_gateway'] = default_gateway


    # 4. DNS Servers
    dns_servers = []
    print("\nDNS Servers:")
    if system == "Linux":
        try:
            # Most modern Linux systems use /etc/resolv.conf
            # systemd-resolved might use a stub resolver, actual DNS might be elsewhere
            with open("/etc/resolv.conf", "r") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("nameserver"):
                        dns_servers.append(line.split()[1])
        except FileNotFoundError:
            print("  /etc/resolv.conf not found.")
        except Exception as e:
            print(f"  Error reading /etc/resolv.conf: {e}")

    elif system == "Windows":
        try:
            # Get-DnsClientServerAddress -AddressFamily IPv4 | Select-Object -ExpandProperty ServerAddresses
            # Using 'ipconfig /all' as a more universal command-line approach
            output = subprocess.check_output("ipconfig /all", shell=True, text=True, stderr=subprocess.DEVNULL, encoding='latin-1') # latin-1 for wider char support
            current_dns_servers = []
            for line in output.splitlines():
                if "DNS Servers" in line or "DNS-Server" in line: # Check for localized terms too
                    parts = line.split(":", 1)
                    if len(parts) > 1 and parts[1].strip():
                        # Multiple DNS servers can be on subsequent lines with indentation
                        current_dns_servers.append(parts[1].strip())
                    # Keep collecting subsequent lines if they are indented and contain IPs
                    next_line_index = output.splitlines().index(line) + 1
                    while next_line_index < len(output.splitlines()):
                        next_line = output.splitlines()[next_line_index].strip()
                        if next_line and re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", next_line):
                            current_dns_servers.append(next_line)
                            next_line_index += 1
                        else:
                            break # Stop if not an indented IP
            # Filter out empty strings and duplicates, and "::1" if it slips in
            dns_servers = sorted(list(set(s for s in current_dns_servers if s and s != "::1")))

        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"  Error running ipconfig /all: {e}")
        except Exception as e:
            print(f"  Unexpected error parsing ipconfig output: {e}")

    elif system == "Darwin": # macOS
        try:
            # scutil --dns | grep nameserver | awk '{print $3}'
            output = subprocess.check_output("scutil --dns", shell=True, text=True, stderr=subprocess.DEVNULL)
            for line in output.splitlines():
                line = line.strip()
                if line.startswith("nameserver["):
                    dns_servers.append(line.split()[-1])
            dns_servers = sorted(list(set(dns_servers))) # Remove duplicates
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("  Error running scutil --dns.")

    if dns_servers:
        for dns in dns_servers:
            print(f"  - {dns}")
    else:
        print("  No DNS servers found or unable to determine.")
    network_info['dns_servers'] = dns_servers


    # 5. Basic Internet Connectivity Test
    print("\nInternet Connectivity Test:")
    # Ping a reliable host (e.g., Google's public DNS)
    # Using socket.create_connection for a TCP check, as ICMP ping might be blocked
    # or require admin rights.
    test_host = "8.8.8.8" # Google Public DNS
    test_port = 53    # DNS port
    try:
        socket.create_connection((test_host, test_port), timeout=3)
        print(f"  Successfully connected to {test_host} on port {test_port} (TCP). Internet access likely.")
        network_info['internet_connectivity'] = {"status": "connected", "method": f"TCP to {test_host}:{test_port}"}
    except (socket.timeout, socket.error) as e:
        print(f"  Failed to connect to {test_host} on port {test_port} (TCP): {e}. Internet access might be an issue.")
        network_info['internet_connectivity'] = {"status": "failed", "method": f"TCP to {test_host}:{test_port}", "error": str(e)}

    print("-" * 30 + "\n")
    return network_info


# Example of how to use it:
if __name__ == "__main__":
    if not PSUTIL_AVAILABLE:
        print("psutil is highly recommended for comprehensive network information.")
        print("Please install it using: pip install psutil")
        print("Proceeding with limited functionality...\n")

    print("===================================")
    print("      Network Environment Scan     ")
    print("===================================\n")

    net_env_data = get_network_environment()

    # You can then use net_env_data dictionary for further processing or reporting
    # print("\n--- Collected Data (Dictionary) ---")
    # import json
    # print(json.dumps(net_env_data, indent=2))

    print("\nScan complete.")