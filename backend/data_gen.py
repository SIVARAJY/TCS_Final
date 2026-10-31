"""Stage 1 - Data collection (synthetic). Customers, accounts, devices, IPs, merchants, transactions.
Plants: Ring 1 (duplicate identity + shared device/IP + fan-in + rapid pass-through), Ring 2 (circular flow),
an innocent household (benign decoy) and a same-name stranger (entity-resolution decoy)."""
import random
from datetime import datetime, timedelta

BASE = datetime(2026, 10, 12, 9, 0)
FIRST = ["Asha", "Ravi", "Meena", "Karthik", "Divya", "Imran", "Lakshmi", "Suresh", "Neha", "Farhan", "Anita", "Rohit", "Kavya", "Dev", "Isha"]
LAST = ["Kumar", "Iyer", "Reddy", "Khan", "Das", "Pillai", "Sharma", "Joseph", "Naidu", "Menon", "Gupta", "Verma"]
STREETS = ["Anna Salai", "Lake View Rd", "Beach Rd", "Temple St", "Mount Rd", "Park St", "Gandhi St", "Nehru Nagar"]


def generate(seed: int = 7):
    rnd = random.Random(seed)
    nodes, edges = {}, []
    n = {"txn": 0}

    def node(id_, type_, label=None, **attrs):
        nodes.setdefault(id_, {"id": id_, "type": type_, "label": label or id_, **attrs})

    def cust(cid, name, dob, phone, email, address):
        node(cid, "customer", cid, name=name, dob=dob, phone=phone, email=email, address=address)

    def own(c, a):
        node(a, "account"); edges.append({"source": c, "target": a, "type": "OWNS"})

    def uses(c, d):
        node(d, "device"); edges.append({"source": c, "target": d, "type": "USES"})

    def login(c, ip):
        node(ip, "ip"); edges.append({"source": c, "target": ip, "type": "LOGIN_FROM"})

    def txn(src, dst, amount, ts, kind="TRANSFER"):
        n["txn"] += 1
        edges.append({"source": src, "target": dst, "type": kind, "amount": round(amount, 2),
                      "ts": ts.isoformat(timespec="minutes"), "txn": f"TXN-{n['txn']:03d}"})

    # --- background: 40 ordinary customers ---
    for i in range(40):
        c = f"CUS-{1000+i}"
        name = f"{rnd.choice(FIRST)} {rnd.choice(LAST)}"
        dob = f"{rnd.randint(1960, 2002)}-{rnd.randint(1, 12):02d}-{rnd.randint(1, 28):02d}"
        phone = f"+91 9{rnd.randint(10**8, 10**9-1)}"
        addr = f"{rnd.randint(1, 99)} {rnd.choice(STREETS)}, Chennai"
        if i == 10:  # decoy: same name as ring customer, different person
            name, dob, addr = "Arjun Mehta", "1985-02-02", "7 Park St, Chennai"
        cust(c, name, dob, phone, f"user{i}@mail.com", addr)
        own(c, f"ACC-{2000+i}"); uses(c, f"DEV-{100+i}"); login(c, f"IP-{100+i}")
    # innocent household: CUS-1001 lives with CUS-1000 and shares device + IP
    h = nodes["CUS-1000"]
    nodes["CUS-1001"].update(name=f"{nodes['CUS-1001']['name'].split()[0]} {h['name'].split()[1]}", address=h["address"])
    uses("CUS-1001", "DEV-100"); login("CUS-1001", "IP-100")

    for m in range(1, 9):
        node(f"MER-{m}", "merchant")
    senders = {}
    for _ in range(45):  # forward-only transfers, max 2 senders per receiver -> no accidental fan-in/cycles
        a, b = sorted(rnd.sample(range(40), 2))
        if len(senders.setdefault(b, set())) >= 2:
            continue
        senders[b].add(a)
        txn(f"ACC-{2000+a}", f"ACC-{2000+b}", rnd.uniform(20, 900), BASE - timedelta(days=rnd.randint(0, 20), minutes=rnd.randint(0, 1400)))
    for _ in range(50):
        txn(f"MER-{rnd.randint(1, 8)}", f"ACC-{2000+rnd.randint(0, 39)}", rnd.uniform(15, 400),
            BASE - timedelta(days=rnd.randint(0, 20), minutes=rnd.randint(0, 1400)), "PAYS")

    # --- RING 1 ---
    cust("CUS-1", "Arjun Mehta", "1990-04-12", "+91 98410 11223", "arjun.mehta@mail.com", "12 Lake View Road, Chennai")
    cust("CUS-2", "Priya Nair", "1993-08-30", "+91 90030 55671", "priya.n@mail.com", "44 Beach Rd, Chennai")
    cust("CUS-3", "Arjun K. Mehta", "1990-04-12", "98410-11223", "a.mehta90@mail.com", "12 Lakeview Rd, Chennai")  # duplicate identity
    cust("CUS-900", "Vikram Rao", "1979-11-03", "+91 94440 77812", "v.rao@mail.com", "9 Temple St, Chennai")
    cust("CUS-950", "Sana Iqbal", "1988-01-21", "+91 97100 22134", "sana.i@mail.com", "31 Gandhi St, Chennai")
    for c, a in [("CUS-1", "ACC-101"), ("CUS-2", "ACC-102"), ("CUS-3", "ACC-103"), ("CUS-900", "ACC-900"), ("CUS-950", "ACC-950")]:
        own(c, a)
    uses("CUS-1", "DEV-7"); uses("CUS-2", "DEV-7"); uses("CUS-3", "DEV-8")
    uses("CUS-900", "DEV-900"); uses("CUS-950", "DEV-950")
    for c in ["CUS-1", "CUS-2", "CUS-3"]:
        login(c, "IP-55")
    login("CUS-900", "IP-900"); login("CUS-950", "IP-950")
    t0 = BASE + timedelta(days=1)
    for mer, acc, amt, dt in [("MER-3", "ACC-101", 5000, -90), ("MER-5", "ACC-102", 4900, -80), ("MER-6", "ACC-103", 5000, -70)]:
        txn(mer, acc, amt, t0 + timedelta(minutes=dt), "PAYS")
    txn("ACC-101", "ACC-900", 4900, t0)
    txn("ACC-102", "ACC-900", 4800, t0 + timedelta(minutes=7))
    txn("ACC-103", "ACC-900", 4950, t0 + timedelta(minutes=15))
    txn("ACC-900", "ACC-950", 14200, t0 + timedelta(minutes=22))

    # --- RING 2: circular flow ---
    for k, nm in [(910, "Mohan Lal"), (911, "Rekha Bose"), (912, "Tariq Ali")]:
        cust(f"CUS-{k}", nm, f"19{70+k%20}-0{k%9+1}-1{k%9}", f"+91 9{k}000{k}12", f"u{k}@mail.com", f"{k} Mount Rd, Chennai")
        own(f"CUS-{k}", f"ACC-{k}"); uses(f"CUS-{k}", f"DEV-{k}"); login(f"CUS-{k}", f"IP-{k}")
    t1 = BASE + timedelta(days=3)
    txn("ACC-910", "ACC-911", 9000, t1)
    txn("ACC-911", "ACC-912", 8900, t1 + timedelta(hours=2))
    txn("ACC-912", "ACC-910", 8800, t1 + timedelta(hours=4))
    return list(nodes.values()), edges
