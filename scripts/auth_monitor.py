import pyshark
import time
import asyncio

#  Python 3.14 Compatibility Monkey-Patch 
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
