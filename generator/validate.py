"""Walidacja bez pytest; opcja --determinism uruchamia generator dwukrotnie."""

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from openpyxl import load_workbook

import config as cfg
from kalendarz import build_calendar, easter, fiscal_year, foreign_closed, lfl_start, month_start
from model import active_fraction, monthly_profile, ramp_factor, sales_profile, utilities_season
from odpowiedzi import QUESTIONS, make_answers
from schemat import ARROW_TYPES, GRAINS, SCHEMAS, normalize
from wymiary import build_dimensions


class Results:
    def __init__(self):
        self.rows = []

    def check(self, name, passed, value, expected):
        self.rows.append({"test": name, "wartosc": str(value), "oczekiwane": str(expected),
                          "wynik": "PASS" if bool(passed) else "FAIL"})

    def range(self, name, value, low, high, unit=""):
        self.check(name, np.isfinite(value) and low <= value <= high,
                   f"{value:.6f}{unit}", f"{low:g} do {high:g}{unit}")

    def zero(self, name, value, tolerance=0):
        self.check(name, np.isfinite(value) and abs(value) <= tolerance,
                   f"{value:.6g}", f"0, tolerancja {tolerance:g}")

    def print(self):
        frame = pd.DataFrame(self.rows)
        widths = {column: max(len(column), frame[column].str.len().max()) for column in frame.columns}
        header = " | ".join(column.ljust(widths[column]) for column in frame.columns)
        print(header)
        print("-" * len(header))
        for row in frame.itertuples(index=False, name=None):
            print(" | ".join(str(value).ljust(widths[column]) for column, value in zip(frame.columns, row)))
        print(f"Wynik: {sum(frame.wynik.eq('PASS'))}/{len(frame)} PASS")
        frame.to_csv(cfg.ROOT / "generator" / "wyniki_walidacji.csv", index=False,
                     encoding="utf-8-sig", lineterminator="\n")
        return bool(frame.wynik.eq("PASS").all())


def maximum_error(left, right):
    aligned = pd.concat([left.rename("left"), right.rename("right")], axis=1)
    if aligned.isna().any().any() or not len(aligned):
        return float("inf")
    return float((aligned["left"] - aligned["right"]).abs().max())


def read_tables(results):
    expected = {f"{name}.parquet" for name in SCHEMAS}
    actual = {path.name for path in (cfg.DATA_DIR / "parquet").glob("*.parquet")}
    results.check("Pliki Parquet", actual == expected, len(actual), f"{len(expected)} nazw zgodnych ze schematem")
    tables = {}
    for name, columns in SCHEMAS.items():
        file = cfg.DATA_DIR / "parquet" / f"{name}.parquet"
        schema = pq.read_schema(file)
        correct = schema.names == [column for column, _, _ in columns]
        correct &= all(schema.field(column).type == ARROW_TYPES[kind] for column, kind, _ in columns)
        results.check(f"Kontrakt {name}", correct, len(schema.names), "dokładne kolumny i typy Arrow")
        tables[name] = normalize(name, pd.read_parquet(file))
    duplicate_count = sum(frame.duplicated(GRAINS[name]).sum() for name, frame in tables.items())
    results.zero("Unikalność wszystkich ziaren", duplicate_count)
    required_nulls = 0
    optional = {
        "dim_data": {"nazwa_swieta"},
        "dim_mpk": {"powierzchnia_m2", "data_otwarcia", "data_zamkniecia", "lfl_od"},
    }
    for name, frame in tables.items():
        required = [column for column in frame if column not in optional.get(name, set())]
        required_nulls += frame[required].isna().sum().sum()
    results.zero("Brak nulli w wymaganych kolumnach", required_nulls)
    codecs = set()
    for name in SCHEMAS:
        meta = pq.ParquetFile(cfg.DATA_DIR / "parquet" / f"{name}.parquet").metadata
        for group in range(meta.num_row_groups):
            codecs.update(meta.row_group(group).column(col).compression for col in range(meta.num_columns))
    results.check("Kompresja Parquet", codecs == {"SNAPPY"}, ", ".join(sorted(codecs)), "SNAPPY")
    return tables


def check_dimensions(tables, results):
    mpk, cal = tables["dim_mpk"], tables["dim_data"]
    expected = normalize("dim_data", build_calendar())
    results.check("Pełny kalendarz i wszystkie atrybuty", cal.equals(expected), len(cal), f"{len(expected)} poprawnych dni")
    results.check("Daty Wielkanocy", easter(2023).isoformat() == "2023-04-09" and
                  easter(2024).isoformat() == "2024-03-31" and easter(2025).isoformat() == "2025-04-20"
                  and easter(2026).isoformat() == "2026-04-05" and easter(2027).isoformat() == "2027-03-28",
                  "2023, 2024, 2025, 2026, 2027", "09.04, 31.03, 20.04, 05.04, 28.03")
    christmas = cal.loc[cal["data"].dt.month.eq(12) & cal["data"].dt.day.eq(24)].set_index("rok")["czy_swieto_pl"]
    results.check("Wigilia wolna od 2025", (~christmas.loc[[2023, 2024]]).all()
                  and christmas.loc[[2025, 2026, 2027]].all(), christmas.astype(int).tolist(), "0, 0, 1, 1, 1")
    shop = mpk.loc[mpk["typ_mpk"].eq("Sklep")]
    active = shop.loc[shop["status"].eq("Aktywny")]
    expected_network = {(brand, country): count for brand, counts in cfg.STORE_COUNTS.items()
                        for (country, *_), count in zip(cfg.COUNTRIES, counts, strict=True)}
    counts = active.groupby(["marka_kod", "kraj_kod"]).size()
    network_ok = all(counts.get(key, 0) == value for key, value in expected_network.items())
    results.check("Sieć aktywna na 08.12.2026", network_ok, len(active), f"{sum(expected_network.values())} sklepów, liczebności SPEC")
    expected_ec = len(cfg.BRANDS) * len(cfg.COUNTRIES)
    expected_hq = len(cfg.DEPARTMENTS) + len(cfg.BRANDS)
    results.check("Kanały i centrala", mpk["typ_mpk"].value_counts().get("E-commerce", 0) == expected_ec
                  and mpk["typ_mpk"].value_counts().get("Centrala", 0) == expected_hq,
                  f"{sum(mpk.typ_mpk.eq('E-commerce'))}, {sum(mpk.typ_mpk.eq('Centrala'))}",
                  f"{expected_ec} E-commerce, {expected_hq} Centrala")
    expected_dimensions = {
        "dim_marka": cfg.BRANDS + [cfg.GROUP_BRAND], "dim_kraj": cfg.COUNTRIES,
        "dim_kategoria": cfg.CATEGORIES, "dim_scenariusz": cfg.SCENARIOS, "dim_konto": cfg.ACCOUNTS,
    }
    correct = True
    for name, rows in expected_dimensions.items():
        correct &= tables[name].equals(normalize(name, pd.DataFrame(rows, columns=tables[name].columns)))
    results.check("Domeny wymiarów i GRP", correct, "5/6/9/3/13", "pełne słowniki SPEC")
    lower = shop["marka_kod"].map({brand: limits[0] for brand, limits in cfg.AREAS.items()})
    upper = shop["marka_kod"].map({brand: limits[1] for brand, limits in cfg.AREAS.items()})
    results.check("Powierzchnie sklepów i null poza sklepami",
                  shop["powierzchnia_m2"].between(lower, upper).all()
                  and mpk.loc[~mpk.typ_mpk.eq("Sklep"), "powierzchnia_m2"].isna().all(),
                  f"{len(shop)} sklepów", "zakresy powierzchni według marki")
    formats_ok = shop.format_sklepu.isin(["Centrum handlowe", "Park handlowy", "Ulica handlowa"]).all()
    other = mpk.loc[~mpk.typ_mpk.eq("Sklep")]
    formats_ok &= other.miasto.eq("").all() and other.format_sklepu.eq("").all()
    formats_ok &= mpk.loc[~mpk.typ_mpk.eq("Centrala"), "dzial_centrali"].eq("").all()
    results.check("Formaty i atrybuty nieużywane poza MPK", formats_ok, "Sklep, E-commerce, Centrala",
                  "właściwe domeny i puste atrybuty nieadekwatne")
    open_shops = shop.loc[shop["data_otwarcia"].notna()]
    dates_ok = (open_shops["lfl_od"].to_numpy() == lfl_start(open_shops["data_otwarcia"]).to_numpy()).all()
    dates_ok &= mpk.loc[~mpk.typ_mpk.eq("Sklep"), "lfl_od"].isna().all()
    results.check("Definicja lfl_od", dates_ok, len(open_shops), "12 pełnych miesięcy i pierwszy dzień miesiąca")
    planned = shop.loc[shop["status"].eq("Planowany")]
    planned_ok = len(planned) == 7 and planned["data_otwarcia"].isna().all() and planned["lfl_od"].isna().all()
    planned_ok &= planned["data_otwarcia_plan"].between(cfg.PLAN_START, cfg.CALENDAR_END).all()
    planned_ok &= planned.groupby("marka_kod").size().to_dict() == {"AUR": 1, "LUM": 2, "VEN": 4}
    results.check("Siedem planowanych otwarć RF 2027/28", planned_ok, len(planned), "VEN 4, LUM 2, AUR 1, rzeczywiste daty null")
    closed = shop.loc[shop["status"].eq("Zamknięty")]
    closure_ok = len(closed) == 5 and sum(closed.marka_kod.eq("KRO") & closed.data_zamkniecia.between("2025-04-01", "2026-06-30")) == 4
    closure_ok &= sum(closed.marka_kod.eq("LUM") & closed.data_zamkniecia.dt.year.eq(2025)) == 1
    results.check("Historia pięciu zamknięć", closure_ok, len(closed), "4 KRO od kwietnia 2025 do czerwca 2026, 1 LUM w 2025")
    historical = shop.loc[shop["mpk_id"].isin(cfg.HISTORICAL_OPENINGS)]
    delays = (historical.data_otwarcia.dt.year - historical.data_otwarcia_plan.dt.year) * 12 \
        + historical.data_otwarcia.dt.month - historical.data_otwarcia_plan.dt.month
    results.check("Pozostałe otwarcia historyczne", len(historical) == 13 and delays.between(0, 1).all()
                  and historical.groupby("marka_kod").size().to_dict() == {"AUR": 2, "LUM": 3, "VEN": 8},
                  len(historical), "8 VEN, 3 LUM, 2 AUR, przesunięcie najwyżej miesiąc")
    ramp_dates = pd.to_datetime(["2026-07-15", "2026-10-15", "2027-01-15", "2027-02-15"])
    ramp = ramp_factor(ramp_dates, pd.to_datetime(["2026-07-15"] * 4))
    results.check("Rozruch od 70% do 100% w sześć miesięcy",
                  np.isclose(ramp[0], .70) and .84 < ramp[1] < .86 and np.isclose(ramp[2:], 1.).all()
                  and np.all(np.diff(ramp) >= 0), ", ".join(f"{value:.2%}" for value in ramp),
                  "70%, około 85%, 100%, 100%")


