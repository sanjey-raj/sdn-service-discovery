import argparse
import signal
import socket
import time
from common import decode, encode, request, MAX_PACKET

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--registry', default='10.0.0.1')
    p.add_argument('--registry-port', type=int, default=9999)
    p.add_argument('--service', default='echo')
    p.add_argument('--port', type=int, default=10001)
    p.add_argument('--heartbeat', type=float, default=0.7)
    a = p.parse_args()
    running = True
    def stop(*_):
        nonlocal running
        running = False
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    data = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    data.bind(('0.0.0.0', a.port))
    data.settimeout(0.1)
    control = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    target = (a.registry, a.registry_port)
    advert = dict(op='advertise', service=a.service, port=a.port)
    due = 0
    while running:
        if time.monotonic() >= due:
            try:
                request(control, target, advert, timeout=0.15, retries=1)
            except TimeoutError:
                pass
            due = time.monotonic() + a.heartbeat
        try:
            raw, peer = data.recvfrom(MAX_PACKET)
            msg = decode(raw)
            if msg.get('op') == 'call':
                data.sendto(encode(dict(v=1, xid=msg.get('xid'), ok=True,
                                       result=msg.get('payload'), server=a.port)), peer)
        except (socket.timeout, ValueError, UnicodeError):
            pass
    try:
        request(control, target, dict(advert, op='withdraw'), retries=1)
    except TimeoutError:
        pass

if __name__ == '__main__':
    main()
