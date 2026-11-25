"""Deterministyczna sieć placówek i wymiary słownikowe."""

import numpy as np
import pandas as pd

import config as cfg
from kalendarz import build_calendar, lfl_start
from schemat import SCHEMAS


def build_dimensions(rng):
    dimensions = {"dim_data": build_calendar()}
    for name, rows in [
        ("dim_marka", cfg.BRANDS + [cfg.GROUP_BRAND]), ("dim_kraj", cfg.COUNTRIES),
        ("dim_kategoria", cfg.CATEGORIES), ("dim_scenariusz", cfg.SCENARIOS),
        ("dim_konto", cfg.ACCOUNTS),
    ]:
        dimensions[name] = pd.DataFrame(rows, columns=[item[0] for item in SCHEMAS[name]])
    rows, economics = [], []
    names = {code: name for code, name, *_ in cfg.BRANDS}
    country_names = {code: name for code, name, *_ in cfg.COUNTRIES}
    store_ids = []
    for brand, counts in cfg.STORE_COUNTS.items():
        for (country, *_), count in zip(cfg.COUNTRIES, counts, strict=True):
            store_ids.extend(cfg.store_id(brand, country, number) for number in range(1, count + 1))
    store_ids += list(cfg.CLOSURES) + list(cfg.PLANNED_OPENINGS)
    for mpk_id in sorted(store_ids):
        _, brand, country, number = mpk_id.split("-")
        city = cfg.CITIES[country][(int(number) - 1) % len(cfg.CITIES[country])]
        area_range = cfg.DELAYED_STORE_AREA if mpk_id in cfg.DELAYED_OPENINGS else cfg.AREAS[brand]
        area = int(rng.integers(area_range[0] // 10, area_range[1] // 10 + 1) * 10)
        opening = pd.Timestamp(year=int(rng.integers(2008, 2023)),
                               month=int(rng.integers(1, 13)), day=int(rng.integers(1, 29)))
        planned = opening
        if mpk_id in cfg.HISTORICAL_OPENINGS:
            planned = pd.Timestamp(cfg.HISTORICAL_OPENINGS[mpk_id])
            opening = planned + pd.DateOffset(months=int(rng.integers(0, 2)))
        if mpk_id in cfg.DELAYED_OPENINGS:
            planned, opening = map(pd.Timestamp, cfg.DELAYED_OPENINGS[mpk_id])
        if mpk_id in cfg.PLANNED_OPENINGS:
            planned, opening = pd.Timestamp(cfg.PLANNED_OPENINGS[mpk_id]), pd.NaT
        closing = pd.Timestamp(cfg.CLOSURES[mpk_id]) if mpk_id in cfg.CLOSURES else pd.NaT
        rows.append({
            "mpk_id": mpk_id, "mpk_nazwa": f"{names[brand]} {city} {int(number)}",
            "typ_mpk": "Sklep", "kanal": "Sklep", "marka_kod": brand, "kraj_kod": country,
            "miasto": city,
            "format_sklepu": rng.choice(cfg.STORE_FORMATS, p=cfg.STORE_FORMAT_WEIGHTS),
            "powierzchnia_m2": area, "dzial_centrali": "",
            "data_otwarcia_plan": planned, "data_otwarcia": opening, "data_zamkniecia": closing,
            "status": "Planowany" if pd.isna(opening) else "Zamknięty" if pd.notna(closing) else "Aktywny",
            "lfl_od": lfl_start([opening])[0] if pd.notna(opening) else pd.NaT,
        })
        economics.append({
            "mpk_id": mpk_id,
            "annual_base": area * cfg.DENSITY[brand] * cfg.COUNTRY_FACTOR[country]
                           * cfg.SALES_SCALE * rng.uniform(*cfg.STORE_PRODUCTIVITY_RANGE),
            "margin_offset": float(np.clip(rng.normal(0, cfg.STORE_MARGIN_OFFSET_SIGMA),
                                           -cfg.STORE_MARGIN_OFFSET_LIMIT, cfg.STORE_MARGIN_OFFSET_LIMIT)),
        })
    for country, *_ in cfg.COUNTRIES:
        for brand, *_ in cfg.BRANDS:
            mpk_id = cfg.ecom_id(brand, country)
            rows.append({
                "mpk_id": mpk_id, "mpk_nazwa": f"{names[brand]} e-commerce {country_names[country]}",
                "typ_mpk": "E-commerce", "kanal": "E-commerce", "marka_kod": brand,
                "kraj_kod": country, "miasto": "", "format_sklepu": "", "powierzchnia_m2": None,
                "dzial_centrali": "", "data_otwarcia_plan": pd.Timestamp("2018-04-01"),
                "data_otwarcia": pd.Timestamp("2018-04-01"), "data_zamkniecia": pd.NaT,
                "status": "Aktywny", "lfl_od": pd.NaT,
            })
            economics.append({
                "mpk_id": mpk_id,
                "annual_base": 1e9 * cfg.ECOM_BRAND_WEIGHTS[brand] * cfg.ECOM_COUNTRY_WEIGHTS[country],
                "margin_offset": float(np.clip(rng.normal(0, cfg.ECOM_MARGIN_OFFSET_SIGMA),
                                               -cfg.ECOM_MARGIN_OFFSET_LIMIT, cfg.ECOM_MARGIN_OFFSET_LIMIT)),
            })
    departments = [(f"HQ-{code}", name, "GRP") for code, name in cfg.DEPARTMENTS]
    departments += [(f"HQ-MKT-{brand}", "Marketing", brand) for brand, *_ in cfg.BRANDS]
    for mpk_id, department, brand in departments:
        rows.append({
            "mpk_id": mpk_id,
            "mpk_nazwa": f"Centrala {department}" + (f" {names[brand]}" if brand != "GRP" else ""),
            "typ_mpk": "Centrala", "kanal": "Centrala", "marka_kod": brand, "kraj_kod": "PL",
            "miasto": "", "format_sklepu": "", "powierzchnia_m2": None,
            "dzial_centrali": department, "data_otwarcia_plan": pd.Timestamp("2008-01-01"),
            "data_otwarcia": pd.Timestamp("2008-01-01"), "data_zamkniecia": pd.NaT,
            "status": "Aktywny", "lfl_od": pd.NaT,
        })
    dimensions["dim_mpk"] = pd.DataFrame(rows)
    dimensions["dim_mpk"]["powierzchnia_m2"] = dimensions["dim_mpk"]["powierzchnia_m2"].astype("Int64")
    return dimensions, pd.DataFrame(economics).set_index("mpk_id")