def check_keys_values(tables, results):
    dims = {
        "mpk_id": ("dim_mpk", "mpk_id"), "marka_kod": ("dim_marka", "marka_kod"),
        "kraj_kod": ("dim_kraj", "kraj_kod"), "kategoria_kod": ("dim_kategoria", "kategoria_kod"),
        "scenariusz_kod": ("dim_scenariusz", "scenariusz_kod"), "konto_id": ("dim_konto", "konto_id"),
    }
    invalid = 0
    for name, frame in tables.items():
        for column, (dimension, key) in dims.items():
            if column in frame and name != dimension:
                invalid += (~frame[column].isin(tables[dimension][key])).sum()
        date_key = "data" if name == "fakt_sprzedaz_dzienna" else "miesiac"
        if not name.startswith("dim_") and date_key in frame:
            invalid += (~frame[date_key].isin(tables["dim_data"]["data"])).sum()
            if date_key == "miesiac":
                invalid += (~frame[date_key].dt.day.eq(1)).sum()
    results.zero("Integralność wszystkich kluczy", invalid)
    invalid_money, decimals = 0, 0.
    for frame in tables.values():
        for column in frame:
            if column.endswith("_pln"):
                values = frame[column]
                invalid_money += ((values < 0) | ~np.isfinite(values)).sum()
                if column != "kurs_sredni_pln":
                    decimals = max(decimals, float((values - values.round(2)).abs().max()))
    results.zero("Kwoty nieujemne i skończone", invalid_money)
    results.zero("Kwoty zaokrąglone do groszy", decimals, .000001)
    non_sales = ["fakt_sprzedaz_kategorie_mies", "agg_sprzedaz_mies", "ref_plan_2027_28_rozklad"]
    no_grp = all(not tables[name]["marka_kod"].eq("GRP").any() for name in non_sales)
    results.check("GRP wyłącznie poza sprzedażą", no_grp, "3 tabele sprzedażowe", "brak GRP")
    cat = tables["fakt_sprzedaz_kategorie_mies"]
    bad_categories = ((cat.kategoria_kod.eq("SR") & ~cat.marka_kod.eq("VEN")) |
                      (cat.marka_kod.eq("KRO") & ~cat.kategoria_kod.isin(["OB", "AK"]))).sum()
    results.zero("Domeny SR i asortyment KRO", bad_categories)
    expected_pairs = set(zip(tables["dim_mpk"].loc[~tables["dim_mpk"].typ_mpk.eq("Centrala"), "marka_kod"],
                             tables["dim_mpk"].loc[~tables["dim_mpk"].typ_mpk.eq("Centrala"), "kraj_kod"]))
    lum_shops = tables["dim_mpk"].loc[tables["dim_mpk"].typ_mpk.eq("Sklep") & tables["dim_mpk"].marka_kod.eq("LUM")]
    results.check("Brak sklepów Lumi w SE i DK", not lum_shops.kraj_kod.isin(["SE", "DK"]).any(),
                  len(expected_pairs), "Lumi w SE i DK wyłącznie E-commerce")
    d = tables["fakt_sprzedaz_dzienna"]
    results.zero("Dodatnie paragony i sztuki", ((d.liczba_paragonow < 1) | (d.liczba_sztuk < d.liczba_paragonow)).sum())
    fx = tables["fakt_kursy_walut"]
    fx_months = len(pd.date_range(cfg.DAILY_START, cfg.FORECAST_START, freq="MS"))
    fx_ok = len(fx) == fx_months * len(cfg.FX_BASE) and set(fx.waluta) == set(cfg.FX_BASE)
    fx_ok &= fx.miesiac.min() == pd.Timestamp(cfg.DAILY_START) and fx.miesiac.max() == pd.Timestamp(cfg.FORECAST_START)
    deviation = (fx.kurs_sredni_pln / fx.waluta.map(cfg.FX_BASE) - 1.).abs().max()
    results.check("Kursy i zakres miesięcy", fx_ok and deviation < .10, f"{len(fx)} wierszy; maks. odchylenie {deviation:.3%}",
                  f"{fx_months} miesięcy × {len(cfg.FX_BASE)} waluty, odchylenie od bazy <10%")


