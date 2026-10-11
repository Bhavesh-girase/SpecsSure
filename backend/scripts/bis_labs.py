"""
Testing route: BIS labs and BIS-recognised / empanelled labs that can test each standard, with their testing charges and
the clauses they test — from BIS LIMS "IS-wise test facilities" (lims.bis.gov.in/home/search_is_number/), fetched from a
machine in India for the compulsory-certification and GeM standards.

Input : var/labs/*.json   Output: data/corpus/bis_labs.json
"""
import collections
import glob
import json
import os
import re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CITY_FIX = {"gujurat": "Gujarat", "kolkata-700027": "Kolkata"}


KNOWN = ["Delhi", "New Delhi", "Noida", "Greater Noida", "Ghaziabad", "Gurugram", "Gurgaon", "Faridabad", "Sonipat", "Panipat", "Ambala", "Alwar",
         "Jaipur", "Jalandhar", "Ludhiana", "Chandigarh", "Mohali", "Parwanoo", "Baddi", "Dehradun", "Haridwar", "Roorkee", "Lucknow", "Kanpur", "Agra",
         "Varanasi", "Meerut", "Kolkata", "Howrah", "Guwahati", "Bhubaneswar", "Patna", "Ranchi", "Jamshedpur", "Raipur", "Bhopal", "Indore",
         "Ahmedabad", "Vadodara", "Baroda", "Surat", "Rajkot", "Vapi", "Gandhinagar", "Mumbai", "Thane", "Navi Mumbai", "Pune", "Nashik", "Nagpur",
         "Aurangabad", "Goa", "Bengaluru", "Bangalore", "Mysuru", "Mysore", "Hubli", "Chennai", "Coimbatore", "Madurai", "Salem", "Tiruchirappalli",
         "Hosur", "Hyderabad", "Secunderabad", "Visakhapatnam", "Vijayawada", "Kochi", "Cochin", "Thiruvananthapuram", "Trivandrum", "Kozhikode",
         "Jammu", "Srinagar", "Shimla", "Solan", "Bhiwadi", "Neemrana", "Udaipur", "Jodhpur", "Kota", "Gwalior", "Jabalpur", "Durgapur", "Siliguri",
         "Cuttack", "Rourkela", "Kakkalur", "Manesar", "Bahadurgarh", "Kundli", "Rudrapur", "Kashipur", "Sahibabad", "Okhla", "Kalyani"]
FIX = {"Gurgaon": "Gurugram", "Bangalore": "Bengaluru", "Baroda": "Vadodara", "Mysore": "Mysuru", "Cochin": "Kochi", "Trivandrum": "Thiruvananthapuram"}


def city_of(name: str):
    for c in sorted(KNOWN, key=len, reverse=True):
        if re.search(r"\b" + re.escape(c) + r"\b", name, re.I):
            return FIX.get(c, c)
    return city_of_tail(name)


def city_of_tail(name: str):
    n = re.sub(r"\(\d+\)", "", name).strip(" ,-")
    m = re.search(r"(?:,|-|–)\s*([A-Za-z .]+?)(?:\s*-?\s*\d{6})?\s*$", n)
    if m:
        c = m.group(1).strip(" .")
        if 2 < len(c) < 25 and not re.search(r"\b(ltd|limited|llp|pvt|private|lab|labs|laboratory|house|centre|center|unit)\b", c, re.I):
            return CITY_FIX.get(c.lower(), c.title())
    return None


def main():
    out, n_labs, labs_all = {}, 0, set()
    for f in glob.glob(os.path.join(ROOT, "var", "labs", "*.json")):
        d = json.load(open(f, encoding="utf-8"))
        if not d["labs"]:
            continue
        rows, tests = [], collections.Counter()
        seen = set()
        for l in d["labs"]:
            name = re.sub(r"\s+\d{5,}\s*$", "", l["lab"]).strip()
            key = (name.lower(), l.get("scope"))
            if key in seen:
                continue
            seen.add(key)
            osl = l.get("osl") if l.get("osl") not in (None, "None", "") else None
            rows.append({"lab": name, "city": city_of(name), "type": "BIS laboratory" if not osl and name.upper().startswith("BIS") else "BIS-recognised lab",
                         "osl_code": osl, "scope": None if l.get("scope") in ("-", "0", "", None) else l["scope"],
                         "charges_total": l.get("charges_total"), "clauses_tested": l.get("clauses")})
            for c in l.get("clause_sample") or []:
                t = re.sub(r"^[\w.() ]*?\(|\)$", "", c).strip() if "(" in c else c
                if 3 < len(t) < 90:
                    tests[t] += 1
            labs_all.add(name.lower())
        rows.sort(key=lambda r: (r["charges_total"] is None, r["charges_total"] or 0, -(r["clauses_tested"] or 0)))
        charges = [r["charges_total"] for r in rows if r["charges_total"]]
        out[d["base"]] = {"labs": rows, "count": len(rows), "min_charges": min(charges) if charges else None,
                          "median_charges": sorted(charges)[len(charges) // 2] if charges else None,
                          "cities": sorted({r["city"] for r in rows if r["city"]}), "tests_seen": [t for t, _ in tests.most_common(12)]}
        n_labs += len(rows)
    meta = {"source": "BIS LIMS — IS-wise test facilities in BIS labs / recognised labs / empanelled labs (lims.bis.gov.in)",
            "fetched": "2026-09-27", "standards": len(out), "lab_entries": n_labs, "distinct_labs": len(labs_all),
            "note": "Charges are as listed by the lab on LIMS (excluding taxes); first two result pages per standard. Confirm on LIMS before relying on them."}
    json.dump({"meta": meta, "standards": out}, open(os.path.join(ROOT, "data", "corpus", "bis_labs.json"), "w"), ensure_ascii=False)
    print(json.dumps(meta, indent=1))
    print(json.dumps(out.get("IS 694", {}), indent=1)[:1500])


if __name__ == "__main__":
    main()
