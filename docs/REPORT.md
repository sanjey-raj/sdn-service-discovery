# UDP Service Discovery with Dynamic SDN Filtering

**SDN-Socket Programming – Jackfruit Mini Project | Project 21**  
**Team members and roll numbers:**SANJEY RAJ S(PES1UG25AM350)

&#x09;		      ROHITH(PES1UG25AM319)

&#x09;		      SHARANU SAJJAN(PES1UG25AM361)

&#x09;		      SHANTHANU NAIDU(PES1UG25AM360) 
**GitHub repository:** https://github.com/sanjey-raj/sdn-service-discovery

## Abstract

This project implements a UDP-based service directory integrated with an
SDN-controlled Mininet network. Two service servers periodically advertise an
echo service to a registry. Two clients discover available endpoints and invoke
them directly. A separate local policy controller translates live registry
state into OpenFlow 1.3 allow rules. Lease expiry removes permission for failed
service endpoints; a lower-priority drop rule blocks stale service traffic.

The supplied experiment archive contains 31 runs and 3,720 client attempts:
five repetitions of each static/dynamic normal, failure and packet-loss
condition, plus one dynamic restart experiment. Both modes achieved 100%
success in normal conditions and 96.67% during server failure. Dynamic
filtering increased discovery latency, while switch counters and flow snapshots
provided evidence of stale-traffic blocking and automatic permission recovery.

## 1\. Problem and objectives

Clients need to locate a service without hardcoding every server address.
Servers may register, leave gracefully or crash. A stale directory can direct
clients toward unavailable endpoints. The objectives are to implement low-level
UDP advertisements and discovery, maintain a registry, expire unresponsive
servers, integrate application events with SDN, and evaluate the tradeoff
between static forwarding and dynamic service filtering.

## 2\. Architecture

Five Mininet hosts connect to one Open vSwitch, s1. Each host link is configured
for 10 Mbps bandwidth and 2 ms delay. There is one path; the project does not
implement rerouting.

|Host|Address|Role|
|-|-|-|
|r|10.0.0.1|UDP registry, port 9999|
|a|10.0.0.2|UDP echo server, port 10001|
|b|10.0.0.3|UDP echo server, port 10002|
|c|10.0.0.4|Client 1|
|d|10.0.0.5|Client 2|

Servers send UDP advertisements to r; clients send UDP discovery requests to r.
The registry returns live endpoints, then clients send service requests directly
to the chosen server. Clients alternate across the returned list.

The registry sends full endpoint snapshots to a separate controller over a
mode-0600 Unix socket. Mininet hosts share the filesystem, permitting this local
out-of-band channel. The controller uses ovs-ofctl to issue OpenFlow 1.3 commands
over OVS's local management connection. It is not a Ryu/POX remote controller.
Successful flow command completion is required before snapshot acknowledgement;
the registry synchronizes state before responding to discovery requests.

|Priority|Match|Action|
|-|-|-|
|200|Registered server IP and UDP service port|NORMAL; hard timeout 3 s|
|100|UDP service ports 10000–10015|DROP; dynamic mode only|
|0|Other traffic, including ARP and registry discovery|NORMAL|

Static mode installs only NORMAL forwarding. Both modes retain the same dynamic
application registry; static mode is not a static-directory baseline.

## 3\. Socket protocol and concurrency

Application messages are UTF-8 JSON objects with protocol version v=1, operation
and random correlation identifier xid. The operations are advertise, withdraw,
discover and call. Advertise/withdraw include a service name and port; the
registry takes the IP from the UDP source. Discover returns the matching live
endpoint list. Call returns an echo payload, allowing an objective success check.

Servers advertise approximately every 0.7 s. Registry leases last 3 s and use a
monotonic clock. Graceful exit sends withdrawal; a crash is detected by missing
heartbeats. Clients accept only responses matching both target address and xid,
and retry at most three times with a 0.4 s timeout per attempt. Echo is idempotent;
this protocol does not guarantee exactly-once execution for arbitrary services.

The registry uses a serialized event loop. Each server interleaves heartbeats
and bounded receives. Separate host processes permit two concurrent clients.
Malformed messages are ignored/logged. Endpoint allowlisting restricts SDN-enabled
registration to the lab server IPs and reserved service port range. This is a
trusted-network demonstration, not authenticated service discovery.

## 4\. Experimental method

