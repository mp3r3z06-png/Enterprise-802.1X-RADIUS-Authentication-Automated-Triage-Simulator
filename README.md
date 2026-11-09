# Enterprise 802.1X RADIUS Authentication & Automated Triage Simulator

## Objective

A fully containerized 802.1X network authentication lab simulating enterprise wireless access control (AAA). Built to demonstrate secure protocol analysis (EAP-PEAP/MSCHAPv2) and Python-based network automation, this project replicates the architecture of modern corporate SSIDs and automates the detection of authentication failures using custom packet inspection scripts.

## Tech Stack

* **Infrastructure:** Docker Compose, Ubuntu, FreeRADIUS
* **Networking:** Virtual Bridge Networks, UDP 1812/1813, 802.1X
* **Security & Cryptography:** EAPOL, PEAP, MSCHAPv2, PAP
* **Automation & Analysis:** Python 3.14, `pyshark`, `tshark`, `eapol_test`
