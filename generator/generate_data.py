"""Uruchomienie: python generator/generate_data.py."""

import sys
import time

import numpy as np
import pandas as pd

import config as cfg
from eksport import write_dictionary, write_excel, write_tables
from kalendarz import build_plan_calendar
from model import (build_actual, build_aggregate, build_budget, build_categories, build_daily,
                   build_forecast, build_fx, build_plan, monthly_profile, monthly_sales, sales_profile)
from odpowiedzi import write_answers
from schemat import SCHEMAS, normalize
from wymiary import build_dimensions


def generate():
    start = time.perf_counter()
    rng = np.random.default_rng(cfg.SEED)
    tables, economics = build_dimensions(rng)
    mpk = tables["dim_mpk"]
    actual_days = sales_profile(tables["dim_data"], mpk, economics)
    planned_days = sales_profile(tables["dim_data"], mpk, economics, planned=True)
    actual_profile = monthly_profile(actual_days, mpk)
    planned_profile = monthly_profile(planned_days, mpk, planned=True)
    daily = build_daily(actual_days, mpk, economics, rng)
    monthly = monthly_sales(daily)
    act = build_actual(monthly, mpk, actual_profile)
    bud = build_budget(act, monthly, mpk, actual_profile, planned_profile)
    fc = build_forecast(act, bud, mpk, actual_profile, planned_profile)
    tables["fakt_sprzedaz_dzienna"] = daily
    tables["fakt_sprzedaz_kategorie_mies"] = build_categories(daily, mpk)
    tables["fakt_pnl"] = pd.concat([act, bud, fc], ignore_index=True)
    tables["fakt_kursy_walut"] = build_fx(rng)
    tables["agg_sprzedaz_mies"] = build_aggregate(tables["fakt_pnl"], mpk)
    tables["plan_kalendarz"] = build_plan_calendar(tables["dim_data"])
    tables["ref_plan_2027_28_rozklad"], targets = build_plan(tables["agg_sprzedaz_mies"])
    tables = {name: normalize(name, tables[name]) for name in SCHEMAS}
    write_tables(tables)
    write_excel(tables, targets)
    summary, metrics = write_answers(tables)
    write_dictionary(tables, metrics)
    elapsed = time.perf_counter() - start
    total_bytes = sum(path.stat().st_size for path in cfg.DATA_DIR.rglob("*") if path.is_file())
    print("Tabela                                      Wiersze")
    for name, table in tables.items():
        print(f"{name:42s} {len(table):>9,d}")
    print(f"Rozmiar dane: {total_bytes / 1_000_000:.2f} MB ({total_bytes:,} bajtów)")
    print(f"Czas generowania: {elapsed:.2f} s")
    print("Klucz odpowiedzi, pytania 1 do 12:")
    for nr in range(1, 13):
        print(f"{nr}. {summary[nr]}")
    if elapsed >= 180:
        raise RuntimeError("Generowanie przekroczyło limit 180 sekund.")
    if total_bytes >= 60_000_000:
        raise RuntimeError("Rozmiar danych przekroczył limit 60 MB.")
    return tables


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    generate()