The environment shown in the student's terminal is Ubuntu 24.04.4 LTS under
WSL 2, kernel 6.18.33.2-microsoft-standard-WSL2. Installation output identifies
Mininet 2.3.0-1.1 and Open vSwitch package 3.3.9-0ubuntu0.24.04.1. These details
come from the supplied screenshots; CPU/RAM, runtime Python version and git
commit were not captured in the uploaded experiment files.

Each run uses two clients with 60 sequential attempts each (120 total), a 0.1 s
inter-sample pause, the same topology, heartbeat and lease settings. Failure kills
server a with SIGKILL approximately 2 s after clients start. Four seconds later,
flow snapshots are saved and 100 deliberately stale datagrams are sent to a.
Restart/churn additionally restarts a after the stale-probe stage. Loss adds 10%
egress loss on the two client links after registration; this is not loss on all
links or independently in both directions.

There are five runs per mode for normal, failure and loss. The first was run
manually; repetitions 2–5 followed the supplied shell loop, with static before
dynamic in each pair. Runs are sequential, unseeded and not randomized. WSL host
load and random loss may affect timing. Churn has one run and is functional
evidence, not a repeated performance comparison.

The analysis recomputes nearest-rank per-run percentiles from the original CSVs,
combining both clients within a run. Reported latency summaries are the median
of the five per-run statistics; bracketed values are minimum–maximum across
runs. These are not pooled percentiles, confidence intervals or significance
tests. Success counts pool attempts within each condition, where each run has
identical size. Failed discovery responses would be absent from discovery
percentiles; total-time percentiles include all attempts.

## 5\. Measured results

|Condition|Mode|Runs|Successful calls / attempts|Success %|Median run discovery p50, ms \[range]|Median run discovery p95, ms \[range]|Median run total p95, ms \[range]|
|-|-|-:|-:|-:|-|-|-|
|normal|static|5|600/600|100.00|9.247 \[9.148–9.303]|10.193 \[9.989–11.357]|23.112 \[21.075–25.890]|
|normal|dynamic|5|600/600|100.00|40.084 \[37.202–41.503]|62.057 \[59.794–76.873]|74.266 \[70.141–91.647]|
|failure|static|5|580/600|96.67|9.245 \[9.091–9.492]|10.320 \[9.955–11.617]|34.365 \[26.330–35.511]|
|failure|dynamic|5|580/600|96.67|27.974 \[27.025–30.582]|52.968 \[47.516–58.587]|73.069 \[64.063–92.499]|
|loss|static|5|599/600|99.83|9.785 \[9.420–10.352]|410.015 \[409.923–411.233]|421.144 \[419.852–819.335]|
|loss|dynamic|5|598/600|99.67|44.900 \[43.150–46.845]|447.055 \[440.594–452.615]|467.799 \[459.673–848.572]|
|churn|dynamic|1|116/120|96.67|36.366 \[36.366–36.366]|78.091 \[78.091–78.091]|104.108 \[104.108–104.108]|

### Interpretation

Normal operation succeeded on all 600 attempts in each mode. Median run discovery
p50 increased from 9.247 ms with static forwarding to 40.084 ms with dynamic
filtering. Repeated flow-programming subprocesses and acknowledged state updates
are a plausible source of overhead, but their contribution was not profiled
separately. The measurements demonstrate a cost, not a latency improvement.

Failure runs succeeded on 580/600 attempts in each mode. All 20 failures in each
condition are recorded as UDP response timeouts. Because both modes use the same
lease-based registry, similar availability is expected. The CSVs lack per-sample
absolute timestamps, so exact crash-to-recovery and last-heartbeat-to-expiry
latencies cannot be established from these files.

Loss runs succeeded on 599/600 static attempts and 598/600 dynamic attempts.
There is no evidence here that dynamic filtering improves packet-loss resilience.
Retries support high completion rates in both modes. Discovery p95 around
410–447 ms is consistent with the configured 400 ms timeout, although individual
retry counts are not logged. Total p95 varied considerably: up to 819.335 ms
static and 848.572 ms dynamic in individual runs.

### Dynamic SDN evidence

All five dynamic failure snapshots after expiry contain only the surviving
server's priority-200 allow rule (10.0.0.3). The failed server's allow rule is
absent. The saved increase in the priority-100 drop counter for UDP 10001 is:

|Run|Drop-counter increase during stale-probe stage|
|-|-:|
|dynamic-failure|100|
|dynamic-failure-r2|98|
|dynamic-failure-r3|100|
|dynamic-failure-r4|92|
|dynamic-failure-r5|100|

