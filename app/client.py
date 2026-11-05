import argparse
import csv
import socket
import time
from common import request

def sample(registry, port, service, index=0):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        start = time.perf_counter()
        row = dict(discovery_ms='', call_ms='', total_ms='', success=0, endpoint='', error='')
        try:
            reply = request(s, (registry, port), dict(op='discover', service=service))
            row['discovery_ms'] = (time.perf_counter() - start) * 1000
            services = reply.get('services', [])
            if not services:
                raise ValueError('no service')
            endpoint = services[index % len(services)]
            row['endpoint'] = f"{endpoint['ip']}:{endpoint['port']}"
            call_start = time.perf_counter()
            result = request(s, (endpoint['ip'], endpoint['port']),
                             dict(op='call', payload='hello'))
            row['call_ms'] = (time.perf_counter() - call_start) * 1000
            row['success'] = int(result.get('ok') is True and result.get('result') == 'hello')
        except (TimeoutError, ValueError, OSError) as e:
            row['error'] = str(e)
        row['total_ms'] = (time.perf_counter() - start) * 1000
        return row

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--registry', default='10.0.0.1')
    p.add_argument('--registry-port', type=int, default=9999)
    p.add_argument('--service', default='echo')
    p.add_argument('--count', type=int, default=20)
    p.add_argument('--interval', type=float, default=0.1)
    p.add_argument('--output', default='results/client.csv')
    a = p.parse_args()
    with open(a.output, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['sample', 'discovery_ms', 'call_ms', 'total_ms',
                                         'success', 'endpoint', 'error'])
        w.writeheader()
        for i in range(a.count):
            w.writerow(dict(sample=i, **sample(a.registry, a.registry_port, a.service, i)))
            f.flush()
            time.sleep(a.interval)

if __name__ == '__main__':
    main()
