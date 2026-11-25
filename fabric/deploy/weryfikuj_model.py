"""Weryfikacja wdrożonych modeli: zapytania DAX porównane z kluczem odpowiedzi.

SM_Kontroling: pytania testowe agenta z dane/oczekiwane_odpowiedzi.csv. Generator liczy klucz niezależnie
(pandas na plikach parquet), a tu te same liczby wylicza silnik modelu przez gotowe miary. Zgodność oznacza,
że miary, relacje i kalendarz finansowy są poprawne, więc agent ma na czym oprzeć dobre odpowiedzi.

SM_Planowanie: miary bazowe planu (stały rok finansowy) i klucz alokacji celu 2027/28.

Kwoty w kluczu są zaokrąglone do tysięcy PLN, procenty do 0,1 pp, stąd tolerancje.

Uruchomienie po krokach modele i odswiez:
  python fabric/deploy/weryfikuj_model.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fabric_api as fa  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
STAN = Path(__file__).with_name(".stan_wdrozenia.json")
WYNIK = REPO / "dokumentacja" / "wyniki_weryfikacji_dax.md"

KW = 1500
PP = 0.0006
WSP = 0.006

TESTY_KONTROLING = [
    {
        "nr": "1", "opis": "Sprzedaż netto 2Q 2026/27, wykonanie wobec budżetu",
        "dax": """EVALUATE CALCULATETABLE ( ROW ( "ACT", [Sprzedaż netto ACT], "BUD", [Sprzedaż netto BUD (miesiące zamknięte)],
            "ODCH", [Odchylenie sprzedaży ACT vs BUD], "PROC", [Odchylenie sprzedaży ACT vs BUD %] ),
            'Data'[Kwartał finansowy pełny] = "2Q 2026/27" )""",
        "klucz": None,
        "oczek": [("", "ACT", 213603000, KW), ("", "BUD", 220492000, KW), ("", "ODCH", -6889000, KW),
                  ("", "PROC", -0.0312, PP)],
    },
    {
        "nr": "2", "opis": "Odchylenie sprzedaży od budżetu według marek, 2026/27 narastająco",
        "dax": """EVALUATE CALCULATETABLE ( FILTER ( ADDCOLUMNS ( VALUES ( 'Marka'[Marka] ),
            "ODCH", [Odchylenie sprzedaży ACT vs BUD], "PROC", [Odchylenie sprzedaży ACT vs BUD %] ),
            NOT ISBLANK ( [ODCH] ) ), 'Data'[Rok finansowy] = "2026/27" )""",
        "klucz": "Marka[Marka]",
        "oczek": [("Aurea", "ODCH", -1031000, KW), ("Aurea", "PROC", -0.0059, PP),
                  ("Vento", "ODCH", -16301000, KW), ("Vento", "PROC", -0.0615, PP),
                  ("Lumi", "ODCH", 3812000, KW), ("Lumi", "PROC", 0.0482, PP),
                  ("Kroko", "ODCH", -8352000, KW), ("Kroko", "PROC", -0.0772, PP)],
    },
    {
        "nr": "3", "opis": "Vento Niemcy 1H 2026/27 i opóźnione otwarcia",
        "dax": """EVALUATE CALCULATETABLE ( ROW ( "ACT", [Sprzedaż netto ACT], "BUD", [Sprzedaż netto BUD (miesiące zamknięte)],
            "PROC", [Odchylenie sprzedaży ACT vs BUD %],
            "OPOZNIONE", COUNTROWS ( FILTER ( 'MPK', 'MPK'[Data otwarcia planowana] >= DATE ( 2026, 4, 1 )
                && 'MPK'[Data otwarcia] > 'MPK'[Data otwarcia planowana] ) ) ),
            'Data'[Rok finansowy] = "2026/27", 'Data'[Półrocze finansowe] = "1H",
            'Marka'[Kod marki] = "VEN", 'Kraj'[Kod kraju] = "DE" )""",
        "klucz": None,
        "oczek": [("", "ACT", 43720000, KW), ("", "BUD", 51061000, KW), ("", "PROC", -0.1438, PP),
                  ("", "OPOZNIONE", 4, 0)],
    },
    {
        "nr": "4", "opis": "Pięć sklepów z największym przekroczeniem budżetu czynszów, 2026/27",
        "dax": """EVALUATE TOPN ( 5, CALCULATETABLE ( FILTER ( ADDCOLUMNS ( VALUES ( 'MPK'[Kod MPK] ),
            "ODCH", [Odchylenie kwoty ACT vs BUD] ), NOT ISBLANK ( [ODCH] ) ),
            'Data'[Rok finansowy] = "2026/27", 'Konto'[Numer konta] = "5120" ), [ODCH], DESC )""",
        "klucz": "MPK[Kod MPK]",
        "oczek": [("SK-AUR-AT-002", "ODCH", 96876, KW), ("SK-AUR-AT-003", "ODCH", 65876, KW),
                  ("SK-AUR-AT-004", "ODCH", 62001, KW), ("SK-AUR-AT-001", "ODCH", 60063, KW),
                  ("SK-AUR-AT-005", "ODCH", 56188, KW)],
    },
    {
        "nr": "5", "opis": "Odzież wierzchnia, listopad 2026 wobec listopada 2025",
        "dax": """EVALUATE CALCULATETABLE ( ROW ( "CY", [Sprzedaż netto (kategorie)],
            "LY", [Sprzedaż netto (kategorie) rok wcześniej], "DYN", [Dynamika sprzedaży (kategorie) r/r %] ),
            'Data'[Rok kalendarzowy] = 2026, 'Data'[Miesiąc kalendarzowy nr] = 11, 'Kategoria'[Kod kategorii] = "OW" )""",
        "klucz": None,
        "oczek": [("", "CY", 10761000, KW), ("", "LY", 14926000, KW), ("", "DYN", -0.2790, PP)],
    },
    {
        "nr": "5b", "opis": "Odzież wierzchnia, dynamika r/r według marek",
        "dax": """EVALUATE CALCULATETABLE ( FILTER ( ADDCOLUMNS ( VALUES ( 'Marka'[Kod marki] ),
            "DYN", [Dynamika sprzedaży (kategorie) r/r %] ), NOT ISBLANK ( [DYN] ) ),
            'Data'[Rok kalendarzowy] = 2026, 'Data'[Miesiąc kalendarzowy nr] = 11, 'Kategoria'[Kod kategorii] = "OW" )""",
        "klucz": "Marka[Kod marki]",
        "oczek": [("AUR", "DYN", -0.2938, PP), ("VEN", "DYN", -0.2693, PP)],
    },
    {
        "nr": "6", "opis": "Udział e-commerce w kolejnych latach finansowych (miesiące zamknięte)",
        "dax": """EVALUATE CALCULATETABLE ( FILTER ( ADDCOLUMNS ( VALUES ( 'Data'[Rok finansowy] ),
            "UDZ", [Udział e-commerce %] ), NOT ISBLANK ( [UDZ] ) ), 'Data'[Miesiąc zamknięty] = TRUE () )""",
        "klucz": "Data[Rok finansowy]",
        "oczek": [("2023/24", "UDZ", 0.1800, PP), ("2024/25", "UDZ", 0.1898, PP), ("2025/26", "UDZ", 0.2063, PP),
                  ("2026/27", "UDZ", 0.2309, PP)],
    },
    {
        "nr": "7", "opis": "Black Friday 2025 wobec średniej pozostałych piątków listopada",
        "dax": """EVALUATE
            VAR _bf = CALCULATE ( [Sprzedaż netto (dane dzienne)], 'Data'[Data] = DATE ( 2025, 11, 28 ) )
            VAR _inne = CALCULATE ( AVERAGEX ( VALUES ( 'Data'[Data] ), [Sprzedaż netto (dane dzienne)] ),
                'Data'[Rok kalendarzowy] = 2025, 'Data'[Miesiąc kalendarzowy nr] = 11,
                'Data'[Dzień tygodnia nr] = 5, 'Data'[Data] <> DATE ( 2025, 11, 28 ) )
            RETURN ROW ( "BF", _bf, "INNE", _inne, "KROTNOSC", DIVIDE ( _bf, _inne ) )""",
        "klucz": None,
        "oczek": [("", "BF", 7388000, KW), ("", "INNE", 3510000, KW), ("", "KROTNOSC", 2.105, WSP)],
    },
    {
        "nr": "8", "opis": "Koszt logistyki e-commerce na zamówienie w Niemczech, październik i listopad 2026",
        "dax": """EVALUATE CALCULATETABLE ( ADDCOLUMNS ( VALUES ( 'Data'[Miesiąc kalendarzowy nr] ),
            "ACT", [Koszt logistyki e-commerce na zamówienie ACT], "BUD", [Koszt logistyki e-commerce na zamówienie BUD] ),
            'Data'[Rok kalendarzowy] = 2026, 'Data'[Miesiąc kalendarzowy nr] IN { 10, 11 }, 'Kraj'[Kod kraju] = "DE" )""",
        "klucz": "Data[Miesiąc kalendarzowy nr]",
        "oczek": [(10, "ACT", 30.95, WSP), (10, "BUD", 24.68, WSP), (11, "ACT", 30.95, WSP), (11, "BUD", 25.51, WSP)],
    },
    {
        "nr": "9", "opis": "Prognoza EBITDA 2026/27 wobec budżetu",
        "dax": """EVALUATE CALCULATETABLE ( ROW ( "FC", [EBITDA FC], "BUD", [EBITDA BUD],
            "ODCH", [Odchylenie EBITDA FC vs BUD], "PROC", [Odchylenie EBITDA FC vs BUD %] ),
            'Data'[Rok finansowy] = "2026/27" )""",
        "klucz": None,
        "oczek": [("", "FC", 149380000, KW), ("", "BUD", 161951000, KW), ("", "ODCH", -12570000, KW),
                  ("", "PROC", -0.0776, PP)],
    },
    {
        "nr": "10", "opis": "Pięć sklepów Kroko z najniższą marżą brutto %, 2026/27",
        "dax": """EVALUATE TOPN ( 5, CALCULATETABLE ( FILTER ( ADDCOLUMNS ( VALUES ( 'MPK'[Kod MPK] ),
            "GM", [Marża brutto % ACT] ), NOT ISBLANK ( [GM] ) ),
            'Data'[Rok finansowy] = "2026/27", 'Marka'[Kod marki] = "KRO", 'MPK'[Typ MPK] = "Sklep" ), [GM], ASC )""",
        "klucz": "MPK[Kod MPK]",
        "oczek": [("SK-KRO-PL-016", "GM", 0.5202, PP), ("SK-KRO-DE-003", "GM", 0.5233, PP),
                  ("SK-KRO-PL-010", "GM", 0.5249, PP), ("SK-KRO-PL-002", "GM", 0.5249, PP),
                  ("SK-KRO-SE-001", "GM", 0.5269, PP)],
    },
    {
        "nr": "11", "opis": "Sprzedaż LFL Kroko 2Q 2026/27 rok do roku",
        "dax": """EVALUATE CALCULATETABLE ( ROW ( "LFL", [Sprzedaż LFL], "LY", [Sprzedaż LFL rok wcześniej],
            "DYN", [Dynamika LFL r/r %] ),
            'Data'[Kwartał finansowy pełny] = "2Q 2026/27", 'Marka'[Kod marki] = "KRO" )""",
        "klucz": None,
        "oczek": [("", "LFL", 28319000, KW), ("", "LY", 30471000, KW), ("", "DYN", -0.0706, PP)],
    },
    {
        "nr": "12", "opis": "Koszty IT i licencji (konto 5420), 2025/26 wobec 2024/25",
        "dax": """EVALUATE CALCULATETABLE ( ADDCOLUMNS ( VALUES ( 'Data'[Rok finansowy] ), "ACT", [Kwota ACT] ),
            'Konto'[Numer konta] = "5420", 'Data'[Rok finansowy] IN { "2024/25", "2025/26" } )""",
        "klucz": "Data[Rok finansowy]",
        "oczek": [("2024/25", "ACT", 10835000, KW), ("2025/26", "ACT", 11485000, KW)],
    },
    {
        "nr": "13", "opis": "Sprzedaż w 2029 roku (model nie ma danych, wynik ma być pusty)",
        "dax": """EVALUATE ROW ( "ACT", CALCULATE ( [Sprzedaż netto ACT], 'Data'[Rok kalendarzowy] = 2029 ),
            "BUD", CALCULATE ( [Sprzedaż netto BUD], 'Data'[Rok kalendarzowy] = 2029 ),
            "FC", CALCULATE ( [Sprzedaż netto FC], 'Data'[Rok kalendarzowy] = 2029 ) )""",
        "klucz": None,
        "oczek": [("", "ACT", None, 0), ("", "BUD", None, 0), ("", "FC", None, 0)],
    },
    {
        "nr": "14", "opis": "Bieżący kwartał 3Q 2026/27: P&L za miesiące zamknięte i dane dzienne za grudzień",
        "dax": """EVALUATE CALCULATETABLE ( ROW ( "PNL", [Sprzedaż netto ACT],
            "DZIENNE_OTWARTE", CALCULATE ( [Sprzedaż netto (dane dzienne)], 'Data'[Miesiąc zamknięty] = FALSE () ) ),
            'Data'[Kwartał finansowy pełny] = "3Q 2026/27" )""",
        "klucz": None,
        "oczek": [("", "PNL", 175616000, KW), ("", "DZIENNE_OTWARTE", 30659000, KW)],
    },
]


def testy_planowanie(klucz: dict) -> list[dict]:
    """Testy SM_Planowanie. Oczekiwane wartości pochodzą z fabric/plan/klucz_alokacji_2027_28.json."""
    t = [{
        "nr": "P0", "opis": "Miary bazowe ze stałym rokiem nie zależą od roku w kontekście",
        "dax": """EVALUATE ROW ( "ACT_2526", [Sprzedaz ACT 2025/26],
            "ACT_2526_W_2728", CALCULATE ( [Sprzedaz ACT 2025/26], 'Kalendarz'[Rok finansowy] = "2027/28" ),
            "FC_2627", [Sprzedaz FC 2026/27], "BUD_2627", [Sprzedaz BUD 2026/27] )""",
        "klucz": None,
        "oczek": [("", "ACT_2526", klucz["act_2025_26_grupa"], 1), ("", "ACT_2526_W_2728", klucz["act_2025_26_grupa"], 1),
                  ("", "FC_2627", klucz["fc_2026_27_grupa"], 1), ("", "BUD_2627", klucz["bud_2026_27_grupa"], 1)],
    }, {
        "nr": "P1", "opis": "Profil miesięczny ACT 2025/26 według marek (podstawa alokacji celu)",
        "dax": """EVALUATE FILTER ( ADDCOLUMNS ( CROSSJOIN ( VALUES ( 'Marka'[Kod marki] ), VALUES ( 'Kalendarz'[Miesiac] ) ),
            "ACT", [Sprzedaz ACT 2025/26] ), NOT ISBLANK ( [ACT] ) )""",
        "klucz": ("Marka[Kod marki]", "Kalendarz[Miesiac]"),
        "oczek": [((m["marka"], m["miesiac"]), "ACT", m["act_2025_26"], 1) for m in klucz["marka_miesiac"]],
    }]
    return t


def wartosc(x):
    return None if x is None else float(x)


def sprawdz(ws: str, mid: str, test: dict) -> list[dict]:
    try:
        rows = fa.dax(ws, mid, test["dax"])
    except RuntimeError as e:
        return [{"nr": test["nr"], "opis": test["opis"], "pole": "zapytanie", "oczekiwane": "", "wynik": str(e)[:300],
                 "ok": False}]
    k = test["klucz"]
    if k is None:
        idx = {"": rows[0] if rows else {}}
    elif isinstance(k, tuple):
        idx = {tuple(r.get(c) for c in k): r for r in rows}
    else:
        idx = {r.get(k): r for r in rows}
    out = []
    for key, col, exp, tol in test["oczek"]:
        r = idx.get(key)
        got = None if r is None else wartosc(r.get(f"[{col}]"))
        if exp is None:
            ok = got is None
        else:
            ok = got is not None and abs(got - exp) <= tol
        out.append({"nr": test["nr"], "opis": test["opis"], "pole": f"{key} {col}".strip(),
                    "oczekiwane": exp, "wynik": got, "ok": ok})
    return out


def fmt(v) -> str:
    if v is None:
        return "puste"
    if isinstance(v, float) and abs(v) < 10:
        return f"{v:.4f}".replace(".", ",")
    if isinstance(v, (int, float)):
        return f"{v:,.0f}".replace(",", " ")
    return str(v)


def main() -> None:
    st = json.loads(STAN.read_text(encoding="utf-8"))
    ws = st["workspaceId"]
    wyniki = []
    for t in TESTY_KONTROLING:
        wyniki += sprawdz(ws, st["modele"]["SM_Kontroling"], t)
    plik_klucza = REPO / "fabric" / "plan" / "klucz_alokacji_2027_28.json"
    if "SM_Planowanie" in st.get("modele", {}) and plik_klucza.exists():
        klucz = json.loads(plik_klucza.read_text(encoding="utf-8"))
        for t in testy_planowanie(klucz):
            wyniki += sprawdz(ws, st["modele"]["SM_Planowanie"], t)
    ok = sum(w["ok"] for w in wyniki)
    linie = ["# Wyniki weryfikacji DAX", "",
             "Plik generuje `fabric/deploy/weryfikuj_model.py` na wdrożonych modelach. Oczekiwane wartości pochodzą z "
             "klucza odpowiedzi generatora (`dane/oczekiwane_odpowiedzi.csv`) i klucza alokacji planu "
             "(`fabric/plan/klucz_alokacji_2027_28.json`).", "",
             f"Wynik: {ok} z {len(wyniki)} sprawdzeń zgodnych.", "",
             "| Pytanie | Opis | Pole | Oczekiwane | Wynik modelu | Zgodne |", "|---|---|---|---:|---:|---|"]
    for w in wyniki:
        linie.append(f"| {w['nr']} | {w['opis']} | {w['pole']} | {fmt(w['oczekiwane'])} | {fmt(w['wynik'])} | "
                     f"{'tak' if w['ok'] else 'NIE'} |")
        if not w["ok"]:
            print(f"NIEZGODNE {w['nr']} {w['pole']}: oczekiwane {w['oczekiwane']}, wynik {w['wynik']}")
    WYNIK.parent.mkdir(exist_ok=True)
    WYNIK.write_text("\n".join(linie) + "\n", encoding="utf-8")
    print(f"{ok}/{len(wyniki)} zgodnych, szczegóły w {WYNIK.relative_to(REPO)}")
    sys.exit(0 if ok == len(wyniki) else 1)


if __name__ == "__main__":
    main()
