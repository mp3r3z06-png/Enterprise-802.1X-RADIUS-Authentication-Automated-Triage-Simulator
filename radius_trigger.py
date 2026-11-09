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
