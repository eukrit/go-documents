# -*- coding: utf-8 -*-
"""
freight_calculator.py
GO Corporation — Import Landed Cost Calculator
Route: China (Foshan / Guangzhou) → Bangkok, Thailand

Usage:
    Edit the INPUT block below, then run:
        python freight_calculator.py

Rate sources:
  - Sea/Land rates: Gift Somlak rate card (China-Thai, last confirmed 2025)
  - Air rate: Logimark International, PO.1254 MXP→BKK, March 2026
  - Insurance: Chubb via Logimark, confirmed PO.1254 actual invoice
  - HS codes: confirmed from actual Thai customs clearances

RATE TABLE (Gift Somlak / China-Thai, confirmed):
  Sea  CBM : 4,600.00 THB/CBM  ($140.4130/CBM)
  Sea  KGS :    35.00 THB/KG   ($1.0684/KG)
  Land CBM : 7,200.00 THB/CBM  ($219.7769/CBM)
  Land KGS :    48.00 THB/KG   ($1.4652/KG)
  Implied FX: 32.76 THB/USD
"""

# ──────────────────────────────────────────────
#  INPUT — edit this block for each quotation
# ──────────────────────────────────────────────

# Product info
PRODUCT_NAME        = "ED 70 Aluminum Folding Door"
HS_CODE             = "7610"       # See HS code table below
HS_DUTY_RATE        = 0.10         # 10% for HS 7610 (aluminum structures)
                                   # 20% for HS 9403 (furniture) — confirmed

# EXW price — set one of the two options:
EXW_PRICE_FOREIGN   = 0            # Foreign currency amount (set 0 to use THB)
EXW_CURRENCY        = "USD"        # "USD" | "EUR" | "CNY"
FX_RATE_TO_THB      = 32.76        # THB per 1 unit — implied from Gift rate card
                                   # EUR: ~37.40 (Logimark PO.1254, Mar 2026)
                                   # CNY: ~4.50 (check current rate)

EXW_PRICE_THB       = 150000       # Set in THB directly — overrides FX calc if > 0

# Package dimensions and weight
PKG_LENGTH_CM       = 285          # crate length
PKG_WIDTH_CM        = 30           # crate width
PKG_HEIGHT_CM       = 280          # crate height
PKG_ACTUAL_KG       = 120          # gross weight of package

# Freight mode
MODE                = "sea"        # "sea" | "land" | "air"

# ── China-Thai confirmed rates (Gift Somlak rate card) ──────────────────────
# Billing rule: charge whichever is HIGHER — CBM-based or KGS-based
# This reflects standard LCL practice: large/light items pay on volume,
# small/heavy items pay on weight.

SEA_RATE_THB_PER_CBM  = 4600      # Confirmed Gift rate card 2025
SEA_RATE_THB_PER_KG   = 35        # Confirmed Gift rate card 2025

LAND_RATE_THB_PER_CBM = 7200      # Confirmed Gift rate card 2025
LAND_RATE_THB_PER_KG  = 48        # Confirmed Gift rate card 2025

# Factory → Shenzhen/GZ port delivery cost (ask supplier or Gift)
FACTORY_TO_PORT_THB   = 0         # Fill in when known from supplier

# Oversized length surcharge (ask Gift for items >250cm in any dimension)
OVERSIZED_SURCHARGE_THB = 0       # Fill in if applicable

# ── Air freight rate (Logimark, door-to-door EXW) ──────────────────────────
# Basis: PO.1254 Italy→BKK March 2026 = ~182 THB/kg base, ~214 THB/kg with
# fuel (EUR 0.70/kg) + SCC (EUR 0.10/kg) surcharges at 1 EUR = 37.40 THB
# China→BKK is shorter; estimate 100–140 THB/kg — confirm with Logimark/DHL
AIR_RATE_THB_PER_KG   = 130       # REPLACE with fresh forwarder quote

