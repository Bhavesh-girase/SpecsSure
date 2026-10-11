"""
Generates data/engine/market_catalog.json — a SYNTHETIC product-space catalogue used by the
Market Feasibility / Restriction detector. Manufacturer names are fictional. In production this
would be replaced by GeM catalogue data, BIS licence data (BIS CARE / e-BIS) and past bid data.

Deterministic (seeded) so evaluations are reproducible:
    python -m scripts.generate_market_catalog
"""
import json
import os
import random

R = random.Random(108)
OUT = os.path.join(os.path.dirname(__file__), "..", "data", "engine", "market_catalog.json")

STEEL_MFRS = ["Arya Rebar Ltd", "Bharat Ispat Works", "Coastal TMT Pvt Ltd", "Deccan Steel Rolling", "Eastern Alloys",
              "Ganga Metallics", "Himgiri Steels", "Indus Rebar Co", "Jwala Ispat", "Kaveri Metals", "Lakshya TMT",
              "Malwa Steel Industries"]
CEMENT_MFRS = ["Adarsh Cements", "Bhoomi Cement Works", "Chambal Cements", "Dhara Cement Ltd", "Everest Clinker",
               "Freedom Cements", "Girnar Cement Co", "Himadri Cements", "Indrayani Cement", "Jyoti Cement Ltd"]
CABLE_MFRS = ["Anant Cables", "Bijli Wires", "Chetak Conductors", "Dhruv Cables", "Ekta Wires", "Flame-Safe Cables"]


def r2(x, n=3):
    return round(x, n)


def steel():
    out = []
    for i, m in enumerate(STEEL_MFRS):
        for j in range(R.choice([1, 2, 2])):
            grade = R.choices(["Fe 500D", "Fe 550D", "Fe 500"], [0.7, 0.2, 0.1])[0]
            ys_min = 500 if "500" in grade else 550
            ys = R.uniform(ys_min + 8, ys_min + 85)
            ratio = R.uniform(1.10, 1.22) if grade.endswith("D") else R.uniform(1.08, 1.14)
            carbon = R.uniform(0.185, 0.25) if not m.startswith("Arya") else R.uniform(0.20, 0.24)
            if m.startswith("Kaveri"):
                carbon = R.uniform(0.15, 0.17)   # the only very-low-carbon producer -> restriction demo
            s = R.uniform(0.018, 0.040)
            p = R.uniform(0.018, 0.040)
            out.append({
                "id": f"STL-{i + 1:02d}{j + 1}", "category": "steel", "manufacturer": m,
                "model": f"{m.split()[0]} TMT {grade.replace(' ', '')}{'-' + chr(65 + j) if j else ''}",
                "grade": grade, "standard": "IS 1786:2008", "bis_licence": R.random() > 0.08,
                "attributes": {
                    "yield_strength": r2(ys, 1), "tensile_strength": r2(ys * ratio, 1), "ts_ys_ratio": r2(ratio, 3),
                    "elongation": r2(R.uniform(16.2, 22.0) if grade.endswith("D") else R.uniform(12.5, 17), 1),
                    "total_elongation_max_force": r2(R.uniform(5.5, 11.0), 1),
                    "carbon": r2(carbon, 3), "sulphur": r2(s, 3), "phosphorus": r2(p, 3),
                    "sulphur_phosphorus": r2(s + p, 3), "carbon_equivalent": r2(R.uniform(0.33, 0.42), 3),
                },
                "sizes_mm": sorted(set([8, 10, 12, 16, 20, 25, 28, 32]) - set(R.sample([10, 25, 28, 32], k=R.choice([0, 0, 1, 1, 2]))) | set(R.sample([36, 40], k=R.randint(0, 2)))),
                "region": R.choice(["North", "South", "East", "West", "Central"]),
            })
    return out


