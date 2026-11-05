"""Local out-of-band SDN policy controller using OVS's OpenFlow management socket.
No Ryu dependency. Registry sends full state over a mode-0600 Unix socket.
"""
import argparse
import ipaddress
import json
import os
import socket
import subprocess

COOKIE = '0x21'

def of(bridge, *args):
    subprocess.run(['ovs-ofctl', '-O', 'OpenFlow13', *args[:1], bridge, *args[1:]],
                   check=True, capture_output=True, text=True, timeout=2)

class Policy:
    def __init__(self, bridge, mode, run=of):
        self.bridge, self.mode, self.run = bridge, mode, run
        self.active = set()

    def initialize(self):
        self.run(self.bridge, 'del-flows')
        self.run(self.bridge, 'add-flow', 'priority=0,actions=NORMAL')
        # Service ports reserved for this project. Discovery 9999 remains reachable.
        if self.mode == 'dynamic':
            for port in range(10000, 10016):
                self.run(self.bridge, 'add-flow',
                         f'priority=100,udp,tp_dst={port},actions=drop')

    def reconcile(self, endpoints):
        wanted = set()
        for ip, port in endpoints:
            ip = str(ipaddress.IPv4Address(ip))
            if ip not in ('10.0.0.2', '10.0.0.3') or type(port) is not int or not 10000 <= port <= 10015:
                raise ValueError('endpoint outside lab allowlist')
            wanted.add((ip, port))
        if self.mode == 'dynamic':
            for ip, port in self.active - wanted:
                self.run(self.bridge, 'del-flows',
                         f'cookie={COOKIE}/-1,udp,nw_dst={ip},tp_dst={port}')
            for ip, port in wanted:
                self.run(self.bridge, 'add-flow',
                         f'cookie={COOKIE},priority=200,hard_timeout=3,udp,nw_dst={ip},tp_dst={port},actions=NORMAL')
        self.active = wanted
        print(json.dumps({'event': 'reconcile', 'mode': self.mode,
                          'active': sorted(wanted)}), flush=True)

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--bridge', default='s1')
    p.add_argument('--socket', default='/tmp/sd21.sock')
    p.add_argument('--mode', choices=['static', 'dynamic'], default='dynamic')
    a = p.parse_args()
    policy = Policy(a.bridge, a.mode)
    policy.initialize()
    if os.path.exists(a.socket):
        os.unlink(a.socket)
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.bind(a.socket)
        os.chmod(a.socket, 0o600)
        s.listen(8)
        while True:
            conn, _ = s.accept()
            with conn:
                conn.settimeout(2)
                try:
                    data = b''
                    while b'\n' not in data:
                        chunk = conn.recv(8192)
                        if not chunk or len(data) + len(chunk) > 8192:
                            raise ValueError('invalid snapshot size')
                        data += chunk
                    policy.reconcile(json.loads(data)['endpoints'])
                    conn.sendall(b'OK\n')
                except (ValueError, TypeError, KeyError, OSError, subprocess.SubprocessError) as e:
                    print(str(e), flush=True)

if __name__ == '__main__':
    main()
