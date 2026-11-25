"""Klucz alokacji celu sprzedaży 2027/28 dla scenariusza Planning (P1).

Prowadzący wstawia w Planie kolumnę "Plan 2027/28" skopiowaną z miary "Sprzedaz ACT 2025/26",
a potem wpisuje cel marki w wierszu sumy marki. Plan rozkłada wpisaną kwotę proporcjonalnie do
wartości, które już są w kolumnie, czyli według struktury sprzedaży 2025/26. Ten skrypt wylicza,
co powinno się pojawić w komórkach, żeby na warsztacie dało się to sprawdzić na żywo.

Wejścia: dane/excel/cele_sprzedazy_2027_28.xlsx (cele marka x kraj x kanał),
dane/parquet/agg_sprzedaz_mies.parquet, plan_kalendarz.parquet, ref_plan_2027_28_rozklad.parquet.
Wyjścia w fabric/plan/: klucz_alokacji_2027_28.json (dla weryfikuj_model.py), .csv i .md.

Uruchomienie: python fabric/plan/klucz_alokacji_2027_28.py
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[2]
PARQ = REPO / "dane" / "parquet"
OUT = Path(__file__).resolve().parent
NAZWY = {"AUR": "Aurea", "VEN": "Vento", "LUM": "Lumi", "KRO": "Kroko"}
KOLEJNOSC = ["AUR", "VEN", "LUM", "KRO"]


def pln(x: float) -> str:
    return f"{x:,.0f}".replace(",", " ")


def mln(x: float) -> str:
    return f"{x / 1e6:,.2f}".replace(",", " ").replace(".", ",")


def proc(x: float) -> str:
    return f"{x * 100:+.1f}%".replace(".", ",")


def main() -> None:
    agg = pd.read_parquet(PARQ / "agg_sprzedaz_mies.parquet")
    kal = pd.read_parquet(PARQ / "plan_kalendarz.parquet")
    ref = pd.read_parquet(PARQ / "ref_plan_2027_28_rozklad.parquet")
    cele = pd.read_excel(REPO / "dane" / "excel" / "cele_sprzedazy_2027_28.xlsx", sheet_name="Cele")

    agg["miesiac"] = pd.to_datetime(agg["miesiac"])
    kal["miesiac"] = pd.to_datetime(kal["miesiac"])
    agg = agg.merge(kal[["miesiac", "rok_finansowy", "kwartal", "miesiac_nazwa", "miesiac_fin_nr"]], on="miesiac")

    def suma(scen: str, rok: str) -> pd.DataFrame:
        return agg[(agg.scenariusz_kod == scen) & (agg.rok_finansowy == rok)]

    act = suma("ACT", "2025/26")
    assert act.miesiac.nunique() == 12, "ACT 2025/26 musi mieć 12 miesięcy"

    cel_marki = cele.groupby("marka")["cel_2027_28_pln"].sum()
    fc_marki_excel = cele.groupby("marka")["sprzedaz_fc_2026_27_pln"].sum()
    fc_marki_model = suma("FC", "2026/27").groupby("marka_kod")["sprzedaz_netto_pln"].sum()
    act_marki = act.groupby("marka_kod")["sprzedaz_netto_pln"].sum()

    roznica_fc = (fc_marki_excel - fc_marki_model.reindex(fc_marki_excel.index)).abs().max()
    assert roznica_fc < 1000, f"FC w Excelu rozjeżdża się z modelem o {roznica_fc:.0f} PLN"

    bm = act.groupby(["marka_kod", "miesiac_fin_nr", "miesiac_nazwa", "kwartal"], as_index=False)["sprzedaz_netto_pln"].sum()
    bm = bm.rename(columns={"sprzedaz_netto_pln": "act_2025_26"})
    bm["udzial"] = bm["act_2025_26"] / bm["marka_kod"].map(act_marki)
    bm["cel_marki"] = bm["marka_kod"].map(cel_marki)
    bm["plan_2027_28"] = bm["cel_marki"] * bm["udzial"]
    bm = bm.sort_values(["marka_kod", "miesiac_fin_nr"])

    # Kontrola krzyżowa z ref_plan: ten sam rozkład, gdy cel wpisuje się w wierszach marka x kraj x kanał.
    ref_bm = ref.groupby(["marka_kod", "kraj_kod", "kanal"])["plan_ly_pln"].sum()
    cele_mkk = cele.set_index(["marka", "kraj", "kanal"])["cel_2027_28_pln"]
    cele_mkk.index.names = ref_bm.index.names
    roznica_ref = (ref_bm - cele_mkk.reindex(ref_bm.index)).abs().max()
    assert roznica_ref < 1, f"ref_plan nie sumuje się do celów z Excela ({roznica_ref:.2f} PLN)"

    # Przykład do dyskusji: alokacja z góry (cel marki) wobec celu z dołu (cel kraju w Excelu) dla Vento DE.
    ven = act[act.marka_kod == "VEN"]
    udzial_de = ven[ven.kraj_kod == "DE"]["sprzedaz_netto_pln"].sum() / ven["sprzedaz_netto_pln"].sum()
    ven_de_gora = cel_marki["VEN"] * udzial_de
    ven_de_dol = cele[(cele.marka == "VEN") & (cele.kraj == "DE")]["cel_2027_28_pln"].sum()

    grupa = {
        "act_2025_26_grupa": round(float(act["sprzedaz_netto_pln"].sum()), 2),
        "fc_2026_27_grupa": round(float(suma("FC", "2026/27")["sprzedaz_netto_pln"].sum()), 2),
        "bud_2026_27_grupa": round(float(suma("BUD", "2026/27")["sprzedaz_netto_pln"].sum()), 2),
        "cel_2027_28_grupa": float(cel_marki.sum()),
    }
    klucz = {
        **grupa,
        "cele_marek": {k: float(cel_marki[k]) for k in KOLEJNOSC},
        "act_2025_26_marek": {k: round(float(act_marki[k]), 2) for k in KOLEJNOSC},
        "marka_miesiac": [
            {"marka": r.marka_kod, "miesiac": r.miesiac_nazwa, "miesiac_fin_nr": int(r.miesiac_fin_nr),
             "act_2025_26": round(float(r.act_2025_26), 2), "plan_2027_28": round(float(r.plan_2027_28), 2)}
            for r in bm.itertuples()
        ],
        "ven_de": {"udzial_act_2025_26": udzial_de, "alokacja_z_gory": ven_de_gora, "cel_z_excela": float(ven_de_dol)},
    }
    (OUT / "klucz_alokacji_2027_28.json").write_text(json.dumps(klucz, ensure_ascii=False, indent=1), encoding="utf-8")
    bm[["marka_kod", "kwartal", "miesiac_fin_nr", "miesiac_nazwa", "act_2025_26", "udzial", "cel_marki", "plan_2027_28"]] \
        .round(2).to_csv(OUT / "klucz_alokacji_2027_28.csv", index=False, encoding="utf-8")

    miesiace = bm.drop_duplicates("miesiac_fin_nr").sort_values("miesiac_fin_nr")["miesiac_nazwa"].tolist()
    md = [
        "# Klucz alokacji celu 2027/28 (scenariusz P1)", "",
        "Plik generuje `fabric/plan/klucz_alokacji_2027_28.py`. Dane są syntetyczne.", "",
        "Prowadzący wstawia w Planie kolumnę liczbową `Plan 2027/28` z opcją kopiowania wartości z miary "
        "`Sprzedaz ACT 2025/26`, a następnie wpisuje cel marki w wierszu sumy marki. Rozkład proporcjonalny do "
        "wartości istniejących w kolumnie opisuje samouczek Planning w Microsoft Learn. Dokładne zachowanie "
        "zaokrągleń w Planie trzeba potwierdzić przed warsztatem, dlatego kwoty poniżej traktujemy jako "
        "punkt odniesienia z dokładnością do pojedynczych złotych.", "",
        "## Cele do wpisania w wierszach marek", "",
        "| Marka | ACT 2025/26 (PLN) | Cel 2027/28 do wpisania (PLN) | Zmiana wobec ACT 2025/26 |",
        "|---|---:|---:|---:|",
    ]
    for k in KOLEJNOSC:
        md.append(f"| {NAZWY[k]} | {pln(act_marki[k])} | {pln(cel_marki[k])} | {proc(cel_marki[k] / act_marki[k] - 1)} |")
    md += [f"| Grupa | {pln(grupa['act_2025_26_grupa'])} | {pln(grupa['cel_2027_28_grupa'])} | "
           f"{proc(grupa['cel_2027_28_grupa'] / grupa['act_2025_26_grupa'] - 1)} |", "",
           "Cele marek to sumy wierszy arkusza `Cele` w pliku `cele_sprzedazy_2027_28.xlsx` (marka x kraj x kanał). "
           "Plik powstał jako prognoza FC 2026/27 powiększona o docelowy wzrost, zaokrąglona do tysięcy PLN.", "",
           "## Oczekiwany rozkład po miesiącach (mln PLN)", "",
           "| Marka | " + " | ".join(miesiace) + " | Razem |",
           "|---|" + "---:|" * (len(miesiace) + 1)]
    for k in KOLEJNOSC:
        w = bm[bm.marka_kod == k].sort_values("miesiac_fin_nr")
        md.append(f"| {NAZWY[k]} | " + " | ".join(mln(v) for v in w["plan_2027_28"]) + f" | {mln(w['plan_2027_28'].sum())} |")
    sumy = bm.groupby("miesiac_fin_nr")["plan_2027_28"].sum().sort_index()
    md.append("| Grupa | " + " | ".join(mln(v) for v in sumy) + f" | {mln(sumy.sum())} |")
    md += ["", "## Punkt do dyskusji: cel z góry czy z dołu", "",
           f"Vento w Niemczech miało w 2025/26 udział {f'{udzial_de * 100:.1f}'.replace('.', ',')}% w sprzedaży marki. "
           "Po wpisaniu celu "
           f"marki Plan przydzieli Niemcom około {mln(ven_de_gora)} mln PLN, a cel z pliku Excel, budowany "
           f"oddolnie po krajach, wynosi {pln(ven_de_dol)} PLN. Różnica pokazuje, że alokacja według "
           "historycznej struktury nie uwzględnia nowych sklepów ani opóźnionych otwarć. Do tego służy wpisanie "
           "celu na poziomie kraju albo zablokowanie wybranych komórek przed rozkładem.", "",
           "Tabela `ref_plan_2027_28_rozklad` w lakehouse zawiera rozkład miesięczny w wariancie, w którym cele "
           "wpisuje się na poziomie marka x kraj x kanał (kolumna `plan_ly_pln`), oraz wariant z udziałami "
           "średnimi z dwóch lat (`plan_sr2_pln`). Suma `plan_ly_pln` dla każdego wiersza celu zgadza się "
           "z plikiem Excel, co skrypt sprawdza przy każdym uruchomieniu.", ""]
    (OUT / "klucz_alokacji_2027_28.md").write_text("\n".join(md), encoding="utf-8")

    print("cele marek:", {k: pln(cel_marki[k]) for k in KOLEJNOSC}, "grupa", pln(grupa["cel_2027_28_grupa"]))
    print("ACT 2025/26 grupa", pln(grupa["act_2025_26_grupa"]), "FC 2026/27", pln(grupa["fc_2026_27_grupa"]),
          "BUD 2026/27", pln(grupa["bud_2026_27_grupa"]))
    print(f"VEN DE: udział {udzial_de:.4f}, z góry {pln(ven_de_gora)}, z Excela {pln(ven_de_dol)}")
    print(f"maks. różnica FC Excel vs model {roznica_fc:.2f} PLN, ref_plan vs Excel {roznica_ref:.4f} PLN")


if __name__ == "__main__":
    main()
