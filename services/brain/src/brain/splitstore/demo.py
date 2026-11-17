"""Demo: docker compose run --rm brain python -m brain.splitstore.demo

Seeds invented salaries, prints a raw dump of vault-a, shows the payroll total computed without
rebuilding any salary, then tampers with one share and shows the check catching it.
"""

from decimal import Decimal
from typing import Any

import psycopg

from brain.config import settings
from brain.splitstore import AccessDenied, Actor, IntegrityError, get_store
from brain.splitstore.shares import P

STAFF = [  # invented people and amounts, in cents
    ("emp-001", "Γιώργος Παπαδόπουλος", 4_250_00),
    ("emp-002", "Μαρία Ιωάννου", 5_100_00),
    ("emp-003", "Νίκος Καραγιάννης", 3_875_50),
    ("emp-004", "Ελένη Δημητρίου", 6_420_00),
    ("emp-005", "Alex Smith", 7_000_00),
    ("emp-006", "Σοφία Αλεξίου", 3_990_25),
]
HR = Actor("demo.hr", "payroll")
OUTSIDER = Actor("demo.intern", "intern")


def euros(cents: int) -> str:
    return f"{Decimal(cents) / 100:,.2f} EUR"


def main() -> None:
    audit: list[tuple[str, str, str, dict[str, Any]]] = []
    store = get_store(lambda *e: audit.append(e))
    with psycopg.connect(settings.vault_a_url) as c:
        c.execute("DELETE FROM shares WHERE record_id LIKE 'emp-%'")
    with psycopg.connect(settings.vault_b_url) as c:
        c.execute("DELETE FROM shares WHERE record_id LIKE 'emp-%'")

    print("1. Seeding invented salaries and names (each value split in two shares)")
    for rid, name, cents in STAFF:
        store.store(rid, "name", name)
        store.store(rid, "salary_cents", cents)
    print(f"   stored {len(STAFF) * 2} values\n")

    print("2. Raw dump of vault-a (this is all someone who steals vault-a sees)")
    with psycopg.connect(settings.vault_a_url) as c:
        rows = c.execute(
            "SELECT record_id, field, num, encode(data, 'hex') FROM shares "
            "WHERE record_id LIKE 'emp-%' ORDER BY record_id, field"
        ).fetchall()
    for rid, field, num, hexdata in rows:
        print(f"   {rid}  {field:<13} {num if num is not None else hexdata}")

    print("\n3. Aggregate payroll (each vault sums its own shares; no salary is rebuilt)")
    total = store.aggregate_sum("salary_cents")
    print(
        f"   total payroll: {euros(total)}   (plaintext check: {euros(sum(s for *_, s in STAFF))})"
    )

    print("\n4. Authorized reveal vs. unauthorized")
    who = store.reveal("emp-002", "name", HR)
    pay = store.reveal("emp-002", "salary_cents", HR)
    assert isinstance(who, str) and isinstance(pay, int)
    print(f"   payroll officer sees emp-002: {who}, {euros(pay)}")
    try:
        store.reveal("emp-002", "salary_cents", OUTSIDER)
    except AccessDenied as e:
        print(f"   intern refused: {e}")

    print("\n5. Tamper with one share in vault-a (+1 on emp-003's salary share)")
    with psycopg.connect(settings.vault_a_url) as c:
        c.execute(
            f"UPDATE shares SET num = (num + 1) % {P} "
            "WHERE record_id = 'emp-003' AND field = 'salary_cents'"
        )
    try:
        store.reveal("emp-003", "salary_cents", HR)
        print("   NOT DETECTED (this is a bug)")
    except IntegrityError as e:
        print(f"   detected: IntegrityError ({e})")
    print(
        "   audit trail:",
        [(a, act, t) for a, act, t, _ in audit if "integrity" in act or "denied" in act],
    )


if __name__ == "__main__":
    main()
