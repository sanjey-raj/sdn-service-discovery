import importlib.util
from pathlib import Path
import socket
import subprocess
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'app'))
sys.path.insert(0, str(ROOT / 'sdn'))
from registry import Registry
from controller import Policy
from common import request

class StateTests(unittest.TestCase):
    def test_heartbeat_expiry_withdraw_and_multiple_servers(self):
        r = Registry(ttl=3)
        msg = dict(op='advertise', service='echo', port=10001)
        r.handle(msg, ('10.0.0.2', 5555), 0)
        r.handle(msg, ('10.0.0.3', 5555), 1)
        r.handle(msg, ('10.0.0.2', 5555), 2)
        self.assertEqual(len(r.entries), 2)
        r.expire(4)
        self.assertEqual(len(r.entries), 1)
        r.handle(dict(msg, op='withdraw'), ('10.0.0.2', 5555), 4)
        self.assertFalse(r.entries)

    def test_malformed_advertisement(self):
        r = Registry()
        for port in (True, -1, '10001', 70000):
            with self.assertRaises(ValueError):
                r.handle(dict(op='advertise', service='echo', port=port), ('x', 1), 0)

    def test_dynamic_policy_removal_and_refresh(self):
        calls = []
        p = Policy('s1', 'dynamic', lambda *args: calls.append(args))
        p.initialize()
        p.reconcile([['10.0.0.2', 10001]])
        self.assertTrue(any('hard_timeout=3' in str(c) for c in calls))
        p.reconcile([])
        self.assertTrue(any(c[1] == 'del-flows' and 'tp_dst=10001' in str(c) for c in calls))
        self.assertEqual(calls[-1][1], 'del-flows')
        with self.assertRaises(ValueError):
            p.reconcile([['10.0.0.99', 10001]])

    def test_static_policy_does_not_install_dynamic_rules(self):
        calls = []
        p = Policy('s1', 'static', lambda *args: calls.append(args))
        p.initialize()
        count = len(calls)
        p.reconcile([['10.0.0.2', 10001]])
        self.assertEqual(len(calls), count)

class SocketIntegration(unittest.TestCase):
    def test_udp_discovery_call_crash_expiry_and_bad_packet(self):
        # Kernel allocates isolated local ports for this test.
        ports = []
        for _ in range(2):
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.bind(('127.0.0.1', 0))
            ports.append(s)
        rp, sp = [s.getsockname()[1] for s in ports]
        for s in ports:
            s.close()
        processes = []
        try:
            processes.append(subprocess.Popen([sys.executable, str(ROOT/'app/registry.py'),
                                               '--bind', '127.0.0.1', '--port', str(rp), '--ttl', '0.5'],
                                              stdout=subprocess.DEVNULL))
            time.sleep(0.15)
            processes.append(subprocess.Popen([sys.executable, str(ROOT/'app/server.py'),
                                               '--registry', '127.0.0.1', '--registry-port', str(rp),
                                               '--port', str(sp), '--heartbeat', '0.1']))
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.sendto(b'not json', ('127.0.0.1', rp))
                for _ in range(30):
                    reply = request(s, ('127.0.0.1', rp), dict(op='discover', service='echo'))
                    if reply['services']:
                        break
                    time.sleep(0.05)
                self.assertEqual(reply['services'][0]['port'], sp)
                response = request(s, ('127.0.0.1', sp), dict(op='call', payload='works'))
                self.assertEqual(response['result'], 'works')
                processes[-1].kill()
                processes[-1].wait()
                time.sleep(0.7)
                reply = request(s, ('127.0.0.1', rp), dict(op='discover', service='echo'))
                self.assertEqual(reply['services'], [])
        finally:
            for proc in processes:
                if proc.poll() is None:
                    proc.terminate()
                proc.wait(timeout=3)

if __name__ == '__main__':
    unittest.main()
