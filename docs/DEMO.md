# D1 and D2 demo guide

## D1: approximately 5 minutes

1. Draw the topology and identify discovery versus service UDP traffic.
2. Run the tests and explain one genuine localhost socket test.
3. Start `sudo /usr/bin/python3 topology.py --mode dynamic`.
4. Run `pingall`; invoke both clients using the README commands.
5. Show successful CSV rows and `ovs-ofctl -O OpenFlow13 dump-flows s1`.
6. Identify priority 200 live-service rules, priority 100 default service drop,
   and priority 0 forwarding. Explain the separate local policy controller.

## D2: approximately 8–10 minutes

1. Show the normal static/dynamic repeated-run summary.
2. Run the dynamic failure experiment; show server log, pre-failure flows,
   expired allow rule and stale-probe drop counter delta.
3. Contrast static failure forwarding counters and packet capture.
4. Show dynamic churn: service a's allow rule disappears and later reappears.
5. Show loss experiment success/latency and retry explanation.
6. Present results with limitations and show the GitHub repository.

## Interactive failure and capture

At the Mininet prompt, obtain the server PID precisely (do not use broad pkill):

```text
a pgrep -af 'app/server.py'
a tcpdump -U -n -i a-eth0 udp dst port 10001 > results/capture-a.txt 2>&1 &
```

Choose the PID whose command includes `--port 10001`, then substitute it below:

```text
a kill -9 SERVER_A_PID
```

Wait at least four seconds, dump flows, run probes and dump flows again:

```text
sh ovs-ofctl -O OpenFlow13 dump-flows s1
c python3 app/probe.py --count 100
sh ovs-ofctl -O OpenFlow13 dump-flows s1
c python3 app/client.py --count 10 --output results/after-failure.csv
```

Dynamic mode should drop stale probes before they reach a-eth0; compare a fresh
static run using the same steps. Stop the specific capture PID before exiting.
Restart service a to demonstrate dynamic registration:

```text
a python3 app/server.py --port 10001 > results/restart-a.log 2>&1 &
sh ovs-ofctl -O OpenFlow13 dump-flows s1
```

Wait for the next advertisement before checking the allow rule. The runner cleans
up processes it starts; manually started background jobs should be stopped by PID.

## Viva prompts with key points

- Why UDP? Datagram transport, low setup overhead; application must handle loss.
- Why xid? Reject unrelated or delayed replies; retries are idempotent here.
- Why source validation? Advertised IP cannot redirect a reply; spoofing still
  requires authentication defenses beyond this lab.
- Why leases? A crashed process cannot send a graceful withdrawal.
- TTL tradeoff? Short values detect failure sooner but risk false expiry under loss.
- Where is SDN? Separate controller programs OpenFlow allow/drop rules in response
  to registry state, with successful flow command completion before acknowledging the update.
- Why no remote controller? This implementation uses local OVS management
  connections through ovs-ofctl; the Mininet controller object is unnecessary.
- Does discovery prove service health? No: an endpoint can fail immediately after
  discovery. Call timeouts and subsequent rediscovery are still necessary.
- Is latency lower with SDN? Not guaranteed. This policy adds control work; its
  demonstrated benefit is forwarding control for expired endpoints.
- Concurrency? Event-driven registry, bounded receive waits in each server,
  multiple host processes and independent client sockets.
- Why not exactly-once calls? UDP retries may duplicate requests; echo is idempotent.
- What if the controller dies? New discoveries withhold replies and existing
  allow rules expire. Unrelated forwarding remains available.
