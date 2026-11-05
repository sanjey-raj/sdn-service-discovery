"""Single-threaded UDP state machine; monotonic leases and acknowledged SDN snapshots."""
import argparse
import json
import socket
import time
from common import decode, encode, MAX_PACKET

class Registry:
    def __init__(self, ttl=3):
        self.ttl = ttl
        self.entries = {}

    def expire(self, now):
        for key in list(self.entries):
            if self.entries[key]['expires'] <= now:
                del self.entries[key]

    def handle(self, msg, peer, now):
        self.expire(now)
        op = msg.get('op')
        if op in ('advertise', 'withdraw'):
            name = msg.get('service')
            port = msg.get('port')
            if not isinstance(name, str) or not 1 <= len(name) <= 64:
                raise ValueError('invalid service')
            if type(port) is not int or not 1024 <= port <= 65535:
                raise ValueError('invalid port')
            key = (name, peer[0], port)
            if op == 'withdraw':
                self.entries.pop(key, None)
            else:
                self.entries[key] = dict(service=name, ip=peer[0], port=port,
                                         expires=now + self.ttl)
            return {'ok': True}
        if op == 'discover':
            return {'ok': True, 'services': [
                {k: v for k, v in e.items() if k != 'expires'}
                for e in self.entries.values() if e['service'] == msg.get('service')]}
        raise ValueError('unknown operation')

    def sync(self, path):
        if not path:
            return
        endpoints = sorted({(e['ip'], e['port']) for e in self.entries.values()})
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            s.connect(path)
            s.sendall(encode({'endpoints': endpoints}) + b'\n')
            if s.recv(32) != b'OK\n':
                raise OSError('controller rejected snapshot')

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--bind', default='0.0.0.0')
    p.add_argument('--port', type=int, default=9999)
    p.add_argument('--ttl', type=float, default=3)
    p.add_argument('--controller')
    a = p.parse_args()
    state = Registry(a.ttl)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind((a.bind, a.port))
    s.settimeout(0.2)
    last_sync = 0
    while True:
        try:
            now = time.monotonic()
            state.expire(now)
            if now - last_sync >= 0.5:
                state.sync(a.controller)
                last_sync = now
            try:
                data, peer = s.recvfrom(MAX_PACKET)
            except socket.timeout:
                continue
            msg = decode(data)
            if a.controller and msg.get('op') in ('advertise', 'withdraw'):
                if peer[0] not in ('10.0.0.2', '10.0.0.3') or type(msg.get('port')) is not int or not 10000 <= msg['port'] <= 10015:
                    raise ValueError('endpoint outside lab allowlist')
            response = state.handle(msg, peer, time.monotonic())
            # Discovery replies are sent only after switch updates acknowledge.
            state.sync(a.controller)
            response.update(v=1, xid=msg.get('xid'))
            s.sendto(encode(response), peer)
        except (ValueError, UnicodeError, KeyError, TypeError) as e:
            print(json.dumps({'event': 'bad_packet', 'error': str(e)}), flush=True)
        except OSError as e:
            # Fail closed: withhold replies; installed allow rules expire in 3 s.
            print(json.dumps({'event': 'controller_error', 'error': str(e)}), flush=True)

if __name__ == '__main__':
    main()