The probe program reports sending 100 datagrams. Saved counter deltas range from
92 to 100; the snapshots do not establish the fate of every individual probe.
Possible counter-update timing or other effects were not isolated. Report these
observed deltas without claiming all probes were proven dropped in every run.
The initial dynamic-failure run does show a delta of exactly 100.

All five static failure dumps contain NORMAL forwarding and no dynamic service
drop rules. Their NORMAL counters include other traffic, so they cannot by
themselves quantify the exact number of probes reaching server a. No endpoint
packet capture was included in the upload.

In dynamic-churn, the post-expiry snapshot contains only 10.0.0.3. The restart
snapshot contains both 10.0.0.2 and 10.0.0.3, demonstrating re-registration and
permission restoration. Its observed stale-drop delta is 98; calls succeeded
on 116/120 attempts. This is one functional restart run.

## 6\. Reproduction and evidence

Follow README.md for installation, interactive demonstration and individual
experiments. Run `python3 analyze\_results.py` to regenerate:

* results/verified-run-metrics.csv: metrics for all 31 individual runs.
* results/verified-analysis.json: grouped medians/ranges and flow evidence.

The original client CSVs, controller/registry/server logs, experiment metadata and
flow snapshots are preserved in results/. All 31 metadata-backed runs contain
two client CSVs and the expected 120 samples. Review found no tracebacks,
controller\_error, bad\_packet or capitalized Error messages in these run logs;
this log scan is not a proof that every possible fault was absent.

Five automated application/policy tests passed in the student's Ubuntu screenshot
and again in the review environment. Mocked policy tests alone do not test OVS;
the uploaded Mininet outputs provide separate real-switch evidence.

## 7\. Limitations

The controller is local and uses ovs-ofctl rather than a persistent OpenFlow
framework. Confirm course acceptance if a specific framework is required. The
single-switch topology does not demonstrate multipath routing. There is no
cryptographic authentication, rate limiting, durable registry or registry
replication. Only reserved UDP service destination ports are filtered.
Controller outage fail-close is implemented via hard timeouts but was not tested
by these experiments. No exact recovery timing, packet captures, randomized
trial order or confidence intervals were supplied. Repeated registrations refresh
rules frequently, making the implementation appropriate for a small lab rather
than a high-throughput directory. A full graphical Ubuntu desktop is unnecessary;
the observed Mininet/OpenFlow tests ran under WSL 2.

## Rubric coverage

|Component|Marks|Implementation / evidence|
|-|-:|-|
|D1 architecture|2|README architecture, addressing, protocol and flow rules|
|D1 sockets|4|Low-level UDP, advertisements, discovery, echo, retries, two clients|
|D1 Mininet + SDN|4|Five hosts, OVS, local OpenFlow controller, flow dumps|
|D1 integration|3|Advertise/expire → acknowledged OpenFlow allow/delete|
|D1 testing/demo|2|Local tests plus VM connectivity, lookup, call and flows|
|D2 functionality|4|Registration, withdrawal, lookup, heartbeat expiry|
|D2 dynamic SDN|6|Refresh/remove allow rules, default service drop, hard-timeout fail-close|
|D2 robustness|4|SIGKILL, stale probes, loss and restart|
|D2 performance|5|Paired static/dynamic runs, CSV percentiles, success and counters|
|D2 docs/demo/viva|6|README, source, demo guide, actual results and GitHub submission|

Coverage is not a prediction of marks. Submitted logs provide WSL 2 Mininet
evidence; students must explain the design and publish their GitHub repository.



## 8\. Conclusion

The application demonstrates UDP discovery, multiple clients, lease-based server
removal and dynamic switch permission changes in a working Mininet environment.
Repeated experiments show reliable normal operation and broadly similar call
availability between the two modes. Dynamic mode's additional benefit is stale
service filtering and permission recovery, accompanied by higher measured
discovery latency. A future version could reduce redundant flow updates, add
authenticated advertisements and instrument precise detection/recovery timing.

## References

* Course assignment rubric and supplied Mininet installation guide.
* Mininet walkthrough: https://mininet.org/walkthrough/
* Open vSwitch OpenFlow FAQ: https://docs.openvswitch.org/en/stable/faq/openflow/
* ovs-ofctl manual: https://www.openvswitch.org/support/dist-docs/ovs-ofctl.8.html