def cement():
    out = []
    for i, m in enumerate(CEMENT_MFRS):
        for grade in R.sample(["43", "53"], k=R.choice([1, 2])):
            base = 43 if grade == "43" else 53
            out.append({
                "id": f"CEM-{i + 1:02d}{grade}", "category": "cement", "manufacturer": m,
                "model": f"{m.split()[0]} OPC {grade}", "grade": grade, "standard": "IS 269:2015", "bis_licence": True,
                "attributes": {
                    "compressive_strength_3d": r2(R.uniform(base * 0.56, base * 0.72), 1),
                    "compressive_strength_7d": r2(R.uniform(base * 0.78, base * 0.9), 1),
                    "compressive_strength_28d": r2(R.uniform(base + 3, base + (14 if grade == "43" else 12)), 1),
                    "fineness": r2(R.uniform(280, 380), 0), "initial_setting_time": r2(R.uniform(60, 200), 0),
                    "final_setting_time": r2(R.uniform(170, 330), 0), "soundness_le_chatelier": r2(R.uniform(0.5, 3.0), 1),
                    "soundness_autoclave": r2(R.uniform(0.02, 0.30), 2),
                },
                "region": R.choice(["North", "South", "East", "West", "Central"]),
            })
    return out


def cables():
    out = []
    for i, m in enumerate(CABLE_MFRS):
        out.append({
            "id": f"CBL-{i + 1:02d}", "category": "cables", "manufacturer": m, "model": f"{m.split()[0]} FR 1100V",
            "grade": "1100 V", "standard": "IS 694:2010", "bis_licence": True,
            "attributes": {"voltage_grade": 1100, "oxygen_index": r2(R.uniform(29, 35), 1),
                           "smoke_density": r2(R.uniform(40, 70), 0), "insulation_thickness": r2(R.uniform(0.7, 0.9), 2)},
            "sizes_mm2": [1.5, 2.5, 4.0, 6.0, 10.0],
            "region": R.choice(["North", "South", "East", "West"]),
        })
    return out


# ---- v2.1 categories (separate RNG so the original steel/cement/cable products stay identical) ----
R2 = random.Random(2026)
LIGHT_MFRS = ["Aalok Lighting", "Bharat LED Works", "Chandni Lamps", "Deepak Illumination", "Elixir Lights", "Frontier LED",
              "Gyan Jyoti Electricals", "Harit Lighting", "Ishaan Opto", "Jugnu LED Pvt Ltd"]
FAN_MFRS = ["Aerowind Fans", "Breeze India", "Chakra Appliances", "Dhanvantari Electric", "Eolic Home", "Pawan Fans Ltd", "Samir Motors"]
MCB_MFRS = ["Abhay Switchgear", "Bhoomi Protection", "Circuit Kavach", "Dhruva Electricals", "Eksha Controls"]
SOLAR_MFRS = ["Arka Solar", "Bhaskar PV", "Chhaya Energy", "Dinkar Modules", "Ekaditya Power", "Suryodaya PV", "Tejas Photovoltaic"]


def lamps():
    out = []
    for i, m in enumerate(LIGHT_MFRS):
        tier = R2.random()                       # manufacturer-level product-line quality
        eff_lo = 88 + 28 * tier
        pf_lo = 0.86 + 0.08 * tier
        for w in sorted(R2.sample([7, 9, 10, 12, 15, 20], k=R2.choice([4, 5, 6]))):
            out.append({"id": f"LMP-{i + 1:02d}{w:02d}", "category": "lighting", "item": "led_lamp", "manufacturer": m,
                        "model": f"{m.split()[0]} LED {w}W", "grade": "General", "standard": "IS 16102 (Part 2):2017",
                        "bis_licence": R2.random() > 0.08,
                        "attributes": {"rated_power": float(w), "luminous_efficacy": r2(R2.uniform(eff_lo, eff_lo + 14), 1),
                                       "power_factor": r2(R2.uniform(pf_lo, min(0.99, pf_lo + 0.06)), 2),
                                       "colour_rendering_index": float(R2.choice([70, 80, 80, 82, 90]) if tier < 0.3 else R2.choice([80, 80, 82, 90])),
                                       "star_rating": float(3 + round(2 * tier))},
                        "caps": ["B22d", "E27"] if R2.random() > 0.3 else ["B22d"],
                        "region": R2.choice(["North", "South", "East", "West", "Central"])})
    return out


