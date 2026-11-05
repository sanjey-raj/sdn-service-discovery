"""Send deliberate traffic to a stale endpoint; inspect switch counters afterward."""
import argparse
import socket
import time
from common import encode
p = argparse.ArgumentParser()
p.add_argument('--ip', default='10.0.0.2')
p.add_argument('--port', type=int, default=10001)
p.add_argument('--count', type=int, default=100)
a = p.parse_args()
with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
    for i in range(a.count):
        s.sendto(encode(dict(v=1, op='call', xid=str(i), payload='stale-probe')), (a.ip,a.port))
        time.sleep(.01)
print(f'Sent {a.count} UDP datagrams. Use switch flow counters or tcpdump to establish forwarding/drop.')
