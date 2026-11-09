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