def check_daily_reconciliation(tables, results):
    daily = tables["fakt_sprzedaz_dzienna"]
    mpk, cal = tables["dim_mpk"], tables["dim_data"]
    joined = daily.merge(mpk, on="mpk_id", validate="many_to_one").merge(
        cal[["data", "czy_dzien_handlowy_pl"]], on="data", validate="many_to_one")
    bad_pl = joined.typ_mpk.eq("Sklep") & joined.kraj_kod.eq("PL") & ~joined.czy_dzien_handlowy_pl
    results.zero("Polskie sklepy w dniach zamknięcia", bad_pl.sum())
    bad_foreign = joined.typ_mpk.eq("Sklep") & ~joined.kraj_kod.eq("PL") & foreign_closed(joined.data)
    results.zero("Zagraniczne sklepy w dniach zamknięcia", bad_foreign.sum())
    lifecycle = joined.typ_mpk.eq("Centrala") | joined.status.eq("Planowany") \
        | (joined.data < joined.data_otwarcia) | (joined.data_zamkniecia.notna() & (joined.data > joined.data_zamkniecia))
    results.zero("Sprzedaż poza okresem działalności", lifecycle.sum())
    expected_ec = len(pd.date_range(cfg.DAILY_START, cfg.DAILY_END)) * len(cfg.BRANDS) * len(cfg.COUNTRIES)
    ec_count = sum(joined.typ_mpk.eq("E-commerce"))
    results.check("E-commerce codziennie", ec_count == expected_ec, ec_count, expected_ec)
    results.check("Zakres danych dziennych", daily.data.min() == pd.Timestamp(cfg.DAILY_START)
                  and daily.data.max() == pd.Timestamp(cfg.DAILY_END), f"{daily.data.min().date()} do {daily.data.max().date()}",
                  f"{cfg.DAILY_START} do {cfg.DAILY_END}")
    basket = joined.marka_kod.map(cfg.BASKET) * np.where(joined.typ_mpk.eq("E-commerce"), cfg.ECOM_BASKET_FACTOR, 1.)
    expected_receipts = np.maximum(1, np.rint(joined.sprzedaz_netto_pln / basket)).astype(np.int64)
    results.zero("Paragony ze sprzedaży i średniego koszyka",
                 np.max(np.abs(joined.liczba_paragonow.to_numpy() - expected_receipts)))
    closed = joined.loc[joined.data <= cfg.CLOSED_END].copy()
    closed["miesiac"] = month_start(closed.data)
    monthly = closed.groupby(["miesiac", "mpk_id"])[["sprzedaz_netto_pln", "koszt_wlasny_pln"]].sum()
    pnl = tables["fakt_pnl"]
    act = pnl.loc[pnl.scenariusz_kod.eq("ACT")]
    for account, column in [("4010", "sprzedaz_netto_pln"), ("4510", "koszt_wlasny_pln")]:
        booked = act.loc[act.konto_id.eq(account)].set_index(["miesiac", "mpk_id"]).kwota_pln
        results.zero(f"Uzgodnienie ACT {account} do dni", maximum_error(monthly[column], booked), 1.)
    keys = ["miesiac", "marka_kod", "kraj_kod", "kanal"]
    daily_totals = closed.groupby(keys)[["sprzedaz_netto_pln", "koszt_wlasny_pln", "liczba_sztuk"]].sum()
    cat_totals = tables["fakt_sprzedaz_kategorie_mies"].groupby(keys)[daily_totals.columns].sum()
    for column in daily_totals:
        results.zero(f"Kategorie: {column}", maximum_error(daily_totals[column], cat_totals[column]),
                     0 if column == "liczba_sztuk" else 1.)
    full_category = tables["fakt_sprzedaz_kategorie_mies"].loc[
        fiscal_year(tables["fakt_sprzedaz_kategorie_mies"].miesiac) == 2025
    ]
    category_month = full_category.groupby(["miesiac", "kategoria_kod"]).sprzedaz_netto_pln.sum().unstack()
    category_share = category_month.div(category_month.sum(axis=1), axis=0)
    winter = category_share.index.month.isin([10, 11, 12, 1])
    summer = category_share.index.month.isin([5, 6, 7, 8])
    results.range("Kategorie: udział OW jesienią i zimą", category_share.loc[winter, "OW"].mean() * 100., 13., 19., "%")
    results.range("Kategorie: udział OW latem", category_share.loc[summer, "OW"].mean() * 100., 2., 4., "%")
    category_season_ok = category_share.loc[winter, "SW"].mean() > category_share.loc[summer, "SW"].mean()
    category_season_ok &= category_share.loc[summer, ["TS", "SU"]].sum(axis=1).mean() \
        > category_share.loc[winter, ["TS", "SU"]].sum(axis=1).mean()
    december = category_share.index.month == 12
    category_season_ok &= category_share.loc[december, ["AK", "BI"]].sum(axis=1).mean() \
        > category_share.loc[~december, ["AK", "BI"]].sum(axis=1).mean()
    results.check("Kategorie: sezonowość pozostałego asortymentu", category_season_ok,
                  "SW, TS, SU, AK, BI", "SW zimą, TS i SU latem, AK i BI w grudniu")
    agg = tables["agg_sprzedaz_mies"]
    source = pnl.loc[pnl.konto_id.isin(["4010", "4510"])].merge(mpk, on="mpk_id")
    agg_keys = keys + ["scenariusz_kod"]
    pivot = source.pivot_table(index=agg_keys, columns="konto_id", values="kwota_pln", aggfunc="sum")
    result = agg.set_index(agg_keys)
    error = max(maximum_error(result.sprzedaz_netto_pln, pivot["4010"]),
                maximum_error(result.koszt_wlasny_pln, pivot["4510"]))
    results.zero("Agregat do P&L, wszystkie scenariusze", error, .01)
    planned_ids = set(mpk.loc[mpk.status.eq("Planowany"), "mpk_id"])
    results.zero("Brak faktów planowanych sklepów 2027/28",
                 pnl.mpk_id.isin(planned_ids).sum() + daily.mpk_id.isin(planned_ids).sum())


def allowed_accounts(row):
    if row.typ_mpk == "Sklep":
        return ["4010", "4510", "5110", "5120", "5130", "5910", "6010"]
    if row.typ_mpk == "E-commerce":
        return ["4010", "4510", "5210", "5220", "5230"]
    accounts = ["5410", "5420", "5910", "6010"]
    if row.dzial_centrali == "Marketing":
        accounts.append("5210")
    if row.dzial_centrali == cfg.HQ_LOGISTICS_DEPARTMENT:
        accounts.append("5310")
    return accounts


def check_scenarios(tables, results):
    pnl, mpk = tables["fakt_pnl"], tables["dim_mpk"]
    allowed = {row.mpk_id: set(allowed_accounts(row)) for row in mpk.itertuples()}
    allowed_pairs = pd.MultiIndex.from_tuples([(mpk_id, account) for mpk_id, accounts in allowed.items() for account in accounts])
    observed_pairs = pd.MultiIndex.from_frame(pnl[["mpk_id", "konto_id"]])
    results.zero("Konta właściwe dla rodzaju MPK", (~observed_pairs.isin(allowed_pairs)).sum())
    cases = [
        ("ACT", pd.date_range(cfg.DAILY_START, cfg.CLOSED_END, freq="MS"), "data_otwarcia"),
        ("BUD", pd.date_range("2024-04-01", "2027-03-01", freq="MS"), "data_otwarcia_plan"),
        ("FC", pd.date_range("2026-04-01", "2027-03-01", freq="MS"), "data_otwarcia"),
    ]
    for scenario, months, opening_column in cases:
        expected = set()
        for row in mpk.itertuples():
            opening, closing = getattr(row, opening_column), row.data_zamkniecia
            if pd.isna(opening):
                continue
            for month in months:
                if opening <= month + pd.offsets.MonthEnd(0) and (pd.isna(closing) or closing >= month):
                    expected.update((month, row.mpk_id, account) for account in allowed[row.mpk_id])
        actual = set(pnl.loc[pnl.scenariusz_kod.eq(scenario), ["miesiac", "mpk_id", "konto_id"]].itertuples(index=False, name=None))
        results.zero(f"Kompletność {scenario}, miesiąc × MPK × konto", len(expected.symmetric_difference(actual)))
    keys = ["miesiac", "mpk_id", "konto_id"]
    act = pnl.loc[pnl.scenariusz_kod.eq("ACT") & pnl.miesiac.between("2026-04-01", "2026-11-01")].set_index(keys).kwota_pln
    fc = pnl.loc[pnl.scenariusz_kod.eq("FC") & pnl.miesiac.between("2026-04-01", "2026-11-01")].set_index(keys).kwota_pln
    results.zero("FC kwiecień do listopada jest kopią ACT", maximum_error(act, fc), 0.)


def check_cost_rules(tables, results):
    pnl = tables["fakt_pnl"]
    actual = pnl.loc[pnl.scenariusz_kod.eq("ACT")]
    wide = actual.pivot(index=["miesiac", "mpk_id"], columns="konto_id", values="kwota_pln").reset_index()
    wide = wide.merge(tables["dim_mpk"], on="mpk_id")
    stores = wide.loc[wide.typ_mpk.eq("Sklep")].copy()
    age = fiscal_year(stores.miesiac) - 2023
    fraction = active_fraction(stores.miesiac, stores.data_otwarcia, stores.data_zamkniecia)
    nominal = stores.powierzchnia_m2.astype(float) * stores.marka_kod.map(cfg.DENSITY) \
        * stores.kraj_kod.map(cfg.COUNTRY_FACTOR) * cfg.SALES_SCALE / 12. * fraction
    expected = {
        "5110": nominal * cfg.STORE_PAYROLL_FIXED_SHARE * stores.kraj_kod.map(cfg.WAGE_COUNTRY_INDEX)
        * (1. + cfg.WAGE_GROWTH) ** age + cfg.STORE_PAYROLL_VARIABLE_SHARE * stores["4010"],
        "5130": nominal * cfg.STORE_UTILITIES_SHARE * utilities_season(stores.miesiac.dt.month)
        * (1. + cfg.UTILITY_GROWTH) ** age,
        "5910": cfg.STORE_OTHER_SHARE * stores["4010"] + stores.powierzchnia_m2.astype(float)
        * cfg.STORE_OTHER_FIXED_PER_M2 * fraction * (1. + cfg.HQ_OTHER_GROWTH) ** age,
        "6010": stores.powierzchnia_m2.astype(float) * cfg.STORE_DEPRECIATION_PER_M2 * fraction,
    }
    rent_index, cumulative = {}, 1.
    for year, factor in cfg.RENT_INDEX_ACT.items():
        cumulative *= factor
        rent_index[year] = cumulative
    rent_factor = pd.Series(fiscal_year(stores.miesiac), index=stores.index).map(rent_index)
    rent_factor *= np.where(stores.marka_kod.eq(cfg.RENT_SHOCK_BRAND) & stores.kraj_kod.eq(cfg.RENT_SHOCK_COUNTRY) &
                            (stores.miesiac >= cfg.RENT_SHOCK_START),
                            (1. + cfg.RENT_SHOCK_INCREASE) / cfg.RENT_INDEX_ACT[2026], 1.)
    rent_expected = nominal * cfg.STORE_RENT_SHARE * rent_factor
    results.zero("Czynsze ACT: indeksacja w kwietniu i renegocjacja",
                 float((stores["5120"] - rent_expected).abs().max()), .011)
    error = max(float((stores[account] - target).abs().max()) for account, target in expected.items())
    results.zero("Koszty sklepów: płace, media, pozostałe, amortyzacja", error, .011)
    ec = wide.loc[wide.typ_mpk.eq("E-commerce")].copy()
    daily = tables["fakt_sprzedaz_dzienna"]
    orders = daily.assign(miesiac=month_start(daily.data)).groupby(["miesiac", "mpk_id"]).liczba_paragonow.sum()
    ec_index = pd.MultiIndex.from_frame(ec[["miesiac", "mpk_id"]])
    rate = np.where(ec.kraj_kod.eq("PL"), cfg.ORDER_COST_PL_2023, cfg.ORDER_COST_OTHER_2023) \
        * (1. + cfg.ORDER_COST_GROWTH) ** (fiscal_year(ec.miesiac) - 2023)
    rate *= np.where(ec.kraj_kod.eq(cfg.ORDER_SHOCK_COUNTRY) & (ec.miesiac >= cfg.ORDER_SHOCK_START), 1. + cfg.ORDER_SHOCK_INCREASE, 1.)
    ec_errors = [
        (ec["5210"] - ec["4010"] * cfg.ECOM_MARKETING_SHARE).abs().max(),
        (ec["5230"] - ec["4010"] * cfg.ECOM_PAYMENT_SHARE).abs().max(),
        np.max(np.abs(ec["5220"].to_numpy() - orders.reindex(ec_index).to_numpy() * rate)),
    ]
    results.zero("Koszty e-commerce według zamówień i sprzedaży", max(ec_errors), .011)
    stores_total = stores.groupby("miesiac")["4010"].sum()
    logistics = actual.loc[actual.konto_id.eq("5310")].set_index("miesiac").kwota_pln
    results.zero("Logistyka magazynowa = 2,8% sprzedaży sklepów",
                 maximum_error(logistics, stores_total * cfg.HQ_LOGISTICS_STORE_SHARE), .011)
    fy25 = wide.loc[fiscal_year(wide.miesiac) == 2025]
    group_sales = fy25["4010"].sum()
    hq_cost = fy25.loc[fy25.typ_mpk.eq("Centrala"), ["5210", "5310", "5410", "5420", "5910", "6010"]].sum().sum()
    results.range("Koszty centrali RF 2025/26", hq_cost / group_sales * 100., 9., 12., "%")
    it = actual.loc[actual.konto_id.eq("5420")]
    it_share = it.loc[it.mpk_id.eq(cfg.HQ_IT_MPK), "kwota_pln"].sum() / it.kwota_pln.sum()
    results.range("IT i licencje głównie w MPK IT", it_share * 100., 85., 100., "%")


