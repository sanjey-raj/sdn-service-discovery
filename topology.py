#!/usr/bin/env python3
"""Run from repository root with sudo /usr/bin/python3 topology.py."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from mininet.net import Mininet
from mininet.node import OVSSwitch
from mininet.link import TCLink
from mininet.cli import CLI

ROOT = Path(__file__).resolve().parent

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--mode', choices=['dynamic', 'static'], default='dynamic')
    p.add_argument('--experiment', choices=['normal', 'failure', 'loss', 'churn'])
    p.add_argument('--count', type=int, default=60)
    p.add_argument('--out', default='results/run')
    a = p.parse_args()
    os.chdir(ROOT)
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    control_socket = str(out / 'controller.sock')
    if len(control_socket.encode()) >= 104:
        raise SystemExit('Use a shorter --out path (Unix socket path limit)')
    net = Mininet(controller=None, switch=OVSSwitch, link=TCLink, autoSetMacs=True)
    switch = net.addSwitch('s1', protocols='OpenFlow13', failMode='secure')
    hosts = [net.addHost(name, ip=f'10.0.0.{i}/24')
             for i, name in enumerate(['r', 'a', 'b', 'c', 'd'], 1)]
    for h in hosts:
        net.addLink(h, switch, bw=10, delay='2ms')
    procs, logs = [], []
    def spawn(host, name, *args):
        log = open(out / (name + '.log'), 'w')
        logs.append(log)
        command = ['/usr/bin/python3', '-u', *args]
        proc = host.popen(command, stdout=log, stderr=subprocess.STDOUT) if host else subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
        procs.append(proc)
        return proc
    def dump(name):
        result = subprocess.run(['ovs-ofctl', '-O', 'OpenFlow13', 'dump-flows', 's1'],
                                capture_output=True, text=True, check=True)
        (out / name).write_text(result.stdout)
    try:
        net.start()
        controller = spawn(None, 'controller', 'sdn/controller.py', '--mode', a.mode,
                           '--socket', control_socket)
        for _ in range(50):
            if Path(control_socket).exists():
                break
            if controller.poll() is not None:
                raise RuntimeError('controller failed; inspect controller.log')
            time.sleep(0.1)
        else:
            raise RuntimeError('controller did not start')
        r, server_a, server_b, c, d = hosts
        spawn(r, 'registry', 'app/registry.py', '--controller', control_socket)
        first = spawn(server_a, 'server-a', 'app/server.py', '--port', '10001')
        spawn(server_b, 'server-b', 'app/server.py', '--port', '10002')
        time.sleep(2)
        if any(proc.poll() is not None for proc in procs):
            raise RuntimeError('component exited; inspect logs')
        dump('flows-before.txt')
        if not a.experiment:
            print('Hosts: r=registry; a,b=servers; c,d=clients. Logs:', out)
            print('Try: c python3 app/client.py --output results/manual.csv')
            print('Use: sh ovs-ofctl -O OpenFlow13 dump-flows s1')
            CLI(net)
        else:
            if a.experiment == 'loss':
                # Applied after registration; affects subsequent UDP discovery/calls.
                for host in (c, d):
                    host.defaultIntf().config(bw=10, delay='2ms', loss=10)
            clients = [spawn(host, f'client-{i}', 'app/client.py', '--count', str(a.count),
                             '--output', str(out / f'client-{i}.csv'))
                       for i, host in enumerate((c, d), 1)]
            event = {'scenario': a.experiment, 'mode': a.mode, 'count_per_client': a.count}
            if a.experiment in ('failure', 'churn'):
                time.sleep(2)
                first.kill()  # SIGKILL: no graceful withdrawal; test lease expiry.
                first.wait()
                event['failure_wall_time'] = time.time()
                dump('flows-at-failure.txt')
                time.sleep(4)
                dump('flows-after-expiry.txt')
                probe = spawn(c, 'stale-probe', 'app/probe.py')
                if probe.wait(timeout=10):
                    raise RuntimeError('stale probe failed')
                dump('flows-after-stale-probe.txt')
                if a.experiment == 'churn':
                    spawn(server_a, 'server-a-restarted', 'app/server.py', '--port', '10001')
                    event['restart_wall_time'] = time.time()
                    time.sleep(1)
                    dump('flows-after-restart.txt')
            for client in clients:
                if client.wait(timeout=max(120, a.count * 4)):
                    raise RuntimeError('client failed; inspect logs')
            dump('flows-final.txt')
            (out / 'experiment.json').write_text(json.dumps(event, indent=2))
    finally:
        for proc in reversed(procs):
            if proc.poll() is None:
                proc.send_signal(signal.SIGTERM)
        for proc in reversed(procs):
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
        for log in logs:
            log.close()
        net.stop()
        Path(control_socket).unlink(missing_ok=True)

if __name__ == '__main__':
    main()