def streetlights():
    out = []
    for i, m in enumerate(LIGHT_MFRS[:8]):
        premium = i not in (2, 6)                # two budget product lines
        for w in [30, 45, 60, 90, 120, 150]:
            out.append({"id": f"STR-{i + 1:02d}{w:03d}", "category": "lighting", "item": "led_streetlight", "manufacturer": m,
                        "model": f"{m.split()[0]} Road {w}W", "grade": "General", "standard": "IS 10322 (Part 5/Sec 3):2012",
                        "bis_licence": True,
                        "attributes": {"rated_power": float(w),
                                       "luminous_efficacy": r2(R2.uniform(132, 152) if premium else R2.uniform(112, 126), 1),
                                       "power_factor": r2(R2.uniform(0.95, 0.99) if premium else R2.uniform(0.9, 0.95), 2),
                                       "surge_protection": 10.0 if premium else 6.0},
                        "ip_codes": ["IP65", "IP66"] if premium else ["IP65"],
                        "region": R2.choice(["North", "South", "East", "West", "Central"])})
    return out


def fans():
    out = []
    for i, m in enumerate(FAN_MFRS):
        for sweep in R2.sample([900, 1050, 1200, 1400], k=R2.choice([2, 3])):
            star = float(R2.choice([1, 2, 3, 4, 5, 5]))
            base = {900: 150, 1050: 180, 1200: 210, 1400: 250}[sweep]
            out.append({"id": f"FAN-{i + 1:02d}{sweep}", "category": "fans", "item": "ceiling_fan", "manufacturer": m,
                        "model": f"{m.split()[0]} {sweep} mm {int(star)}-star", "grade": "General", "standard": "IS 374:2019",
                        "bis_licence": R2.random() > 0.1,
                        "attributes": {"sweep": float(sweep), "air_delivery": r2(R2.uniform(base, base + 35), 0),
                                       "service_value": r2(3.2 + 0.55 * star + R2.uniform(0, 0.4), 2), "star_rating": star},
                        "region": R2.choice(["North", "South", "East", "West", "Central"])})
    return out


def mcbs():
    out = []
    for i, m in enumerate(MCB_MFRS):
        out.append({"id": f"MCB-{i + 1:02d}", "category": "electrical", "item": "mcb", "manufacturer": m,
                    "model": f"{m.split()[0]} MCB", "grade": "General", "standard": "IS/IEC 60898-1:2002", "bis_licence": True,
                    "attributes": {"breaking_capacity": float(R2.choice([6, 10, 10, 10]))},
                    "ratings_a": [6, 10, 16, 20, 25, 32, 40, 63], "curves": R2.sample(["B", "C", "D"], k=R2.choice([2, 3])),
                    "region": R2.choice(["North", "South", "East", "West"])})
    return out


def solar():
    out = []
    for i, m in enumerate(SOLAR_MFRS):
        for wp in R2.sample([440, 540, 550, 580, 600], k=R2.choice([2, 3])):
            out.append({"id": f"PV-{i + 1:02d}{wp}", "category": "solar", "item": "solar_pv_module", "manufacturer": m,
                        "model": f"{m.split()[0]} {wp}Wp", "grade": "General", "standard": "IS 14286 (Part 1/Sec 1):2023",
                        "bis_licence": R2.random() > 0.08, "almm_listed": R2.random() > 0.2,
                        "attributes": {"module_power": float(wp), "module_efficiency": r2(R2.uniform(20.0, 22.8), 2)},
                        "region": R2.choice(["North", "South", "East", "West", "Central"])})
    return out


if __name__ == "__main__":
    data = {"_comment": "SYNTHETIC market catalogue (fictional manufacturers) for feasibility analysis demos. Replace with GeM / BIS licence data in production.",
            "products": steel() + cement() + cables()}
    for p in data["products"]:
        p.setdefault("item", {"steel": "tmt_steel", "cement": "opc_cement", "cables": "pvc_cable"}[p["category"]])
    data["products"] += lamps() + streetlights() + fans() + mcbs() + solar()
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1)
    print(f"wrote {len(data['products'])} products -> {os.path.abspath(OUT)}")