def check_stories(tables, results):
    pnl, mpk, daily = tables["fakt_pnl"], tables["dim_mpk"], tables["fakt_sprzedaz_dzienna"]
    joined = pnl.merge(mpk, on="mpk_id")
    selected = joined.loc[joined.konto_id.eq("4010") & joined.miesiac.between("2026-04-01", "2026-09-01")
                          & joined.marka_kod.eq(cfg.DELAYED_BRAND) & joined.kraj_kod.eq(cfg.DELAYED_COUNTRY)]
    values = selected.groupby("scenariusz_kod").kwota_pln.sum()
    results.range("Historia 1: Vento DE 1H ACT/BUD", (values.ACT / values.BUD - 1.) * 100., -20., -9., "%")
    delayed = mpk.loc[mpk.mpk_id.isin(cfg.DELAYED_OPENINGS)]
    months = (delayed.data_otwarcia.dt.year - delayed.data_otwarcia_plan.dt.year) * 12 \
        + delayed.data_otwarcia.dt.month - delayed.data_otwarcia_plan.dt.month
    delay_ok = len(delayed) == 4 and months.eq(3).all() \
        and delayed.data_otwarcia_plan.between("2026-05-01", "2026-06-30").all() \
        and delayed.data_otwarcia.between("2026-08-01", "2026-09-30").all()
    results.check("Historia 1: daty czterech opóźnień", delay_ok, f"{len(delayed)} sklepów, {months.min()} do {months.max()} mies.",
                  "plan maj i czerwiec, ACT sierpień i wrzesień, opóźnienie 3 mies.")
    before_actual = joined.loc[joined.mpk_id.isin(delayed.mpk_id) & joined.konto_id.eq("4010")
                              & joined.scenariusz_kod.eq("BUD")
                              & (joined.miesiac < joined.data_otwarcia.dt.to_period("M").dt.to_timestamp())]
    results.check("Historia 1: BUD przed rzeczywistym otwarciem", before_actual.mpk_id.nunique() == 4
                  and before_actual.kwota_pln.gt(0).all(), before_actual.mpk_id.nunique(), "4 MPK z dodatnim BUD")
    rents = joined.loc[joined.miesiac.between("2026-04-01", "2026-11-01") & joined.konto_id.eq("5120")
                       & joined.marka_kod.eq(cfg.RENT_SHOCK_BRAND) & joined.kraj_kod.eq(cfg.RENT_SHOCK_COUNTRY)] \
        .groupby("scenariusz_kod").kwota_pln.sum()
    results.range("Historia 2: czynsze Aurea AT ACT/BUD", (rents.ACT / rents.BUD - 1.) * 100., 9., 14., "%")
    for label, start, end in [("październik", "2026-10-01", "2026-10-01"),
                             ("listopad", "2026-11-01", "2026-11-01"),
                             ("łącznie", "2026-10-01", "2026-11-01")]:
        log = joined.loc[joined.miesiac.between(start, end) & joined.konto_id.eq("5220")
                         & joined.mpk_id.str.match(r"^EC-.+-DE$")].groupby("scenariusz_kod").kwota_pln.sum()
        results.range(f"Historia 3: logistyka DE {label} ACT/BUD", (log.ACT / log.BUD - 1.) * 100., 15., 30., "%")
    cat = tables["fakt_sprzedaz_kategorie_mies"]
    ow = cat.loc[cat.kategoria_kod.eq("OW") & cat.miesiac.dt.month.eq(11)].groupby(cat.miesiac.dt.year).sprzedaz_netto_pln.sum()
    results.range("Historia 4: odzież wierzchnia listopad r/r", (ow[2026] / ow[2025] - 1.) * 100., -35., -20., "%")
    black_fridays = tables["dim_data"].loc[tables["dim_data"].czy_black_friday, "data"]
    sept = daily.loc[daily.data.dt.month.eq(11) & daily.data.dt.year.isin([2025, 2026])
                     & ~daily.data.isin(black_fridays)].copy()
    sept["year"] = sept.data.dt.year
    margins = sept.groupby(["mpk_id", "year"])[["sprzedaz_netto_pln", "koszt_wlasny_pln"]].sum()
    margins["margin"] = 1. - margins.koszt_wlasny_pln / margins.sprzedaz_netto_pln
    margin_wide = margins["margin"].unstack().dropna()
    results.zero("Historia 4: listopad bez Black Friday, marża niższa o 1 pp",
                 float(((margin_wide[2026] - margin_wide[2025]) + .01).abs().max()) * 100., .001)
    lum = joined.loc[joined.marka_kod.eq(cfg.DECLINING_BRAND) & joined.typ_mpk.eq("Sklep")
                     & joined.scenariusz_kod.eq("ACT") & joined.konto_id.eq("4010")
                     & joined.miesiac.dt.month.between(4, 11)].groupby(joined.miesiac.dt.year).kwota_pln.sum()
    results.range("Historia 5: sklepy Kroko kwiecień do listopada r/r", (lum[2026] / lum[2025] - 1.) * 100., -18., -9., "%")
    for year, end, low, high in [(2025, "2026-04-01", -4., 0.), (2026, "2026-12-01", -10., -4.)]:
        start = pd.Timestamp(f"{year}-04-01")
        cohort = mpk.loc[mpk.typ_mpk.eq("Sklep") & mpk.marka_kod.eq(cfg.DECLINING_BRAND) & (mpk.lfl_od <= start)
                         & (mpk.data_zamkniecia.isna() | (mpk.data_zamkniecia >= end)), "mpk_id"]
        months = range(4, 12) if year == 2026 else range(1, 13)
        sales = joined.loc[joined.mpk_id.isin(cohort) & joined.scenariusz_kod.eq("ACT")
                           & joined.konto_id.eq("4010") & joined.miesiac.dt.month.isin(months)]
        totals = sales.groupby(fiscal_year(sales.miesiac)).kwota_pln.sum()
        results.range(f"Historia 5: Kroko LFL RF {year}", (totals[year] / totals[year - 1] - 1.) * 100., low, high, "%")
    group_days = daily.groupby("data").sprzedaz_netto_pln.sum()
    november = group_days.loc["2025-11-01":"2025-11-30"]
    ec_days = daily.loc[daily.mpk_id.str.startswith("EC-") & daily.data.between("2025-04-01", "2026-03-31")] \
        .groupby("data").sprzedaz_netto_pln.sum()
    results.check("Historia 6: Black Friday maksimum grupy w listopadzie",
                  november.idxmax() == pd.Timestamp("2025-11-28"), november.idxmax().date(), "2025-11-28")
    results.check("Historia 6: Black Friday maksimum e-commerce w RF",
                  ec_days.idxmax() == pd.Timestamp("2025-11-28"), ec_days.idxmax().date(), "2025-11-28")
    actual_agg = tables["agg_sprzedaz_mies"].loc[tables["agg_sprzedaz_mies"].scenariusz_kod.eq("ACT")]
    shares = actual_agg.groupby([fiscal_year(actual_agg.miesiac), "kanal"]).sprzedaz_netto_pln.sum().unstack()
    shares["share"] = shares["E-commerce"] / shares[["E-commerce", "Sklep"]].sum(axis=1)
    results.range("Historia 7: udział e-commerce RF 2023/24", shares.loc[2023, "share"] * 100., 16., 20., "%")
    results.range("Historia 7: udział e-commerce RF 2026/27 YTD", shares.loc[2026, "share"] * 100., 21., 26., "%")
    results.check("Historia 7: udział e-commerce rośnie co RF", shares["share"].diff().dropna().gt(0).all(),
                  ", ".join(f"{value:.2%}" for value in shares["share"]), "ściśle rosnący")
    monthly = actual_agg.groupby("miesiac").sprzedaz_netto_pln.sum()
    for year in (2023, 2024, 2025):
        fy_months = monthly.loc[fiscal_year(monthly.index) == year]
        results.check(f"Historia 8: szczyt grudniowy RF {year}", len(fy_months) == 12 and fy_months.idxmax().month == 12,
                      fy_months.idxmax().date(), f"{year}-12-01, pełne 12 miesięcy")
    year_pnl = pnl.loc[pnl.scenariusz_kod.eq("ACT") & (fiscal_year(pnl.miesiac) == 2025)]
    accounts = year_pnl.groupby("konto_id").kwota_pln.sum()
    ebitda = accounts["4010"] - accounts.drop(["4010", "6010"]).sum()
    results.range("Sprzedaż grupy RF 2025/26", accounts["4010"] / 1e9, .7, 1.1, " mld PLN")
    results.range("Marża EBITDA grupy RF 2025/26", ebitda / accounts["4010"] * 100., 12., 22., "%")