# ── Customs clearance service fee ──────────────────────────────────────────
# Separate from duty/VAT — paid to forwarder for clearance service
# Logimark PO.1254 all-in (freight+clearance+duty) was THB 14,076 for 100 kg air
# Service fee component only: estimate THB 2,000–4,000
CLEARANCE_FEE_THB     = 3000      # REPLACE with forwarder's stated fee

# ── Last-mile Bangkok delivery ──────────────────────────────────────────────
# Confirmed from Slack #shipping-china-thai:
#   Oversized item, 6-wheel truck: THB 3,500
#   Standard 4-wheel truck: THB 1,500–2,500
LAST_MILE_THB         = 3500

# ── Insurance (Chubb via Logimark) ─────────────────────────────────────────
INSURE                = True
INSURANCE_RATE        = 0.0045    # 0.45% — confirmed from actual PO.1254 invoice
INSURANCE_MIN_USD     = 40        # Minimum premium USD 40
USD_RATE              = 32.76     # THB/USD — from Gift rate card implied FX

# ──────────────────────────────────────────────
#  HS CODE REFERENCE
# ──────────────────────────────────────────────
# 9403 : Furniture (chairs, tables, shelving)    → 20%  no permit (confirmed)
# 7610 : Aluminum windows, doors, frames         → ~10% no permit (verify)
# 9405 : Lighting fixtures / luminaires          → ~20% no permit (verify)
# 7308 : Iron/steel structures, frames, doors    → ~10% no permit (verify)

# ──────────────────────────────────────────────
#  CALCULATION ENGINE
# ──────────────────────────────────────────────

def calc_cbm(l, w, h):
    """Volume in CBM: L x W x H (cm) / 1,000,000"""
    return (l * w * h) / 1_000_000

def calc_volumetric_air(l, w, h):
    """Air volumetric weight (kg): L x W x H (cm) / 6,000"""
    return (l * w * h) / 6_000

def calc_freight(mode, cbm, actual_kg):
    """
    China-Thai billing rule (Gift Somlak rate card):
      Charge the HIGHER of CBM-based cost or KGS-based cost.
      This ensures neither very large/light nor very small/heavy
      items are under-charged.

      Sea:  max(CBM x 4600,  KG x 35)
      Land: max(CBM x 7200,  KG x 48)
      Air:  chargeable_kg x rate  where CW = max(actual_kg, vol_kg)
    """
    if mode == "sea":
        cbm_cost = cbm * SEA_RATE_THB_PER_CBM
        kg_cost  = actual_kg * SEA_RATE_THB_PER_KG
        freight  = max(cbm_cost, kg_cost)
        basis    = "CBM" if cbm_cost >= kg_cost else "KGS"
        return freight, cbm_cost, kg_cost, basis
    elif mode == "land":
        cbm_cost = cbm * LAND_RATE_THB_PER_CBM
        kg_cost  = actual_kg * LAND_RATE_THB_PER_KG
        freight  = max(cbm_cost, kg_cost)
        basis    = "CBM" if cbm_cost >= kg_cost else "KGS"
        return freight, cbm_cost, kg_cost, basis
    elif mode == "air":
        vol_kg = calc_volumetric_air(PKG_LENGTH_CM, PKG_WIDTH_CM, PKG_HEIGHT_CM)
        cw     = max(actual_kg, vol_kg)
        freight = cw * AIR_RATE_THB_PER_KG
        basis   = "C.W." + (" vol" if vol_kg > actual_kg else " actual")
        return freight, freight, freight, basis
    else:
        raise ValueError(f"Unknown mode: {mode}")

