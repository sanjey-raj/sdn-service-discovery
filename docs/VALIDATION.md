# Validation status

## Original development and review environment

Python 3.12.14. Mininet/ovs-ofctl are unavailable here. Five tests and compilation
checks pass. Controller unit tests use a command recorder; a localhost integration
test uses real UDP sockets for registration, lookup, echo, crash and expiry.

## Student-executed Mininet evidence

Uploaded archive contains 31 metadata-backed runs, each with two CSVs and 120
samples (3,720 attempts total): five runs each of static/dynamic normal, failure
and loss, and one dynamic churn run. Logs and flow snapshots were inspected and
statistics recomputed from the original CSVs using analyze_results.py.

- Normal: 600/600 calls succeed in each mode.
- Failure: 580/600 calls succeed in each mode.
- Loss: 599/600 static; 598/600 dynamic.
- Dynamic failure: allow rule for failed server absent in all five expiry dumps;
  priority-100 stale-service drop counter increases by 92–100 during probe stage.
- Churn: failed-server allow rule removed and restored after restart.
- Static: NORMAL forwarding without service-specific drop rules.
- Student screenshots show five tests passing and five-host pingall at 0% loss.

These experiments ran on the student's WSL 2 Ubuntu, not in the review environment.
See REPORT.md for full methodology, ranges and interpretation.

## Remaining submission work

Add team names/roll numbers; capture Python/runtime and hardware versions if
required; publish the repository and insert its URL. No GitHub publication was
performed here. Endpoint packet captures, exact recovery/detection timing,
controller outage tests and repeated churn tests were not provided. They are
possible extensions, not claims made by the supplied report.