def reference_profiles(tables):
    _, economics = build_dimensions(np.random.default_rng(cfg.SEED))
    actual_days = sales_profile(tables["dim_data"], tables["dim_mpk"], economics)
    actual = monthly_profile(actual_days, tables["dim_mpk"])
    planned = monthly_profile(sales_profile(tables["dim_data"], tables["dim_mpk"], economics, True),
                              tables["dim_mpk"], True)
    return actual, planned, actual_days


def check_budget_weather_forecast(tables, results):
    actual_profile, planned_profile, actual_days = reference_profiles(tables)
    mpk, pnl = tables["dim_mpk"], tables["fakt_pnl"]
    expected_days = pd.MultiIndex.from_frame(actual_days.loc[actual_days.data <= cfg.DAILY_END, ["data", "mpk_id"]])
    observed_days = pd.MultiIndex.from_frame(tables["fakt_sprzedaz_dzienna"][["data", "mpk_id"]])
    results.zero("Pełna siatka otwartych dni wszystkich MPK",
                 len(expected_days.symmetric_difference(observed_days)))
    meta = mpk.loc[~mpk.typ_mpk.eq("Centrala") & ~mpk.status.eq("Planowany")].set_index("mpk_id")
    actual = pnl.loc[pnl.scenariusz_kod.eq("ACT") & pnl.konto_id.eq("4010")]
    errors, cogs_errors, rent_errors, warm_prediction = [], [], [], None
    for year in (2024, 2025, 2026):
        prev_sales = actual.loc[fiscal_year(actual.miesiac) == year - 1].groupby("mpk_id").kwota_pln.sum()
        prev_weights = actual_profile.loc[fiscal_year(actual_profile.miesiac) == year - 1].groupby("mpk_id").weight.sum()
        previous_unit = meta.copy()
        area = previous_unit.powierzchnia_m2.astype(float).fillna(1.)
        previous_unit["rate"] = (prev_sales / prev_weights).reindex(meta.index) / area
        peers = previous_unit.groupby(["marka_kod", "kraj_kod", "typ_mpk"]).rate.transform("mean")
        annual_base = previous_unit.rate.fillna(peers) * area
        profile = planned_profile.loc[fiscal_year(planned_profile.miesiac) == year].copy()
        growth = meta.marka_kod.map(cfg.BUD_STORE_GROWTH)
        growth = growth.where(~meta.typ_mpk.eq("E-commerce"), cfg.BUD_ECOM_GROWTH)
        profile["expected"] = profile.mpk_id.map(annual_base * (1. + growth)) * profile.weight
        booked = pnl.loc[pnl.scenariusz_kod.eq("BUD") & pnl.konto_id.eq("4010")
                         & (fiscal_year(pnl.miesiac) == year)].set_index(["miesiac", "mpk_id"]).kwota_pln
        errors.append(maximum_error(profile.set_index(["miesiac", "mpk_id"]).expected, booked))
        profile["expected_cogs"] = profile.mpk_id.map(annual_base * (1. + growth)) * profile.cogs_weight
        booked_cogs = pnl.loc[pnl.scenariusz_kod.eq("BUD") & pnl.konto_id.eq("4510")
                              & (fiscal_year(pnl.miesiac) == year)].set_index(["miesiac", "mpk_id"]).kwota_pln
        cogs_errors.append(maximum_error(profile.set_index(["miesiac", "mpk_id"]).expected_cogs, booked_cogs))
        previous_rent = pnl.loc[pnl.scenariusz_kod.eq("ACT") & pnl.konto_id.eq("5120")
                                & (fiscal_year(pnl.miesiac) == year - 1)].groupby("mpk_id").kwota_pln.sum()
        previous_fraction = actual_profile.loc[fiscal_year(actual_profile.miesiac) == year - 1].groupby("mpk_id").fraction.sum()
        rent_rate = previous_rent / previous_fraction
        old_stores = profile.loc[profile.mpk_id.isin(rent_rate.dropna().index)].copy()
        old_stores["expected_rent"] = old_stores.mpk_id.map(rent_rate) * 1.03 * old_stores.fraction
        rent_booked = pnl.loc[pnl.scenariusz_kod.eq("BUD") & pnl.konto_id.eq("5120")
                              & (fiscal_year(pnl.miesiac) == year)
                              & pnl.mpk_id.isin(rent_rate.dropna().index)].set_index(["miesiac", "mpk_id"]).kwota_pln
        rent_errors.append(maximum_error(old_stores.set_index(["miesiac", "mpk_id"]).expected_rent, rent_booked))
        if year == 2026:
            normal_growth = pd.Series(cfg.STORE_LFL_GROWTH, index=meta.index)
            normal_growth.loc[meta.marka_kod.eq(cfg.DECLINING_BRAND)] = cfg.DECLINING_STORE_GROWTH[2026]
            normal_growth.loc[meta.typ_mpk.eq("E-commerce")] = cfg.ECOM_GROWTH
            normal_growth.loc[meta.typ_mpk.eq("E-commerce") & meta.marka_kod.eq(cfg.FAST_ECOM_BRAND)] = cfg.FAST_ECOM_GROWTH
            warm_prediction = actual_profile.loc[actual_profile.miesiac.eq(cfg.WEATHER_MONTH)].copy()
            warm_prediction["expected"] = warm_prediction.mpk_id.map(annual_base * (1. + normal_growth)) * warm_prediction.weight
    results.zero("BUD: baza ACT poprzedniego RF i gładki profil", max(errors), .011)
    results.zero("BUD: koszt własny i normalna pogoda", max(cogs_errors), .011)
    results.zero("BUD: czynsze z poprzedniego ACT plus 3%", max(rent_errors), .011)
    warm_prediction["marka_kod"] = warm_prediction.mpk_id.map(meta.marka_kod)
    normal = warm_prediction.groupby("marka_kod").expected.sum()
    september = actual.loc[actual.miesiac.eq(cfg.WEATHER_MONTH)].copy()
    september["marka_kod"] = september.mpk_id.map(meta.marka_kod)
    actual_warm = september.groupby("marka_kod").kwota_pln.sum()
    for brand, factor in cfg.WARM_MONTH_FACTOR.items():
        low, high = (factor - 1.) * 100. - 1.5, (factor - 1.) * 100. + 1.5
        results.range(f"Historia 4: pogoda, sprzedaż {brand} względem trendu",
                      (actual_warm[brand] / normal[brand] - 1.) * 100., low, high, "%")
    future = pnl.loc[pnl.miesiac.between(cfg.FORECAST_START, cfg.FORECAST_END) &
                     pnl.scenariusz_kod.isin(["BUD", "FC"])].pivot(
                         index=["miesiac", "mpk_id", "konto_id"], columns="scenariusz_kod", values="kwota_pln"
                     ).reset_index().merge(mpk, on="mpk_id")
    multiplier = np.where(future.marka_kod.eq(cfg.DECLINING_BRAND), cfg.FC_DECLINING_FACTOR, 1.)
    ratio = actual_profile.set_index(["miesiac", "mpk_id"]).weight / planned_profile.set_index(["miesiac", "mpk_id"]).weight
    key = pd.MultiIndex.from_frame(future[["miesiac", "mpk_id"]])
    multiplier *= np.where(future.mpk_id.isin(cfg.DELAYED_OPENINGS), ratio.reindex(key).fillna(1.), 1.)
    sales_rows = future.konto_id.isin(["4010", "4510"])
    results.zero("FC: Kroko i rzeczywisty rozruch VEN DE",
                 float((future.loc[sales_rows, "FC"] - future.loc[sales_rows, "BUD"] * multiplier[sales_rows]).abs().max()), .011)
    cz = future.konto_id.eq("5120") & future.marka_kod.eq(cfg.RENT_SHOCK_BRAND) & future.kraj_kod.eq(cfg.RENT_SHOCK_COUNTRY)
    cz_target = future.loc[cz, "BUD"] * (1. + cfg.RENT_SHOCK_INCREASE) / (1. + cfg.BUD_RENT_GROWTH)
    results.zero("FC: nowa stawka czynszów AUR AT", float((future.loc[cz, "FC"] - cz_target).abs().max()), .011)
    ec = future.konto_id.eq("5220") & future.kraj_kod.eq(cfg.ORDER_SHOCK_COUNTRY)
    ec_target = future.loc[ec, "BUD"] * multiplier[ec] * (1. + cfg.ORDER_SHOCK_INCREASE)
    results.zero("FC: nowa stawka przewoźnika DE", float((future.loc[ec, "FC"] - ec_target).abs().max()), .011)
    # Pozostałe koszty FC są zmieniane tylko przez jawne zależności od sprzedaży.
    unchanged = ~future.konto_id.isin(["4010", "4510"]) & ~cz
    affected_variable = future.marka_kod.eq(cfg.DECLINING_BRAND) | future.mpk_id.isin(cfg.DELAYED_OPENINGS)
    changed_cost = (affected_variable & future.typ_mpk.eq("Sklep") & future.konto_id.isin(["5110", "5910"])) \
        | (affected_variable & future.typ_mpk.eq("E-commerce") & future.konto_id.isin(["5210", "5220", "5230"])) | ec
    unchanged &= ~changed_cost
    results.zero("FC: pozostałe niezmienione koszty BUD",
                 float((future.loc[unchanged, "FC"] - future.loc[unchanged, "BUD"]).abs().max()), 0.)
    revenue = future.loc[future.konto_id.eq("4010")].set_index(["miesiac", "mpk_id"])
    delta = (revenue.FC - revenue.BUD).reindex(key).fillna(0.).to_numpy()
    target_cost = future.BUD.copy()
    for account, share in [("5110", cfg.STORE_PAYROLL_VARIABLE_SHARE), ("5910", cfg.STORE_OTHER_SHARE)]:
        mask = future.typ_mpk.eq("Sklep") & future.konto_id.eq(account)
        target_cost.loc[mask] += share * delta[mask]
    ec_mask = future.typ_mpk.eq("E-commerce") & future.konto_id.isin(["5210", "5220", "5230"])
    target_cost.loc[ec_mask] *= multiplier[ec_mask]
    target_cost.loc[ec] *= 1. + cfg.ORDER_SHOCK_INCREASE
    results.zero("FC: koszty powiązane ze zmienioną sprzedażą",
                 float((future.loc[changed_cost, "FC"] - target_cost.loc[changed_cost]).abs().max()), .011)