def calc_insurance(cif_thb):
    """Chubb cargo insurance — confirmed from actual PO.1254 invoice"""
    insured_value    = cif_thb * 1.10
    premium          = max(insured_value * INSURANCE_RATE,
                           INSURANCE_MIN_USD * USD_RATE)
    stamp            = 4
    duplicate        = 1
    vat              = premium * 0.07
    total            = premium + stamp + duplicate + vat
    return {
        "insured_value": round(insured_value, 2),
        "premium":       round(premium, 2),
        "stamp":         stamp,
        "duplicate":     duplicate,
        "vat":           round(vat, 2),
        "total":         round(total, 2),
    }

def calc_tax(cif_thb, duty_rate):
    """Thailand import duty + VAT (cascaded)"""
    duty     = cif_thb * duty_rate
    vat_base = cif_thb + duty
    vat      = vat_base * 0.07
    return {
        "duty":     round(duty, 2),
        "vat_base": round(vat_base, 2),
        "vat":      round(vat, 2),
        "total":    round(duty + vat, 2),
    }

def run():
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    sep = "=" * 60
    div = "-" * 60

    print(sep)
    print("  GO CORPORATION — CHINA-THAI LANDED COST CALCULATOR")
    print(sep)
    print(f"  Product  : {PRODUCT_NAME}")
    print(f"  HS Code  : {HS_CODE}  |  Duty: {HS_DUTY_RATE*100:.0f}%")
    print(f"  Mode     : {MODE.upper()}")
    print()

    # EXW price
    if EXW_PRICE_THB > 0:
        exw = EXW_PRICE_THB
    else:
        exw = EXW_PRICE_FOREIGN * FX_RATE_TO_THB
    print(f"  EXW price              : THB {exw:>12,.2f}")

    # Dimensions
    cbm    = calc_cbm(PKG_LENGTH_CM, PKG_WIDTH_CM, PKG_HEIGHT_CM)
    vol_kg = calc_volumetric_air(PKG_LENGTH_CM, PKG_WIDTH_CM, PKG_HEIGHT_CM)
    print(f"  Dimensions             : {PKG_LENGTH_CM} x {PKG_WIDTH_CM} x {PKG_HEIGHT_CM} cm")
    print(f"  Actual weight          : {PKG_ACTUAL_KG} kg")
    print(f"  Volume                 : {cbm:.4f} CBM  |  vol.wt (air): {vol_kg:.1f} kg")
    print()

    # Freight
    freight, cbm_cost, kg_cost, basis = calc_freight(MODE, cbm, PKG_ACTUAL_KG)
    print(f"  --- FREIGHT ({MODE.upper()}) ---")
    if MODE in ("sea", "land"):
        rate_cbm = SEA_RATE_THB_PER_CBM if MODE == "sea" else LAND_RATE_THB_PER_CBM
        rate_kg  = SEA_RATE_THB_PER_KG  if MODE == "sea" else LAND_RATE_THB_PER_KG
        print(f"  Rate (CBM)             : THB {rate_cbm:,.0f}/CBM")
        print(f"  Rate (KGS)             : THB {rate_kg:,.0f}/KG")
        print(f"  CBM cost ({cbm:.4f} CBM) : THB {cbm_cost:>10,.2f}")
        print(f"  KGS cost ({PKG_ACTUAL_KG} kg)      : THB {kg_cost:>10,.2f}")
        arrow = "<<< BILLED"
        if cbm_cost >= kg_cost:
            print(f"  >> Billing basis: CBM  {arrow}  (CBM >= KGS)")
        else:
            print(f"  >> Billing basis: KGS  {arrow}  (KGS > CBM)")
    else:
        cw = max(PKG_ACTUAL_KG, vol_kg)
        print(f"  Chargeable weight      : {cw:.1f} kg  [{basis}]")
        print(f"  Air rate               : THB {AIR_RATE_THB_PER_KG}/kg")
    print(f"  Freight cost           : THB {freight:>12,.2f}")

    # Factory-to-port & oversized
    extras = FACTORY_TO_PORT_THB + OVERSIZED_SURCHARGE_THB
    if extras > 0:
        print(f"  Factory→port           : THB {FACTORY_TO_PORT_THB:>12,.2f}")
        print(f"  Oversized surcharge    : THB {OVERSIZED_SURCHARGE_THB:>12,.2f}")

    # Pre-insurance CIF estimate (used as base for insurance premium)
    cif_pre = exw + freight + extras + CLEARANCE_FEE_THB

    # Insurance
    print()
    print(f"  --- INSURANCE ---")
    if INSURE:
        ins = calc_insurance(cif_pre)
        print(f"  Insured value (CIF×110%): THB {ins['insured_value']:>11,.2f}")
        print(f"  Premium (0.45%)         : THB {ins['premium']:>11,.2f}  [min USD {INSURANCE_MIN_USD}]")
        print(f"  Stamp + duplicate       : THB {ins['stamp'] + ins['duplicate']:>11,.2f}")
        print(f"  VAT (7%)                : THB {ins['vat']:>11,.2f}")
        print(f"  Insurance total         : THB {ins['total']:>11,.2f}")
        ins_total = ins["total"]
    else:
        print(f"  Insurance               : NONE")
        ins_total = 0

    # True CIF
    cif_true = exw + freight + extras + ins_total
    print()
    print(f"  --- IMPORT DUTY & VAT ---")
    print(f"  CIF value (true)       : THB {cif_true:>12,.2f}")
    tax = calc_tax(cif_true, HS_DUTY_RATE)
    print(f"  Import duty ({HS_DUTY_RATE*100:.0f}%)      : THB {tax['duty']:>12,.2f}")
    print(f"  VAT base (CIF+duty)    : THB {tax['vat_base']:>12,.2f}")
    print(f"  VAT (7%)               : THB {tax['vat']:>12,.2f}")
    print(f"  Total import tax       : THB {tax['total']:>12,.2f}")
    print()
    print(f"  Clearance service fee  : THB {CLEARANCE_FEE_THB:>12,.2f}")
    print(f"  Last-mile delivery     : THB {LAST_MILE_THB:>12,.2f}")

    # Landed cost
    landed = exw + freight + extras + ins_total + tax["total"] + CLEARANCE_FEE_THB + LAST_MILE_THB

    print()
    print(div)
    print(f"  TOTAL LANDED COST      : THB {landed:>12,.2f}")
    print(div)
    print()

    # Selling price recommendations
    sell_20 = landed / 0.80
    sell_25 = landed / 0.75
    sell_30 = landed / 0.70
    print(f"  Min sell price (20% GM): THB {sell_20:>12,.2f}")
    print(f"  At 25% GM              : THB {sell_25:>12,.2f}")
    print(f"  At 30% GM              : THB {sell_30:>12,.2f}")
    print()

    # Breakdown table
    print("  COST BREAKDOWN:")
    items = [
        ("EXW product price",     exw),
        ("Freight",               freight),
        ("Factory→port / oversize", extras),
        ("Insurance",             ins_total),
        ("Import duty",           tax["duty"]),
        ("VAT",                   tax["vat"]),
        ("Clearance service fee", CLEARANCE_FEE_THB),
        ("Last-mile delivery",    LAST_MILE_THB),
    ]
    for name, amt in items:
        if amt == 0:
            continue
        pct = (amt / landed * 100) if landed > 0 else 0
        print(f"    {name:<26} THB {amt:>10,.0f}  ({pct:.1f}%)")
    print(div)
    print()
    print("  RATE SOURCES:")
    print("  Sea/Land rates : Gift Somlak rate card (China-Thai, 2025)")
    print("  Air rate       : Logimark PO.1254, MXP->BKK, March 2026")
    print("  Insurance      : Chubb via Logimark, confirmed PO.1254")
    print("  Implied FX     : 32.76 THB/USD (from Gift rate card)")
    print("  NOTE: Rates are from 2025. Get fresh quote before quoting customer.")
    print(sep)

    return landed

if __name__ == "__main__":
    run()
