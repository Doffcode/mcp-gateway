"""Build the frozen hard-negative trigger-word list from MITRE ATT&CK (independent of L2's seeds).

Rule (deterministic): every non-revoked, non-deprecated Enterprise ATT&CK technique/sub-technique in the
tactics credential-access, collection, exfiltration, execution -> lowercase word tokens of its name ->
drop tokens shorter than 4 chars and tokens in GENERIC (generic English/IT words that would match almost
any tool) -> sorted unique list.

Usage: python scripts/build_hard_negative_triggers.py <enterprise-attack-19.2.json> > data/hard_negative_triggers.txt
Source: github.com/mitre-attack/attack-stix-data @ 6cda5ad8 enterprise-attack/enterprise-attack-19.2.json
        sha256 dc1639caa5501d720e280cf1cbd8fbe009884a0c9b3e6e9ed9d0c25166c3d8f4
"""

import json
import re
import sys

TACTICS = {"credential-access", "collection", "exfiltration", "execution"}
GENERIC = {
    "data", "from", "with", "over", "into", "local", "system", "systems", "remote", "network", "service",
    "services", "information", "using", "other", "method", "methods", "user", "native", "alternative",
    "automated", "management", "repository", "repositories", "medium", "physical", "shared", "storage",
    "object", "objects", "input", "configuration", "server", "software", "deployment", "tools", "tool",
    "application", "applications", "account", "accounts", "container", "cloud", "protocol", "protocols",
    "public", "scheduled", "task", "tasks", "job", "jobs", "size", "limits", "transfer", "staged", "staging",
}


def main(path: str) -> None:
    bundle = json.load(open(path))
    names = set()
    for o in bundle["objects"]:
        if o.get("type") != "attack-pattern" or o.get("revoked") or o.get("x_mitre_deprecated"):
            continue
        phases = {p["phase_name"] for p in o.get("kill_chain_phases", []) if p.get("kill_chain_name") == "mitre-attack"}
        if phases & TACTICS:
            names.add(o["name"])
    words = {w for n in names for w in re.findall(r"[a-z0-9]+", n.lower()) if len(w) >= 4 and w not in GENERIC}
    print("# Hard-negative trigger words. FROZEN before L2 was built; do not edit by hand.")
    print("# Source: MITRE ATT&CK Enterprise v19.2 (attack-stix-data @ 6cda5ad8), tactics:", ", ".join(sorted(TACTICS)))
    print(f"# Built by scripts/build_hard_negative_triggers.py from {len(names)} technique names.")
    for w in sorted(words):
        print(w)


if __name__ == "__main__":
    main(sys.argv[1])