def check_plan_excel_answers(tables, results):
    plan = tables["ref_plan_2027_28_rozklad"]
    keys = ["marka_kod", "kraj_kod", "kanal"]
    grouped = plan.groupby(keys)
    results.check("Plan: 12 miesięcy na kombinację", grouped.size().eq(12).all()
                  and set(plan.miesiac) == set(pd.date_range(cfg.PLAN_START, cfg.PLAN_END, freq="MS")),
                  len(plan), f"{grouped.ngroups} kombinacji × 12 miesięcy")
    share_error = max((grouped.udzial_ly.sum() - 1.).abs().max(), (grouped.udzial_sr2.sum() - 1.).abs().max())
    results.zero("Plan: udziały sumują się do 1", share_error, 1e-12)
    product_error = max((plan.plan_ly_pln - (plan.cel_roczny_pln * plan.udzial_ly).round(2)).abs().max(),
                        (plan.plan_sr2_pln - (plan.cel_roczny_pln * plan.udzial_sr2).round(2)).abs().max())
    results.zero("Plan: cel razy udział", product_error, .000001)
    total_error = max((grouped.plan_ly_pln.sum() - grouped.cel_roczny_pln.first()).abs().max(),
                      (grouped.plan_sr2_pln.sum() - grouped.cel_roczny_pln.first()).abs().max())
    results.zero("Plan: miesięczne plany do rocznego celu", total_error, .10)
    agg = tables["agg_sprzedaz_mies"]
    calc_shares = []
    for year in (2024, 2025):
        history = agg.loc[agg.scenariusz_kod.eq("ACT") & (fiscal_year(agg.miesiac) == year)].copy()
        history["month"] = history.miesiac.dt.month
        history["share"] = history.sprzedaz_netto_pln / history.groupby(keys).sprzedaz_netto_pln.transform("sum")
        calc_shares.append(history.set_index(keys + ["month"]).share)
    target = plan.assign(month=plan.miesiac.dt.month).set_index(keys + ["month"])
    error = max(maximum_error(target.udzial_ly, calc_shares[1]),
                maximum_error(target.udzial_sr2, (calc_shares[0] + calc_shares[1]) / 2.))
    results.zero("Plan: źródło LY i średnia udziałów dwóch lat", error, 1e-12)
    path = cfg.DATA_DIR / "excel"
    goals_wb = load_workbook(path / "cele_sprzedazy_2027_28.xlsx", data_only=False)
    assumptions_wb = load_workbook(path / "zalozenia_plan_2027_28.xlsx", data_only=False)
    hq_wb = load_workbook(path / "budzet_opex_centrala_2027_28_szablon.xlsx", data_only=False)
    all_wb = [goals_wb, assumptions_wb, hq_wb]
    expected_sheets = [{"Cele", "Opis"}, {"Zalozenia", "Nowe_sklepy", "Opis"}, {"Budzet", "Instrukcja"}]
    sheets_ok = all(set(wb.sheetnames) == expected for wb, expected in zip(all_wb, expected_sheets))
    format_ok = all(ws.freeze_panes == "A2" and all(cell.font.bold for cell in ws[1])
                    and all(ws.column_dimensions[cell.column_letter].width >= 16 for cell in ws[1])
                    for wb in all_wb for ws in wb)
    results.check("Excel: arkusze i czytelne formatowanie", sheets_ok and format_ok, "3 pliki",
                  "nazwy arkuszy, nagłówki bold, szerokości, zamrożony wiersz")
    goals = pd.DataFrame(goals_wb["Cele"].values)
    goals.columns = goals.iloc[0]
    goals = goals.iloc[1:].rename(columns={"marka": "marka_kod", "kraj": "kraj_kod"}).copy()
    goals = goals.set_index(keys)
    goals["sprzedaz_fc_2026_27_pln"] = goals["sprzedaz_fc_2026_27_pln"].astype(float)
    goals["cel_2027_28_pln"] = goals["cel_2027_28_pln"].astype(float)
    goals["wzrost_docelowy_pct"] = goals["wzrost_docelowy_pct"].astype(float)
    fc = agg.loc[agg.scenariusz_kod.eq("FC")].groupby(keys).sprzedaz_netto_pln.sum()
    expected_growth = pd.Series(
        [cfg.TARGET_GROWTH_2027[brand] + (cfg.TARGET_ECOM_EXTRA_PP if channel == "E-commerce" else 0.)
         for brand, _, channel in goals.index], index=goals.index)
    goals_error = max(maximum_error(goals["sprzedaz_fc_2026_27_pln"], fc),
                      maximum_error(goals["wzrost_docelowy_pct"], expected_growth),
                      maximum_error(goals["cel_2027_28_pln"],
                                    (fc * (1. + expected_growth)).round(-3)),
                      maximum_error(goals["cel_2027_28_pln"], grouped.cel_roczny_pln.first()))
    results.zero("Excel Cele: FC, wzrost, cel, zgodność z ref_plan", goals_error, .011)
    results.check("Excel Cele bez GRP", "GRP" not in goals.index.get_level_values("marka_kod")
                  and len(goals) == grouped.ngroups, len(goals), f"{grouped.ngroups} kombinacji, cztery marki")
    assumptions = assumptions_wb["Zalozenia"]
    new = assumptions_wb["Nowe_sklepy"]
    new_ids = {row[0] for row in new.iter_rows(min_row=2, values_only=True)}
    planned_ids = set(tables["dim_mpk"].loc[tables["dim_mpk"].status.eq("Planowany"), "mpk_id"])
    expected_assumptions = len(cfg.BRANDS) * len(cfg.COUNTRIES)
    results.check("Excel Założenia i Nowe_sklepy", assumptions.max_row == expected_assumptions + 1 and new_ids == planned_ids,
                  f"{assumptions.max_row - 1}, {new.max_row - 1}",
                  f"{expected_assumptions} założeń i {len(planned_ids)} planowanych sklepów")
    ws = hq_wb["Budzet"]
    rows = list(ws.iter_rows(min_row=2, values_only=True))
    template_pairs = {(row[0], str(row[2])) for row in rows}
    hq_pnl = tables["fakt_pnl"].loc[tables["fakt_pnl"].mpk_id.str.startswith("HQ-")].copy()
    hq_pnl["fy"] = fiscal_year(hq_pnl.miesiac)
    expected_pairs = set(hq_pnl[["mpk_id", "konto_id"]].itertuples(index=False, name=None))
    blank_ok = all(all(value is None for value in row[6:18]) for row in rows)
    formulas_ok = all(row[18] == f"=SUM(G{index}:R{index})" for index, row in enumerate(rows, start=2))
    results.check("Excel Budzet: używane konta, puste miesiące, SUM",
                  template_pairs == expected_pairs and blank_ok and formulas_ok, len(rows), f"{len(expected_pairs)} wierszy i tyle samo formuł SUM")
    hq_values = pd.DataFrame([[row[0], str(row[2]), row[4], row[5]] for row in rows],
                             columns=["mpk_id", "konto_id", "ACT", "FC"]).set_index(["mpk_id", "konto_id"])
    errors = []
    for scenario, year in [("ACT", 2025), ("FC", 2026)]:
        expected = hq_pnl.loc[hq_pnl.scenariusz_kod.eq(scenario) & hq_pnl.fy.eq(year)] \
            .groupby(["mpk_id", "konto_id"]).kwota_pln.sum()
        errors.append(maximum_error(hq_values[scenario], expected))
    results.zero("Excel Budzet: sumy ACT i FC z P&L", max(errors), .011)
    for wb in all_wb:
        wb.close()
    markdown, csv, _, metrics = make_answers(tables)
    saved_md = (cfg.DATA_DIR / "oczekiwane_odpowiedzi.md").read_text(encoding="utf-8")
    saved_csv = pd.read_csv(cfg.DATA_DIR / "oczekiwane_odpowiedzi.csv", dtype="string").fillna("")
    rebuilt_csv = csv.astype("string").fillna("")
    spec = (cfg.ROOT / "generator" / "SPEC.md").read_text(encoding="utf-8")
    questions_section = spec.split("## Pytania testowe agenta (klucz odpowiedzi)", 1)[1].split("## Walidacja", 1)[0]
    spec_questions = re.findall(r"^\d+\.\s+(.*)$", questions_section, flags=re.MULTILINE)
    results.check("Klucz 14 pytań policzony z tabel", saved_md == markdown and saved_csv.equals(rebuilt_csv)
                  and saved_csv.pytanie.tolist() == QUESTIONS == spec_questions,
                  len(saved_csv), "14 pytań dosłownie z SPEC i zgodny wynik")
    results.check("Pytanie 13: brak danych 2029", not any(
        frame[column].dt.year.eq(2029).any() for name, frame in tables.items()
        for column, kind, _ in SCHEMAS[name] if kind == "date32"),
        "brak faktów, celu i kalendarza 2029", "odmowa zgadywania")
    closed_december = tables["fakt_pnl"].loc[tables["fakt_pnl"].scenariusz_kod.eq("ACT")
                                            & (tables["fakt_pnl"].miesiac >= cfg.FORECAST_START)]
    results.check("Pytanie 14: dwa składniki niepełnego 3Q",
                  len(closed_december) == 0 and metrics["q14"]["closed"] > 0 and metrics["q14"]["december"] > 0,
                  "zamknięty październik i listopad, grudzień do 08.12", "bez pełnego grudnia ACT")


