"""Write the synthetic proxy and DNS logs in the real formats, plus the DHCP lease table.

Squid `access.log` in native format and Zeek `dns.log` as TSV (PRD section 11). The lease table
maps an address to a user, like a DHCP export would, so the ingest never guesses.
"""

import hashlib
import random
from pathlib import Path

from brain.seed.generate import Org

ZEEK_FIELDS = [
    "ts",
    "uid",
    "id.orig_h",
    "id.orig_p",
    "id.resp_h",
    "id.resp_p",
    "proto",
    "trans_id",
    "rtt",
    "query",
    "qclass",
    "qclass_name",
    "qtype",
    "qtype_name",
    "rcode",
    "rcode_name",
    "AA",
    "TC",
    "RD",
    "RA",
    "Z",
    "answers",
    "TTLs",
    "rejected",
]


def _remote_ip(host: str) -> str:
    h = hashlib.sha256(host.encode()).digest()
    return f"{(h[0] % 200) + 20}.{h[1]}.{h[2]}.{(h[3] % 250) + 1}"


def write_logs(org: Org, out_dir: Path, seed: int = 42) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    ips = {u.idx: u.ip for u in org.users}
    rng = random.Random(f"{seed}:logs")
    squid, zeek = out_dir / "access.log", out_dir / "dns.log"
    with squid.open("w", encoding="utf-8") as sq, zeek.open("w", encoding="utf-8") as zk:
        zk.write("#separator \\x09\n#set_separator\t,\n#empty_field\t(empty)\n#unset_field\t-\n")
        zk.write("#path\tdns\n#fields\t" + "\t".join(ZEEK_FIELDS) + "\n")
        for ev in org.proxy_events:
            ip, ts = ips[ev.user_idx], ev.ts.timestamp()
            remote = _remote_ip(ev.host)
            if ev.via_proxy:
                sq.write(
                    f"{ts:.3f} {rng.randrange(40, 900):>6} {ip} TCP_TUNNEL/200 {ev.size} "
                    f"CONNECT {ev.host}:443 - HIER_DIRECT/{remote} -\n"
                )
            if not ev.via_proxy or rng.random() < 0.7:
                uid = "C" + hashlib.sha1(f"{ts}{ip}{ev.host}".encode()).hexdigest()[:17]
                row = [
                    f"{ts - 0.05:.6f}",
                    uid,
                    ip,
                    str(rng.randrange(20000, 65000)),
                    "10.0.0.2",
                    "53",
                    "udp",
                    str(rng.randrange(1, 65000)),
                    "0.012",
                    ev.host,
                    "1",
                    "C_INTERNET",
                    "1",
                    "A",
                    "0",
                    "NOERROR",
                    "F",
                    "F",
                    "T",
                    "T",
                    "0",
                    remote,
                    "300",
                    "F",
                ]
                zk.write("\t".join(row) + "\n")
    leases = out_dir / "leases.csv"
    with leases.open("w", encoding="utf-8") as f:
        f.write("ip,pseudonym\n")
        for u in org.users:
            f.write(f"{u.ip},{u.pseudonym}\n")
    return {"squid": squid, "zeek": zeek, "leases": leases}
