# Enterprise 802.1X RADIUS Authentication & Automated Triage Simulator

## Objective

A fully containerized 802.1X network authentication lab simulating enterprise wireless access control (AAA). Built to demonstrate secure protocol analysis (EAP-PEAP/MSCHAPv2) and Python-based network automation, this project replicates the architecture of modern corporate SSIDs and automates the detection of authentication failures using custom packet inspection scripts.

## Tech Stack

* **Infrastructure:** Docker Compose, Ubuntu, FreeRADIUS
* **Networking:** Virtual Bridge Networks, UDP 1812/1813, 802.1X
* **Security & Cryptography:** EAPOL, PEAP, MSCHAPv2, PAP
* **Automation & Analysis:** Python 3.14, `pyshark`, `tshark`, `eapol_test`

## Architecture Overview

The environment runs on a native Linux filesystem to enforce strict POSIX permissions. A virtual Docker bridge network (`172.20.0.0/24`) connects a FreeRADIUS server to an Ubuntu-based supplicant client. The client container is granted elevated `NET_ADMIN` kernel capabilities to place its virtual interface into promiscuous mode, allowing Python-driven packet capture scripts to monitor the cryptographic handshakes in real-time.

---

## Phase 1: Environment Initialization & Network Build

To prevent FreeRADIUS from crashing due to globally writable file permissions (a common issue when mounting Windows NTFS drives into Linux containers), the project is isolated entirely within the native Linux filesystem.

```bash
mkdir -p ~/radius_auth_proj/{radius_config,scripts,pcaps}
cd ~/radius_auth_proj
```

### Docker Infrastructure (`docker-compose.yml`)
The entire lab is orchestrated via Docker Compose. 

```yaml
services:
  freeradius:
    image: freeradius/freeradius-server:latest
    container_name: hpe_freeradius
    command: ["-X"]
    ports:
      - "1812:1812/udp" # RADIUS Authentication
      - "1813:1813/udp" # RADIUS Accounting
    volumes:
      - ./radius_config/clients.conf:/etc/freeradius/clients.conf
    networks:
      hpe_lab_net:
        ipv4_address: 172.20.0.5

  radius_client:
    image: ubuntu:latest
    container_name: hpe_supplicant
    cap_add:
      - NET_ADMIN 
    volumes:
      - ./scripts:/scripts
      - ./pcaps:/pcaps 
    networks:
      hpe_lab_net:
        ipv4_address: 172.20.0.10
    command: tail -f /dev/null 

networks:
  hpe_lab_net:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/24
```

**Description:**
*   **Bridge Network (`hpe_lab_net`):** A custom `/24` subnet guarantees static IP assignments, allowing the client to reliably target the RADIUS server without DNS dependencies.
*   **Debug Mode (`-X`):** The server is forced into deep-debug mode to expose inner-tunnel cryptographic failures during EAP negotiation.
*   **Kernel Capabilities (`NET_ADMIN`):** Standard Docker containers are stripped of network manipulation rights. Injecting `NET_ADMIN` grants the Ubuntu container the necessary privileges to execute packet sniffers (`tshark`) directly against its virtual Ethernet interface.

```bash
docker compose up -d
```

## Phase 2: RADIUS Configuration & Dynamic Credential Injection

The FreeRADIUS server requires a recognized NAS client and a user database. The `clients.conf` file is mapped via a standard Docker volume to define the AES shared secret (`hpe_radius_secret_2026`).

**The WSL Volume Mapping Workaround:**
Due to a known Docker daemon bug on Windows Subsystem for Linux (WSL) where dynamically mapped single text files are occasionally corrupted into blank directories, the plaintext user credentials must be generated locally without hidden carriage returns (CRLF) and forcefully injected into the running container via `docker cp`.

```bash
echo 'mateo_test Cleartext-Password := "WirelessAuth2026"' > radius_config/users
echo '' >> radius_config/users
docker cp radius_config/users hpe_freeradius:/etc/freeradius/mods-config/files/authorize
docker restart hpe_freeradius
```
## Phase 3: Client Toolchain & Dependency Management

The Ubuntu supplicant container acts as our simulated enterprise endpoint. Dependencies including `eapoltest`, `tshark`, and the official `freeradius-common` dictionary packages are installed via an interactive root shell.

```bash
docker exec -it hpe_supplicant bash
apt update && apt install -y python3 python3-pip freeradius-common eapoltest tshark
python3 -m pip install pyrad pyshark --break-system-packages
```
## Phase 4: Basic Authentication Verification (PAP)

Before initiating complex TLS handshakes, basic network routing and database decryption are verified using a custom Python script.