def check_import_workbook(tables, results):
    directory = cfg.DATA_DIR / "excel"
    imported = load_workbook(directory / "budzet_opex_centrala_2027_28_import.xlsx", data_only=False)
    template = load_workbook(directory / "budzet_opex_centrala_2027_28_szablon.xlsx", data_only=False)
    try:
        ws = imported["Import"]
        month_columns = [f"m{index:02d}_{month:%Y_%m}" for index, month in enumerate(
            pd.date_range(cfg.PLAN_START, cfg.PLAN_END, freq="MS"), start=1)]
        expected_headers = ["mpk_id", "mpk_nazwa", "konto_id", "konto_nazwa",
                            "act_2025_26_pln", "fc_2026_27_pln"] + month_columns + ["komentarz"]
        headers = [cell.value for cell in ws[1]]
        headers_ok = headers == expected_headers and all(
            isinstance(value, str) and re.fullmatch(r"[a-z][a-z0-9_]*", value) for value in headers
        )
        results.check("PowerTable: nagłówki ASCII i kolejność", headers_ok, len(headers),
                      "19 zgodnych nazw, litera na początku")
        layout_ok = imported.sheetnames == ["Import", "Opis"] and ws["A1"].value == "mpk_id" \
            and len(ws.merged_cells.ranges) == 0
        results.check("PowerTable: płaski układ od A1", layout_ok, ", ".join(imported.sheetnames),
                      "Import pierwszy, Opis drugi, brak scaleń")
        formulas = sum(cell.data_type == "f" for worksheet in imported
                       for row in worksheet.iter_rows() for cell in row)
        results.zero("PowerTable: brak formuł", formulas)
        rows = list(ws.iter_rows(min_row=2, values_only=True))
        source_rows = list(template["Budzet"].iter_rows(min_row=2, values_only=True))
        blank_rows = sum(all(value is None or value == "" for value in row) for row in rows)
        results.zero("PowerTable: brak pustych wierszy", blank_rows)
        numeric_ok = all(isinstance(value, (int, float)) and not isinstance(value, bool) and np.isfinite(value)
                         for row in rows for value in row[4:18])
        results.check("PowerTable: kompletne kolumny liczbowe", numeric_ok,
                      f"{len(rows)} × 14", "ACT, FC i 12 miesięcy, liczby bez nulli")
        keys = [(row[0], str(row[2])) for row in rows]
        source_keys = [(row[0], str(row[2])) for row in source_rows]
        results.check("PowerTable: wiersze i klucze jak w szablonie",
                      len(rows) == len(source_rows) and keys == source_keys and len(keys) == len(set(keys)),
                      len(rows), f"{len(source_rows)} unikalnych par MPK i konto")
        results.check("PowerTable: opisy, ACT i FC jak w szablonie",
                      [row[:6] for row in rows] == [row[:6] for row in source_rows],
                      "6 kolumn źródłowych", "identyczne zapisane wartości")
        formatting_ok = all(cell.font.bold for cell in ws[1]) and all(
            "#,##0" in cell.number_format for row in ws.iter_rows(min_row=2, min_col=5, max_col=18) for cell in row
        )
        results.check("PowerTable: formatowanie", formatting_ok, "pogrubienie i separator tysięcy",
                      "pogrubiony nagłówek, liczby z separatorem")
        description = imported["Opis"]
        description_ok = description.max_row == 4 and [description.cell(row, 1).value for row in range(2, 5)] \
            == ["Dane", "Kolumny", "Projekt"]
        results.check("PowerTable: krótki arkusz Opis", description_ok, description.max_row,
                      "nagłówek i 3 wiersze opisu")
        if not numeric_ok or not headers_ok or not rows:
            return
        months = np.array([row[6:18] for row in rows], dtype=float)
        it = np.array([str(row[2]) == "5420" for row in rows])
        renewal = np.array([row[0] == cfg.IMPORT_IT_RENEWAL_MPK and str(row[2]) == "5420" for row in rows])
        base = np.array([round(float(row[5]) / 12. * (1. + (cfg.IMPORT_WAGE_INDEX if str(row[2]) == "5410"
                                                           else cfg.IMPORT_OTHER_INDEX)), -2)
                         for row in rows])
        column = month_columns.index(cfg.IMPORT_IT_RENEWAL_MONTH)
        extra_pln = cfg.IMPORT_IT_RENEWAL_PLN
        expected = np.repeat(base[:, None], 12, axis=1)
        expected[renewal, column] += extra_pln
        results.zero("PowerTable: indeksacja, miesiące i zaokrąglenie do 100",
                     float(np.max(np.abs(months - expected))), .001)
        extra = months[renewal].sum(axis=1) - 12. * base[renewal]
        renewal_ok = renewal.sum() == 1 \
            and np.isclose(months[renewal, column], base[renewal] + extra_pln, rtol=0, atol=.001).all() \
            and np.isclose(extra, extra_pln, rtol=0, atol=.001).all()
        results.check(f"PowerTable: jednorazowa dopłata wyłącznie {cfg.IMPORT_IT_RENEWAL_MPK} × 5420",
                      renewal_ok, f"{extra.sum():,.0f} PLN".replace(",", " "),
                      f"październik = baza + {extra_pln:,.0f} PLN, suma roczna = 12 × baza + dopłata".replace(",", " "))
        other_it = it & ~renewal
        results.zero("PowerTable: pozostałe MPK konta 5420 bez skoku w październiku",
                     float(np.max(np.abs(months[other_it, column] - base[other_it]))) if other_it.any() else float("inf"),
                     .001)
        commented_keys = [(row[0], str(row[2])) for row in rows
                          if row[18] is not None and str(row[18]).strip()]
        renewal_key = (cfg.IMPORT_IT_RENEWAL_MPK, "5420")
        comments_ok = commented_keys == [renewal_key] and all(
            row[18] is None or row[18] == "" for row in rows
            if (row[0], str(row[2])) != renewal_key
        ) and all(isinstance(row[18], str) and row[18].strip() for row in rows
                  if (row[0], str(row[2])) == renewal_key)
        results.check(f"PowerTable: jedyny komentarz przy {cfg.IMPORT_IT_RENEWAL_MPK} × 5420", comments_ok,
                      len(commented_keys), "jeden komentarz, pozostałe puste")
        results.check("PowerTable: suma projektu za 12 miesięcy",
                      np.isclose(months.sum(), expected.sum(), rtol=0, atol=.001),
                      f"{months.sum():,.0f} PLN".replace(",", " "),
                      f"{expected.sum():,.0f} PLN".replace(",", " "))
    finally:
        imported.close()
        template.close()


