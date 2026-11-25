"""Awaryjne źródło arkusza planistycznego w pliku Excel (scenariusz P1).

Gdyby Plan nie połączył się z modelem SM_Planowanie, Learn opisuje drugą drogę:
arkusz planistyczny można utworzyć z pliku Excel. Plik zawiera sprzedaż ACT 2025/26
w układzie marka x kraj x kanał x miesiąc, przypisaną do miesięcy roku 2027/28.
To ten sam układ, który w modelu daje miara "Sprzedaz ACT 2025/26" pod kolumnami 2027/28.

Nazwy kolumn i wartości są w ASCII, bo Learn ostrzega, że nieobsługiwane znaki Unicode
w źródle mogą blokować wstawienie kolumny wprowadzania danych.

Uruchomienie: python fabric/plan/excel_awaryjny_planu.py
Wynik:        dane/excel/awaryjny_plan_zrodlo_2027_28.xlsx
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[2]
PARQUET = REPO / "dane" / "parquet"
WYNIK = REPO / "dane" / "excel" / "awaryjny_plan_zrodlo_2027_28.xlsx"

# Sumy kontrolne ACT 2025/26 z fabric/plan/klucz_alokacji_2027_28.md (PLN, zaokrąglone do złotych).
KONTROLA = {
    "Aurea": 247_413_778,
    "Vento": 344_103_948,
    "Lumi": 110_434_702,
    "Kroko": 164_197_984,
}


def main() -> int:
    agg = pd.read_parquet(PARQUET / "agg_sprzedaz_mies.parquet")
    kal = pd.read_parquet(PARQUET / "plan_kalendarz.parquet")
    marki = pd.read_parquet(PARQUET / "dim_marka.parquet")

    agg["miesiac"] = pd.to_datetime(agg["miesiac"])
    kal["miesiac"] = pd.to_datetime(kal["miesiac"])

    act = agg[(agg["scenariusz_kod"] == "ACT")
              & (agg["miesiac"] >= "2025-04-01") & (agg["miesiac"] <= "2026-03-01")].copy()
    act["miesiac_docelowy"] = act["miesiac"] + pd.DateOffset(years=2)

    kal27 = kal[kal["rok_finansowy"] == "2027/28"][
        ["miesiac", "rok_finansowy", "kwartal", "miesiac_nazwa", "miesiac_fin_nr"]]
    df = (act.merge(kal27, left_on="miesiac_docelowy", right_on="miesiac", suffixes=("", "_k"))
             .merge(marki[["marka_kod", "marka_nazwa"]], on="marka_kod"))

    wynik = (df.groupby(["marka_nazwa", "kraj_kod", "kanal", "rok_finansowy", "kwartal",
                         "miesiac_nazwa", "miesiac_fin_nr", "miesiac_docelowy"], as_index=False)
               ["sprzedaz_netto_pln"].sum()
               .rename(columns={"marka_nazwa": "Marka", "kraj_kod": "Kraj", "kanal": "Kanal",
                                "rok_finansowy": "Rok finansowy", "kwartal": "Kwartal",
                                "miesiac_nazwa": "Miesiac", "miesiac_fin_nr": "Miesiac fin nr",
                                "miesiac_docelowy": "Data miesiaca",
                                "sprzedaz_netto_pln": "Sprzedaz ACT 2025/26"})
               .sort_values(["Marka", "Kraj", "Kanal", "Miesiac fin nr"]))
    wynik["Sprzedaz ACT 2025/26"] = wynik["Sprzedaz ACT 2025/26"].round(2)

    bledy = []
    for marka, oczek in KONTROLA.items():
        suma = round(wynik.loc[wynik["Marka"] == marka, "Sprzedaz ACT 2025/26"].sum())
        if abs(suma - oczek) > 1:
            bledy.append(f"{marka}: {suma:,} zamiast {oczek:,}")
    razem = round(wynik["Sprzedaz ACT 2025/26"].sum())
    if abs(razem - sum(KONTROLA.values())) > 2:
        bledy.append(f"Grupa: {razem:,} zamiast {sum(KONTROLA.values()):,}")
    if bledy:
        print("Sumy kontrolne się nie zgadzają:\n  " + "\n  ".join(bledy))
        return 1
    tekst = "".join(str(v) for v in wynik.select_dtypes("object").stack().unique()) + "".join(wynik.columns)
    if not tekst.isascii():
        print("W pliku są znaki spoza ASCII, a miały ich nie być.")
        return 1

    opis = pd.DataFrame({"Opis": [
        "Dane syntetyczne przygotowane na warsztat. Nie opisują żadnej istniejącej firmy.",
        "Awaryjne źródło arkusza planistycznego dla scenariusza P1, gdy Plan nie połączy się z modelem SM_Planowanie.",
        "Kolumna Sprzedaz ACT 2025/26 zawiera sprzedaż netto ACT z roku 2025/26 przypisaną do tych samych miesięcy roku 2027/28.",
        "Układ wierszy: Marka > Kraj > Kanal. Układ kolumn: Rok finansowy > Kwartal > Miesiac (sortowanie po Miesiac fin nr).",
        f"Suma kontrolna grupy: {razem:,} PLN.".replace(",", " "),
    ]})
    with pd.ExcelWriter(WYNIK, engine="openpyxl") as xw:
        wynik.to_excel(xw, sheet_name="Dane", index=False)
        opis.to_excel(xw, sheet_name="Opis", index=False)
    print(f"Zapisano {WYNIK.relative_to(REPO)}: {len(wynik)} wierszy, suma {razem:,} PLN".replace(f"{razem:,}", f"{razem:,}".replace(",", " ")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
