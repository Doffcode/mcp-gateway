"""Decision ladder (CLAUDE.md). Pure function of L1/L2 results; K comes from config.

| L2 flags one tool                        -> remove that tool
| L2 flags >= K tools in the same server   -> quarantine server
| L1 mismatch, L2 clean                    -> remove that tool until re-pin approved
| L1 mismatch AND L2 flags the new version -> quarantine server
"""

from dataclasses import dataclass, field

from .l1_pins import L1Result


@dataclass
class Decision:
    allowed: list[str] = field(default_factory=list)
    removed: dict[str, str] = field(default_factory=dict)  # tool -> one-sentence reason
    quarantined: bool = False
    quarantine_reason: str = ""


def decide(server: str, names: list[str], l1: dict[str, L1Result], l2: dict[str, list], k: int) -> Decision:
    d = Decision()
    flagged = [n for n in names if l2.get(n)]
    both = [n for n in flagged if l1[n].status == "mismatch"]
    if both:
        d.quarantined = True
        d.quarantine_reason = (
            f"L1+L2: server '{server}' quarantined because tool '{both[0]}' changed since it was pinned "
            f"and its new version is flagged by L2 ({_flag_summary(l2[both[0]])})."
        )
    elif len(flagged) >= k:
        d.quarantined = True
        d.quarantine_reason = (
            f"L2: server '{server}' quarantined because {len(flagged)} tools ({', '.join(flagged)}) were "
            f"flagged, which meets the threshold K={k}."
        )
    if d.quarantined:
        d.removed = {n: d.quarantine_reason for n in names}
        return d
    for n in names:
        if l2.get(n):
            d.removed[n] = f"L2: tool '{server}/{n}' removed: {_flag_summary(l2[n])}."
        elif l1[n].status == "mismatch":
            d.removed[n] = (
                f"L1: tool '{server}/{n}' removed because its metadata hash changed since it was pinned; "
                f"run `gateway pin approve {server} {n}` to accept the new version."
            )
        else:
            d.allowed.append(n)
    return d


def _flag_summary(flags: list) -> str:
    return "; ".join(str(f) for f in flags)