def check_plan_calendar(tables, results):
    plan = tables["plan_kalendarz"]
    months = pd.date_range(cfg.DAILY_START, cfg.PLAN_END, freq="MS")
    results.check("Plan kalendarz: 60 kolejnych miesięcy",
                  len(plan) == 60 and plan.miesiac.tolist() == months.tolist(),
                  len(plan), f"60 miesięcy, {cfg.DAILY_START} do {cfg.PLAN_END}")
    results.zero("Plan kalendarz: unikalny klucz", plan.duplicated("miesiac").sum())
    text_columns = [column for column, kind, _ in SCHEMAS["plan_kalendarz"] if kind == "string"]
    non_ascii = sum(not isinstance(value, str) or not value.isascii()
                    for column in text_columns for value in plan[column])
    results.zero("Plan kalendarz: wszystkie teksty ASCII", non_ascii)
    results.zero("Plan kalendarz: pokrycie miesięcy agregatu",
                 (~tables["agg_sprzedaz_mies"].miesiac.isin(plan.miesiac)).sum())
    calendar = tables["dim_data"]
    first_days = calendar.loc[calendar.data.dt.day.eq(1)].copy()
    expected = pd.DataFrame({
        "miesiac": first_days.data,
        "rok_finansowy": first_days.rok_finansowy,
        "rok_finansowy_nr": first_days.rok_finansowy_nr,
        "kwartal": first_days.kwartal_finansowy,
        "kwartal_pelny": first_days.kwartal_finansowy_pelny,
        "kwartal_sort": first_days.kwartal_finansowy_sort,
        "miesiac_fin_nr": first_days.miesiac_finansowy_nr,
        "miesiac_nazwa": first_days.miesiac.map({
            1: "Sty", 2: "Lut", 3: "Mar", 4: "Kwi", 5: "Maj", 6: "Cze",
            7: "Lip", 8: "Sie", 9: "Wrz", 10: "Paz", 11: "Lis", 12: "Gru",
        }),
        "okres": first_days.data.dt.strftime("%Y-%m"),
        "rok": first_days.rok,
        "miesiac_nr": first_days.miesiac,
        "czy_miesiac_zamkniety": first_days.czy_miesiac_zamkniety,
    })
    results.check("Plan kalendarz: zgodność z dim_data",
                  plan.equals(normalize("plan_kalendarz", expected)),
                  "12 kolumn", "atrybuty pierwszych dni miesięcy i skróty ASCII")


def check_files(tables, results):
    expected_csv = {f"{name}.csv" for name in SCHEMAS if name != "fakt_sprzedaz_dzienna"} \
        | {"fakt_sprzedaz_dzienna.csv.gz"}
    actual_csv = {path.name for path in (cfg.DATA_DIR / "csv").iterdir() if path.is_file()}
    results.check("Pliki CSV, tylko fakt dzienny gzip", expected_csv == actual_csv, len(actual_csv), f"{len(SCHEMAS)} plików")
    bom_ok, content_ok = True, True
    for name, expected in tables.items():
        daily = name == "fakt_sprzedaz_dzienna"
        file = cfg.DATA_DIR / "csv" / (f"{name}.csv.gz" if daily else f"{name}.csv")
        opener = gzip.open if daily else open
        with opener(file, "rb") as stream:
            bom_ok &= stream.read(3) == b"\xef\xbb\xbf"
        types = {column: "string" for column, kind, _ in SCHEMAS[name] if kind == "string"}
        types.update({column: "Int64" for column, kind, _ in SCHEMAS[name] if kind == "int64"})
        actual = pd.read_csv(file, dtype=types, encoding="utf-8-sig", float_precision="round_trip")
        for column, kind, _ in SCHEMAS[name]:
            if kind == "string" and not expected[column].isna().any():
                actual[column] = actual[column].fillna("")
        actual = normalize(name, actual)
        try:
            pd.testing.assert_frame_equal(expected, actual, check_exact=False, rtol=1e-13, atol=1e-7)
        except AssertionError:
            content_ok = False
    results.check("CSV BOM UTF-8, separator i wartości", bom_ok and content_ok, f"{len(SCHEMAS)} tabel porównanych", "zgodność z Parquet")
    dictionary = (cfg.DATA_DIR / "SLOWNIK_DANYCH.md").read_text(encoding="utf-8")
    docs_ok = True
    for name in SCHEMAS:
        marker = f"### {name}\n"
        if marker not in dictionary:
            docs_ok = False
            continue
        section = dictionary.split(marker, 1)[1].split("\n### ", 1)[0]
        count = f"{len(tables[name]):,}".replace(",", " ")
        docs_ok &= f"Liczba wierszy: {count}." in section and "Relacje i klucze:" in section
        docs_ok &= f"Ziarno: {' × '.join(GRAINS[name])}." in section
    docs_ok &= all(column in dictionary for columns in SCHEMAS.values() for column, _, _ in columns)
    results.check("Słownik obejmuje wszystkie tabele i kolumny", docs_ok, len(SCHEMAS),
                  f"{len(SCHEMAS)} opisów, ziarna, liczności i kolumny")
    paths = list((cfg.ROOT / "generator").glob("*.py")) + list((cfg.ROOT / "generator").glob("*.md")) \
        + list(cfg.DATA_DIR.glob("*.md"))
    forbidden = sum(path.read_text(encoding="utf-8").count(char) for path in paths for char in ("\u2013", "\u2014"))
    results.zero("Styl: brak półpauzy i pauzy", forbidden)
    bold_labels = sum(len(re.findall(r"\*\*[^*\n]+:\*\*|\*\*[^*\n]+\*\*:", path.read_text(encoding="utf-8")))
                      for path in paths)
    results.zero("Styl: brak pogrubionych etykiet z dwukropkiem", bold_labels)
    size = sum(path.stat().st_size for path in cfg.DATA_DIR.rglob("*") if path.is_file())
    results.check("Rozmiar dane", size < 60_000_000, f"{size / 1_000_000:.3f} MB", "<60 MB")


def check_determinism(results):
    runs = []
    for _ in range(2):
        start = time.perf_counter()
        completed = subprocess.run([sys.executable, str(Path(__file__).with_name("generate_data.py"))],
                                   cwd=cfg.ROOT.parent, capture_output=True, text=True, encoding="utf-8", check=False)
        seconds = time.perf_counter() - start
        if completed.returncode:
            results.check("Dwa poprawne uruchomienia generatora", False,
                          completed.stderr[-1500:], "kod 0 z innego katalogu")
            return
        hashes = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                  for path in sorted((cfg.DATA_DIR / "parquet").glob("*.parquet"))}
        runs.append({"seconds": round(seconds, 3), "sha256": hashes})
    identical = runs[0]["sha256"] == runs[1]["sha256"] and len(runs[0]["sha256"]) == len(SCHEMAS)
    results.check("Deterministyczność dwóch uruchomień", identical, len(runs[0]["sha256"]),
                  f"{len(SCHEMAS)} identycznych SHA256 Parquet")
    results.check("Czas dwóch uruchomień", max(run["seconds"] for run in runs) < 180.,
                  ", ".join(f"{run['seconds']:.3f} s" for run in runs), "<180 s każde")
    report = {"seed": cfg.SEED, "identical_parquet": identical,
              "runs": runs, "numpy": np.__version__, "pandas": pd.__version__}
    (cfg.ROOT / "generator" / "weryfikacja_deterministycznosci.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--determinism", action="store_true", help="uruchom generator dwukrotnie i porównaj SHA256 Parquet")
    args = parser.parse_args()
    results = Results()
    try:
        if args.determinism:
            check_determinism(results)
        tables = read_tables(results)
        for check in [check_dimensions, check_keys_values, check_daily_reconciliation, check_scenarios,
                      check_cost_rules, check_stories, check_budget_weather_forecast, check_plan_excel_answers,
                      check_import_workbook, check_plan_calendar, check_files]:
            try:
                check(tables, results)
            except Exception as exc:
                results.check(check.__name__, False, f"{type(exc).__name__}: {exc}", "brak wyjątku")
    except Exception as exc:
        results.check("Odczyt danych", False, f"{type(exc).__name__}: {exc}", "komplet wygenerowanych danych")
    return 0 if results.print() else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