### Trigger Script (`radius_trigger.py`)
```python
import os
import socket
import pyrad.packet
from pyrad.client import Client
from pyrad.dictionary import Dictionary

# Initialize the RADIUS client with standard dictionaries
dict_path = "/usr/share/freeradius/dictionary"
client = Client(server="172.20.0.5", secret=b"hpe_radius_secret_2026", dict=Dictionary(dict_path))
client.timeout = 5

# Construct the Access-Request packet
req = client.CreateAuthPacket(code=pyrad.packet.AccessRequest, User_Name="mateo_test")
req["User-Password"] = req.PwCrypt("WirelessAuth2026") # Encrypts payload via the shared secret

print("[*] Sending RADIUS Access-Request to 172.20.0.5:1812...")

try:
        reply = client.SendPacket(req)
        if reply.code == pyrad.packet.AccessAccept:
                print("[+] Success: Received Access-Accept. Authentication verified!")
        elif reply.code == pyrad.packet.AccessReject:
                print("[-] Failed: Received Access-Reject. Check credentials or clients.conf.")
except Exception as e:
        print(f"[!] Error: {e}")
```

**Description:**
This script isolates network-layer variables. If the complex 802.1X TLS handshake fails later, this script proves whether the issue is a simple password mismatch/routing failure, or a cryptographic certificate error. The script utilizes `pyrad` to load the official RADIUS Attribute-Value Pair (AVP) dictionaries, constructs a standard Password Authentication Protocol (PAP) frame, and mathematically hashes the password payload against the NAS shared secret before transmission.

```bash
python3 /scripts/radius_trigger.py
```
## Phase 5: Enterprise 802.1X PEAP/MSCHAPv2 Simulation

To simulate a true enterprise wireless client connecting to a corporate SSID, we use the `eapol_test` binary. 

### Network Profile (`eapol_test.conf`)
```text
network={
        ssid="HPE_Mist_Corp"
        key_mgmt=IEEE8021X
        eap=PEAP
        identity="mateo_test"
        password="WirelessAuth2026"
        phase2="autheap=MSCHAPV2"
}
```

**Description:**
Modern 802.1X networks utilize a "tunnel inside a tunnel" approach. This configuration defines Phase 1 (`eap=PEAP`), which establishes a secure, encrypted TLS outer tunnel with the RADIUS server to protect the user's identity. Inside that secure tunnel, Phase 2 (`phase2="autheap=MSCHAPV2"`) executes the actual cryptographic challenge-response handshake to validate the password without sending it in plaintext.

```bash
eapol_test -c /scripts/eapol_test.conf -a 172.20.0.5 -p 1812 -s hpe_radius_secret_2026
```
## Phase 6: Automated PCAP Triage Agent

To simulate how enterprise cloud engineering teams build automated triage agents, this Python script utilizes `pyshark` to continuously sniff the virtual interface and automatically flag authentication failures.

### Triage Agent (`auth_monitor.py`)
```python
import pyshark
import time
import asyncio

# --- Python 3.14 Compatibility Monkey-Patch ---
# Newer Python versions aggressively deprecated legacy asyncio thread watchers.
# Pyshark relies on these deprecated watchers during initialization.
# This patch dynamically mocks the expected objects to prevent runtime crashes.
class DummyWatcher:
    def attach_loop(self, loop): pass
    def close(self): pass
    def add_child_handler(self, pid, callback, *args): pass
    def remove_child_handler(self, pid): return False

if not hasattr(asyncio, 'set_child_watcher'):
    asyncio.set_child_watcher = lambda watcher: None
if not hasattr(asyncio, 'get_child_watcher'):
    asyncio.get_child_watcher = lambda: DummyWatcher()
if not hasattr(asyncio, 'SafeChildWatcher'):
    asyncio.SafeChildWatcher = DummyWatcher
# ----------------------------------------------

def monitor_auth():
    # Force event loop creation for the main thread
    asyncio.set_event_loop(asyncio.new_event_loop())
    
    print("[*] Tshark interface initialized. Listening for RADIUS & EAPOL traffic on eth0...")
    
    # BPF Filter drops all irrelevant traffic at the kernel level for performance
    capture = pyshark.LiveCapture(interface='eth0', bpf_filter='udp port 1812 or ether proto 0x888e')

    for packet in capture.sniff_continuously():
        try:
            if 'RADIUS' in packet:
                code = packet.radius.code
                if code == '3':
                    print("[!] ALERT: RADIUS Access-Reject detected! Incorrect credentials or TLS mismatch.")
                elif code == '2':
                    print("[+] SUCCESS: RADIUS Access-Accept verified.")
                    
            elif 'EAP' in packet:
                if packet.eap.code == '4': 
                    print("[!] ALERT: EAP Failure packet detected in the wireless tunnel.")
        except AttributeError:
            continue

if __name__ == '__main__':
    monitor_auth()
```

**Description:**
*   **Packet Inspection:** The script binds directly to `eth0`. Instead of processing all network noise, it applies a strict Berkeley Packet Filter (`bpf_filter`) to capture only RADIUS traffic (UDP 1812) and EAPOL frames (EtherType 0x888e) at the kernel level.
*   **Systems Debugging (Monkey-Patching):** The base Ubuntu image utilizes Python 3.14, which removed legacy `asyncio` threading watchers. Because the `pyshark` dependency has not yet caught up to this deprecation, the script would crash on startup. The inclusion of the monkey-patch intercepts `pyshark`'s calls to the missing functions and returns a dummy object, successfully bypassing the fatal exception and allowing the packet capture to initialize.
