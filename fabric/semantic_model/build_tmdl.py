"""Generuje definicje TMDL trzech modeli semantycznych Direct Lake.

SM_Kontroling          model przygotowany dla AI: polskie nazwy, opisy, miary, ukryte klucze
SM_Kontroling_surowy   ten sam zestaw tabel bez przygotowania (nazwy techniczne, brak miar i opisów)
SM_Planowanie          model pod Plan w Fabric IQ: miesiące, marki, kraje, kanały, nazwy tylko ASCII

Uruchomienie: python fabric/semantic_model/build_tmdl.py
Wynik: fabric/semantic_model/<model>/definition.pbism oraz definition/*.tmdl
Znaczniki {{SQL_ENDPOINT}} i {{SQL_ENDPOINT_ID}} podmienia skrypt wdrożeniowy.
"""
from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent
NS = uuid.UUID("6f1c2a52-6a8e-4c39-9d0f-2b7a3e1d5c10")


def tag(*parts: str) -> str:
    return str(uuid.uuid5(NS, "|".join(parts)))


def q(name: str) -> str:
    return "'" + name.replace("'", "''") + "'"


# Schemat tabel źródłowych w lakehouse (zgodny z generator/SPEC.md)
SOURCE: dict[str, list[tuple[str, str]]] = {
    "dim_data": [
        ("data", "dateTime"), ("rok", "int64"), ("miesiac", "int64"), ("miesiac_nazwa", "string"),
        ("miesiac_skrot", "string"), ("miesiac_poczatek", "dateTime"), ("okres_rrrrmm", "int64"),
        ("dzien_tygodnia_nr", "int64"), ("dzien_tygodnia_nazwa", "string"), ("tydzien_iso", "int64"),
        ("rok_finansowy", "string"), ("rok_finansowy_nr", "int64"), ("kwartal_finansowy", "string"),
        ("kwartal_finansowy_pelny", "string"), ("kwartal_finansowy_sort", "int64"),
        ("polrocze_finansowe", "string"), ("miesiac_finansowy_nr", "int64"), ("czy_swieto_pl", "boolean"),
        ("nazwa_swieta", "string"), ("czy_niedziela_handlowa_pl", "boolean"), ("czy_dzien_handlowy_pl", "boolean"),
        ("czy_black_friday", "boolean"), ("czy_miesiac_zamkniety", "boolean"),
    ],
    "dim_marka": [("marka_kod", "string"), ("marka_nazwa", "string"), ("grupa_docelowa", "string"), ("kolejnosc", "int64")],
    "dim_kraj": [("kraj_kod", "string"), ("kraj_nazwa", "string"), ("waluta_lokalna", "string"), ("region", "string")],
    "dim_kategoria": [("kategoria_kod", "string"), ("kategoria_nazwa", "string"), ("grupa", "string")],
    "dim_scenariusz": [("scenariusz_kod", "string"), ("scenariusz_nazwa", "string"), ("opis", "string"), ("kolejnosc", "int64")],
    "dim_konto": [("konto_id", "string"), ("konto_nazwa", "string"), ("sekcja", "string"), ("grupa_kosztow", "string"),
                  ("znak", "int64"), ("kolejnosc", "int64")],
    "dim_mpk": [
        ("mpk_id", "string"), ("mpk_nazwa", "string"), ("typ_mpk", "string"), ("kanal", "string"), ("marka_kod", "string"),
        ("kraj_kod", "string"), ("miasto", "string"), ("format_sklepu", "string"), ("powierzchnia_m2", "int64"),
        ("dzial_centrali", "string"), ("data_otwarcia_plan", "dateTime"), ("data_otwarcia", "dateTime"),
        ("data_zamkniecia", "dateTime"), ("status", "string"), ("lfl_od", "dateTime"),
    ],
    "fakt_pnl": [("miesiac", "dateTime"), ("mpk_id", "string"), ("konto_id", "string"), ("scenariusz_kod", "string"),
                 ("kwota_pln", "double")],
    "fakt_sprzedaz_dzienna": [("data", "dateTime"), ("mpk_id", "string"), ("sprzedaz_netto_pln", "double"),
                              ("koszt_wlasny_pln", "double"), ("liczba_paragonow", "int64"), ("liczba_sztuk", "int64")],
    "fakt_sprzedaz_kategorie_mies": [("miesiac", "dateTime"), ("marka_kod", "string"), ("kraj_kod", "string"),
                                     ("kanal", "string"), ("kategoria_kod", "string"), ("sprzedaz_netto_pln", "double"),
                                     ("koszt_wlasny_pln", "double"), ("liczba_sztuk", "int64")],
    "fakt_kursy_walut": [("miesiac", "dateTime"), ("waluta", "string"), ("kurs_sredni_pln", "double")],
}

MODEL_TABLES = ["dim_data", "dim_marka", "dim_kraj", "dim_kategoria", "dim_scenariusz", "dim_konto", "dim_mpk",
                "fakt_pnl", "fakt_sprzedaz_dzienna", "fakt_sprzedaz_kategorie_mies", "fakt_kursy_walut"]

KWOTA = "#,0"
PROC = "0.0%"
WSK = "#,0.00"
DATA_FMT = "yyyy-mm-dd"

# Kolumny: (kolumna źródłowa, nazwa w modelu, opis, opcje)
CURATED: dict[str, dict] = {
    "dim_data": {
        "name": "Data",
        "time": True,
        "desc": ("Kalendarz dzienny od 1.04.2023 do 31.03.2028 z atrybutami roku finansowego. Rok finansowy trwa od "
                 "1 kwietnia do 31 marca, np. 2026/27 to okres od 1.04.2026 do 31.03.2027. Kwartały finansowe: 1Q kwiecień "
                 "do czerwca, 2Q lipiec do września, 3Q październik do grudnia, 4Q styczeń do marca. Tabele miesięczne "
                 "są połączone z pierwszym dniem miesiąca, dlatego okresy miesięczne filtruj kolumnami roku, kwartału "
                 "lub miesiąca, a nie pojedynczym dniem."),
        "cols": [
            ("data", "Data", "Dzień kalendarzowy, klucz kalendarza.", {"key": True, "fmt": DATA_FMT}),
            ("rok", "Rok kalendarzowy", "Rok kalendarzowy (styczeń do grudnia). Nie myl z rokiem finansowym.", {}),
            ("miesiac", "Miesiąc kalendarzowy nr", "Numer miesiąca kalendarzowego, 1 to styczeń.", {}),
            ("miesiac_nazwa", "Miesiąc", "Nazwa miesiąca po polsku, sortowana w kolejności roku finansowego (od kwietnia).",
             {"sort": "Miesiąc finansowy nr"}),
            ("miesiac_skrot", "Miesiąc skrót", "Skrót nazwy miesiąca, np. wrz.", {"sort": "Miesiąc finansowy nr"}),
            ("miesiac_poczatek", "Początek miesiąca", "Pierwszy dzień miesiąca.", {"fmt": DATA_FMT}),
            ("okres_rrrrmm", "Okres RRRRMM", "Okres kalendarzowy jako liczba, np. 202609 to wrzesień 2026.", {}),
            ("dzien_tygodnia_nr", "Dzień tygodnia nr", "1 to poniedziałek, 7 to niedziela.", {}),
            ("dzien_tygodnia_nazwa", "Dzień tygodnia", "Nazwa dnia tygodnia po polsku.", {"sort": "Dzień tygodnia nr"}),
            ("tydzien_iso", "Tydzień ISO", "Numer tygodnia według ISO 8601.", {}),
            ("rok_finansowy", "Rok finansowy",
             "Rok finansowy od kwietnia do marca, np. 2026/27. Domyślny sens słowa rok w pytaniach o wyniki.",
             {"sort": "Rok finansowy nr"}),
            ("rok_finansowy_nr", "Rok finansowy nr",
             "Rok kalendarzowy, w którym zaczyna się rok finansowy, np. 2026 dla 2026/27.", {}),
            ("kwartal_finansowy", "Kwartał finansowy", "Kwartał roku finansowego: 1Q, 2Q, 3Q lub 4Q.", {}),
            ("kwartal_finansowy_pelny", "Kwartał finansowy pełny", "Kwartał z rokiem finansowym, np. 3Q 2026/27.",
             {"sort": "Kwartał finansowy sort"}),
            ("kwartal_finansowy_sort", "Kwartał finansowy sort", "Klucz sortowania kwartałów.", {"hidden": True}),
            ("polrocze_finansowe", "Półrocze finansowe", "1H to kwiecień do września, 2H to październik do marca.", {}),
            ("miesiac_finansowy_nr", "Miesiąc finansowy nr",
             "Numer miesiąca w roku finansowym, 1 to kwiecień, 12 to marzec.", {}),
            ("czy_swieto_pl", "Święto w Polsce", "Prawda, jeśli dzień jest świętem ustawowo wolnym w Polsce.", {}),
            ("nazwa_swieta", "Nazwa święta", "Nazwa święta w Polsce.", {}),
            ("czy_niedziela_handlowa_pl", "Niedziela handlowa w Polsce", "Prawda dla niedzieli handlowej w Polsce.", {}),
            ("czy_dzien_handlowy_pl", "Dzień handlowy w Polsce",
             "Prawda, jeśli sklepy stacjonarne w Polsce mogły być otwarte.", {}),
            ("czy_black_friday", "Black Friday", "Prawda dla ostatniego piątku listopada.", {}),
            ("czy_miesiac_zamkniety", "Miesiąc zamknięty",
             "Prawda dla miesięcy zamkniętych księgowo (do listopada 2026 włącznie). Wykonanie (ACT) w rachunku "
             "wyników istnieje tylko dla tych miesięcy.", {}),
        ],
    },
    "dim_marka": {
        "name": "Marka",
        "desc": "Słownik marek. Kod GRP oznacza centralę i koszty bez przypisanej marki.",
        "cols": [
            ("marka_kod", "Kod marki", "Kod marki: AUR, VEN, LUM, KRO lub GRP dla centrali.", {}),
            ("marka_nazwa", "Marka", "Nazwa marki: Aurea, Vento, Lumi, Kroko albo centrala.",
             {"sort": "Kolejność marki"}),
            ("grupa_docelowa", "Grupa docelowa", "Główna grupa klientów marki.", {}),
            ("kolejnosc", "Kolejność marki", "Kolejność prezentacji marek.", {"hidden": True}),
        ],
    },
    "dim_kraj": {
        "name": "Kraj",
        "desc": "Słownik krajów działalności z walutą lokalną i regionem. Centrala jest przypisana do Polski.",
        "cols": [
            ("kraj_kod", "Kod kraju", "Dwuliterowy kod kraju, np. PL, DE, SE.", {}),
            ("kraj_nazwa", "Kraj", "Nazwa kraju po polsku.", {}),
            ("waluta_lokalna", "Waluta lokalna", "Waluta lokalna kraju. Kwoty w modelu są zawsze w PLN.", {}),
            ("region", "Region", "Region sprzedaży.", {}),
        ],
    },
    "dim_kategoria": {
        "name": "Kategoria",
        "desc": "Słownik kategorii towarowych używanych w tabeli Sprzedaż według kategorii.",
        "cols": [
            ("kategoria_kod", "Kod kategorii", "Kod kategorii towarowej, np. OW to odzież wierzchnia.", {}),
            ("kategoria_nazwa", "Kategoria", "Nazwa kategorii towarowej, np. Odzież wierzchnia.", {}),
            ("grupa", "Grupa kategorii", "Grupa kategorii, np. Odzież, Obuwie, Akcesoria.", {}),
        ],
    },
    "dim_scenariusz": {
        "name": "Scenariusz",
        "desc": ("Scenariusze danych finansowych. ACT to wykonanie, BUD to budżet, FC to prognoza 8+4 dla roku "
                 "finansowego 2026/27 (wykonanie kwiecień do listopada 2026 i prognoza grudzień 2026 do marca 2027)."),
        "cols": [
            ("scenariusz_kod", "Kod scenariusza", "ACT, BUD albo FC.", {}),
            ("scenariusz_nazwa", "Scenariusz", "Nazwa scenariusza.", {"sort": "Kolejność scenariusza"}),
            ("opis", "Opis scenariusza", "Opis zakresu scenariusza.", {}),
            ("kolejnosc", "Kolejność scenariusza", "Kolejność prezentacji.", {"hidden": True}),
        ],
    },
    "dim_konto": {
        "name": "Konto",
        "desc": ("Plan kont rachunku wyników (P&L). Kwoty w faktach są dodatnie, a kolumna Znak mówi, czy pozycja "
                 "zwiększa wynik (1, przychody) czy go zmniejsza (-1, koszty). Marża brutto, EBITDA i EBIT są "
                 "liczone miarami."),
        "cols": [
            ("konto_id", "Numer konta",
             "Numer konta jako tekst, np. 4010 przychody, 5120 czynsze, 5220 logistyka e-commerce.", {}),
            ("konto_nazwa", "Konto", "Nazwa pozycji rachunku wyników, np. Czynsze.", {"sort": "Kolejność konta"}),
            ("sekcja", "Sekcja P&L",
             "Sekcja rachunku wyników: Przychody, Koszt własny, Koszty operacyjne, Amortyzacja.", {}),
            ("grupa_kosztow", "Grupa kosztów", "Grupa pozycji, np. koszty sklepów, e-commerce, centrali.", {}),
            ("znak", "Znak", "1 dla przychodów, -1 dla kosztów.", {"hidden": True}),
            ("kolejnosc", "Kolejność konta", "Kolejność pozycji w rachunku wyników.", {"hidden": True}),
        ],
    },
    "dim_mpk": {
        "name": "MPK",
        "desc": ("Miejsca powstawania kosztów: sklepy stacjonarne, kanały e-commerce (jeden na markę i kraj) oraz "
                 "działy centrali. Zawiera daty otwarcia planowane i rzeczywiste, datę zamknięcia oraz datę, od której "
                 "sklep jest porównywalny rok do roku (LFL). Porównanie daty planowanej z rzeczywistą wyjaśnia "
                 "opóźnienia otwarć."),
        "cols": [
            ("mpk_id", "Kod MPK",
             "Kod MPK, np. SK-AUR-AT-001 dla sklepu, EC-AUR-PL dla e-commerce, HQ-TEC dla działu centrali.", {}),
            ("mpk_nazwa", "Nazwa MPK", "Nazwa MPK, np. Aurea Graz 2.", {}),
            ("typ_mpk", "Typ MPK", "Sklep, E-commerce albo Centrala.", {}),
            ("kanal", "Kanał", "Kanał: Sklep, E-commerce albo Centrala.", {}),
            ("marka_kod", "Kod marki MPK", "Klucz do tabeli Marka.", {"hidden": True}),
            ("kraj_kod", "Kod kraju MPK", "Klucz do tabeli Kraj.", {"hidden": True}),
            ("miasto", "Miasto", "Miasto sklepu. Puste dla e-commerce i centrali.", {}),
            ("format_sklepu", "Format sklepu", "Format lokalizacji sklepu.", {}),
            ("powierzchnia_m2", "Powierzchnia m2", "Powierzchnia sprzedaży sklepu w metrach kwadratowych.",
             {"sum": True}),
            ("dzial_centrali", "Dział centrali", "Dział centrali, np. Technologia, Finanse, Marketing.", {}),
            ("data_otwarcia_plan", "Data otwarcia planowana", "Data otwarcia przyjęta w budżecie.", {"fmt": DATA_FMT}),
            ("data_otwarcia", "Data otwarcia", "Rzeczywista data otwarcia. Pusta dla sklepów planowanych.",
             {"fmt": DATA_FMT}),
            ("data_zamkniecia", "Data zamknięcia", "Data zamknięcia sklepu, pusta dla działających.", {"fmt": DATA_FMT}),
            ("status", "Status", "Aktywny, Zamknięty albo Planowany.", {}),
            ("lfl_od", "LFL od",
             "Pierwszy dzień miesiąca, od którego sklep wchodzi do bazy porównywalnej (LFL), czyli po 12 pełnych "
             "miesiącach działania.", {"fmt": DATA_FMT}),
        ],
    },
    "fakt_pnl": {
        "name": "Rachunek wyników",
        "desc": ("Miesięczny rachunek wyników (P&L) na poziomie MPK, konta i scenariusza, w PLN. Wykonanie (ACT) "
                 "obejmuje tylko miesiące zamknięte, od kwietnia 2023 do listopada 2026. Budżet (BUD) obejmuje lata "
                 "finansowe 2024/25, 2025/26 i 2026/27. Prognoza (FC 8+4) obejmuje rok 2026/27. Używaj miar, nie "
                 "sumuj kwot bez filtra scenariusza i konta."),
        "cols": [
            ("miesiac", "miesiac", "Pierwszy dzień miesiąca, klucz do kalendarza.", {"hidden": True, "fmt": DATA_FMT}),
            ("mpk_id", "mpk_id", "Klucz MPK.", {"hidden": True}),
            ("konto_id", "konto_id", "Klucz konta.", {"hidden": True}),
            ("scenariusz_kod", "scenariusz_kod", "Klucz scenariusza.", {"hidden": True}),
            ("kwota_pln", "kwota_pln", "Kwota dodatnia w PLN.", {"hidden": True, "fmt": KWOTA}),
        ],
    },
    "fakt_sprzedaz_dzienna": {
        "name": "Sprzedaż dzienna",
        "desc": ("Sprzedaż dzienna sklepów i e-commerce w PLN od 1.04.2023 do 8.12.2026. Obejmuje także dni miesięcy "
                 "jeszcze niezamkniętych (grudzień 2026), dlatego służy do bieżącej sprzedaży, analiz dziennych, "
                 "paragonów i LFL. Brak wiersza oznacza dzień, w którym sklep był zamknięty. W e-commerce liczba "
                 "paragonów oznacza liczbę zamówień."),
        "cols": [
            ("data", "data", "Dzień sprzedaży.", {"hidden": True, "fmt": DATA_FMT}),
            ("mpk_id", "mpk_id", "Klucz MPK.", {"hidden": True}),
            ("sprzedaz_netto_pln", "sprzedaz_netto_pln", "Sprzedaż netto PLN.", {"hidden": True, "fmt": KWOTA}),
            ("koszt_wlasny_pln", "koszt_wlasny_pln", "Koszt własny PLN.", {"hidden": True, "fmt": KWOTA}),
            ("liczba_paragonow", "liczba_paragonow", "Liczba paragonów lub zamówień.", {"hidden": True}),
            ("liczba_sztuk", "liczba_sztuk", "Liczba sztuk.", {"hidden": True}),
        ],
    },
    "fakt_sprzedaz_kategorie_mies": {
        "name": "Sprzedaż według kategorii",
        "desc": ("Miesięczna sprzedaż według kategorii towarowych, marek, krajów i kanałów (Sklep, E-commerce) za "
                 "miesiące zamknięte, od kwietnia 2023 do listopada 2026, w PLN. Sumy zgadzają się z danymi dziennymi."),
        "cols": [
            ("miesiac", "miesiac", "Pierwszy dzień miesiąca.", {"hidden": True, "fmt": DATA_FMT}),
            ("marka_kod", "marka_kod", "Klucz marki.", {"hidden": True}),
            ("kraj_kod", "kraj_kod", "Klucz kraju.", {"hidden": True}),
            ("kanal", "Kanał sprzedaży", "Sklep albo E-commerce. Tą kolumną filtruj kanał w analizach kategorii.", {}),
            ("kategoria_kod", "kategoria_kod", "Klucz kategorii.", {"hidden": True}),
            ("sprzedaz_netto_pln", "sprzedaz_netto_pln", "Sprzedaż netto PLN.", {"hidden": True, "fmt": KWOTA}),
            ("koszt_wlasny_pln", "koszt_wlasny_pln", "Koszt własny PLN.", {"hidden": True, "fmt": KWOTA}),
            ("liczba_sztuk", "liczba_sztuk", "Liczba sztuk.", {"hidden": True}),
        ],
    },
    "fakt_kursy_walut": {
        "name": "Kursy walut",
        "desc": "Średnie miesięczne kursy walut w PLN za jednostkę waluty. Informacyjnie, kwoty w modelu są już w PLN.",
        "cols": [
            ("miesiac", "miesiac", "Pierwszy dzień miesiąca.", {"hidden": True, "fmt": DATA_FMT}),
            ("waluta", "Waluta", "Kod waluty: EUR, SEK, DKK.", {}),
            ("kurs_sredni_pln", "kurs_sredni_pln", "Średni kurs w PLN.", {"hidden": True}),
        ],
    },
}

RELATIONSHIPS = [
    ("fakt_pnl", "miesiac", "dim_data", "data"),
    ("fakt_pnl", "mpk_id", "dim_mpk", "mpk_id"),
    ("fakt_pnl", "konto_id", "dim_konto", "konto_id"),
    ("fakt_pnl", "scenariusz_kod", "dim_scenariusz", "scenariusz_kod"),
    ("fakt_sprzedaz_dzienna", "data", "dim_data", "data"),
    ("fakt_sprzedaz_dzienna", "mpk_id", "dim_mpk", "mpk_id"),
    ("dim_mpk", "marka_kod", "dim_marka", "marka_kod"),
    ("dim_mpk", "kraj_kod", "dim_kraj", "kraj_kod"),
    ("fakt_sprzedaz_kategorie_mies", "miesiac", "dim_data", "data"),
    ("fakt_sprzedaz_kategorie_mies", "marka_kod", "dim_marka", "marka_kod"),
    ("fakt_sprzedaz_kategorie_mies", "kraj_kod", "dim_kraj", "kraj_kod"),
    ("fakt_sprzedaz_kategorie_mies", "kategoria_kod", "dim_kategoria", "kategoria_kod"),
    ("fakt_kursy_walut", "miesiac", "dim_data", "data"),
]

RW = "Rachunek wyników"
SD = "Sprzedaż dzienna"
SK = "Sprzedaż według kategorii"
ZAMK = "KEEPFILTERS ( 'Data'[Miesiąc zamknięty] = TRUE () )"

SCEN = {
    "ACT": ("1. Wykonanie (ACT)", "wykonanie (ACT), tylko miesiące zamknięte do listopada 2026"),
    "BUD": ("2. Budżet (BUD)", "budżet (BUD) dla lat finansowych 2024/25, 2025/26 i 2026/27"),
    "FC": ("3. Prognoza (FC)", "prognoza 8+4 (FC) dla roku finansowego 2026/27"),
}


def measures() -> list[tuple[str, str, str, str, str, str]]:
    """Lista miar: (tabela, nazwa, DAX, format, folder, opis)."""
    m: list[tuple[str, str, str, str, str, str]] = []

    def add(t: str, n: str, d: str, f: str, fo: str, o: str) -> None:
        m.append((t, n, d.strip(), f, fo, o))

    add(RW, "Kwota (jeden scenariusz)",
        "IF ( HASONEVALUE ( 'Scenariusz'[Kod scenariusza] ), SUM ( 'Rachunek wyników'[kwota_pln] ) )",
        KWOTA, "0. Pomocnicze",
        "Suma kwot rachunku wyników dla dokładnie jednego scenariusza wybranego filtrem. Bez filtra scenariusza "
        "zwraca pustą wartość, żeby nie dodawać wykonania do budżetu. Kwoty są dodatnie, także koszty.")

    for s, (folder, opis) in SCEN.items():
        add(RW, f"Kwota {s}",
            "CALCULATE ( SUM ( 'Rachunek wyników'[kwota_pln] ), REMOVEFILTERS ( 'Scenariusz' ), "
            f"'Scenariusz'[Kod scenariusza] = \"{s}\" )",
            KWOTA, folder,
            f"Kwota w PLN dla scenariusza {opis}. Działa dla dowolnego konta lub grupy kont wybranych filtrem "
            "tabeli Konto, np. czynsze to konto 5120. Koszty są dodatnie.")
        add(RW, f"Sprzedaż netto {s}",
            f"CALCULATE ( [Kwota {s}], REMOVEFILTERS ( 'Konto' ), 'Konto'[Numer konta] = \"4010\" )",
            KWOTA, folder, f"Przychody ze sprzedaży netto (konto 4010) w PLN, {opis}.")
        add(RW, f"Koszt własny {s}",
            f"CALCULATE ( [Kwota {s}], REMOVEFILTERS ( 'Konto' ), 'Konto'[Numer konta] = \"4510\" )",
            KWOTA, folder, f"Koszt własny sprzedaży (konto 4510) w PLN, {opis}.")
        add(RW, f"Marża brutto {s}", f"[Sprzedaż netto {s}] - [Koszt własny {s}]",
            KWOTA, folder, f"Marża brutto w PLN (sprzedaż netto minus koszt własny), {opis}.")
        add(RW, f"Marża brutto % {s}", f"DIVIDE ( [Marża brutto {s}], [Sprzedaż netto {s}] )",
            PROC, folder, f"Marża brutto jako procent sprzedaży netto, {opis}.")
        add(RW, f"Koszty operacyjne {s}",
            f"CALCULATE ( [Kwota {s}], REMOVEFILTERS ( 'Konto' ), 'Konto'[Sekcja P&L] = \"Koszty operacyjne\" )",
            KWOTA, folder, f"Suma kosztów operacyjnych w PLN, {opis}.")
        add(RW, f"EBITDA {s}", f"[Marża brutto {s}] - [Koszty operacyjne {s}]",
            KWOTA, folder, f"EBITDA w PLN: marża brutto minus koszty operacyjne, {opis}.")
        add(RW, f"EBITDA % {s}", f"DIVIDE ( [EBITDA {s}], [Sprzedaż netto {s}] )",
            PROC, folder, f"Marża EBITDA jako procent sprzedaży netto, {opis}.")
        add(RW, f"Amortyzacja {s}",
            f"CALCULATE ( [Kwota {s}], REMOVEFILTERS ( 'Konto' ), 'Konto'[Sekcja P&L] = \"Amortyzacja\" )",
            KWOTA, folder, f"Amortyzacja w PLN, {opis}.")
        add(RW, f"EBIT {s}", f"[EBITDA {s}] - [Amortyzacja {s}]",
            KWOTA, folder, f"EBIT w PLN: EBITDA minus amortyzacja, {opis}.")

    fo = "4. Odchylenia"
    for base in ["Kwota", "Sprzedaż netto", "Marża brutto", "Koszty operacyjne", "EBITDA"]:
        add(RW, f"{base} BUD (miesiące zamknięte)", f"CALCULATE ( [{base} BUD], {ZAMK} )", KWOTA, fo,
            f"{base} według budżetu ograniczona do miesięcy zamkniętych, czyli tych, dla których istnieje wykonanie. "
            "Służy do porównania wykonania z budżetem za ten sam okres.")
    pairs = [("sprzedaży", "Sprzedaż netto", False), ("marży brutto", "Marża brutto", False),
             ("kosztów operacyjnych", "Koszty operacyjne", False), ("EBITDA", "EBITDA", True),
             ("kwoty", "Kwota", False)]
    for label, base, use_abs in pairs:
        diff = f"Odchylenie {label} ACT vs BUD"
        sens = ("Dla kosztów wartość dodatnia oznacza przekroczenie budżetu."
                if base in ("Kwota", "Koszty operacyjne") else "Wartość ujemna oznacza wynik poniżej budżetu.")
        add(RW, diff, f"[{base} ACT] - [{base} BUD (miesiące zamknięte)]", KWOTA, fo,
            f"Wykonanie minus budżet w PLN dla pozycji {base}, tylko za miesiące zamknięte. {sens}")
        den = f"ABS ( [{base} BUD (miesiące zamknięte)] )" if use_abs else f"[{base} BUD (miesiące zamknięte)]"
        add(RW, f"{diff} %", f"DIVIDE ( [{diff}], {den} )", PROC, fo,
            f"Odchylenie wykonania od budżetu dla pozycji {base} jako procent budżetu, tylko miesiące zamknięte.")
    add(RW, "Odchylenie marży brutto % ACT vs BUD (pp)",
        "[Marża brutto % ACT] - DIVIDE ( [Marża brutto BUD (miesiące zamknięte)], "
        "[Sprzedaż netto BUD (miesiące zamknięte)] )",
        PROC, fo,
        "Różnica marży brutto procentowej wykonania i budżetu w punktach procentowych, tylko miesiące zamknięte.")
    for label, base, use_abs in [("sprzedaży", "Sprzedaż netto", False), ("EBITDA", "EBITDA", True),
                                 ("kwoty", "Kwota", False)]:
        diff = f"Odchylenie {label} FC vs BUD"
        add(RW, diff, f"[{base} FC] - [{base} BUD]", KWOTA, fo,
            f"Prognoza 8+4 minus budżet w PLN dla pozycji {base}. Ma sens dla roku finansowego 2026/27.")
        den = f"ABS ( [{base} BUD] )" if use_abs else f"[{base} BUD]"
        add(RW, f"{diff} %", f"DIVIDE ( [{diff}], {den} )", PROC, fo,
            f"Odchylenie prognozy od budżetu dla pozycji {base} jako procent budżetu.")

    fo = "5. Rok do roku"
    shift = "DATEADD ( CALCULATETABLE ( VALUES ( 'Data'[Data] ), " + ZAMK + " ), -1, YEAR )"
    for base, label in [("Sprzedaż netto", "sprzedaży"), ("EBITDA", "EBITDA"), ("Kwota", "kwoty"),
                        ("Marża brutto", "marży brutto")]:
        ly = f"{base} ACT rok wcześniej"
        add(RW, ly, f"CALCULATE ( [{base} ACT], {shift} )", KWOTA, fo,
            f"{base} według wykonania za analogiczne miesiące zamknięte rok wcześniej (przesunięcie o 12 miesięcy).")
        add(RW, f"Dynamika {label} ACT r/r %",
            f"VAR _ly = [{ly}]\nRETURN\n    DIVIDE ( [{base} ACT] - _ly, ABS ( _ly ) )", PROC, fo,
            f"Zmiana rok do roku pozycji {base} według wykonania, w procentach, za miesiące zamknięte.")

    fo = "6. Wskaźniki"
    add(RW, "Koszt logistyki e-commerce na zamówienie ACT",
        "DIVIDE (\n    CALCULATE ( [Kwota ACT], REMOVEFILTERS ( 'Konto' ), 'Konto'[Numer konta] = \"5220\" ),\n"
        "    CALCULATE ( [Liczba zamówień e-commerce], " + ZAMK + " )\n)", WSK, fo,
        "Koszt logistyki e-commerce (konto 5220) według wykonania podzielony przez liczbę zamówień e-commerce, "
        "w PLN na zamówienie.")
    add(RW, "Koszt logistyki e-commerce na zamówienie BUD",
        "DIVIDE (\n    CALCULATE ( [Kwota BUD (miesiące zamknięte)], REMOVEFILTERS ( 'Konto' ), "
        "'Konto'[Numer konta] = \"5220\" ),\n"
        "    CALCULATE ( [Liczba zamówień e-commerce], " + ZAMK + " )\n)", WSK, fo,
        "Budżetowy koszt logistyki e-commerce (konto 5220) podzielony przez faktyczną liczbę zamówień, "
        "w PLN na zamówienie.")

    fo = "Sprzedaż dzienna"
    add(SD, "Sprzedaż netto (dane dzienne)", "SUM ( 'Sprzedaż dzienna'[sprzedaz_netto_pln] )", KWOTA, fo,
        "Sprzedaż netto w PLN z danych dziennych, dostępna do 8.12.2026, także dla miesięcy niezamkniętych.")
    add(SD, "Koszt własny (dane dzienne)", "SUM ( 'Sprzedaż dzienna'[koszt_wlasny_pln] )", KWOTA, fo,
        "Koszt własny sprzedaży w PLN z danych dziennych.")
    add(SD, "Marża brutto (dane dzienne)", "[Sprzedaż netto (dane dzienne)] - [Koszt własny (dane dzienne)]",
        KWOTA, fo, "Marża brutto w PLN z danych dziennych.")
    add(SD, "Marża brutto % (dane dzienne)",
        "DIVIDE ( [Marża brutto (dane dzienne)], [Sprzedaż netto (dane dzienne)] )",
        PROC, fo, "Marża brutto procentowa z danych dziennych.")
    add(SD, "Liczba paragonów", "SUM ( 'Sprzedaż dzienna'[liczba_paragonow] )", "#,0", fo,
        "Liczba paragonów w sklepach, a w e-commerce liczba zamówień.")
    add(SD, "Liczba zamówień e-commerce",
        "CALCULATE ( [Liczba paragonów], KEEPFILTERS ( 'MPK'[Typ MPK] = \"E-commerce\" ) )", "#,0", fo,
        "Liczba zamówień w kanale e-commerce.")
    add(SD, "Liczba sztuk", "SUM ( 'Sprzedaż dzienna'[liczba_sztuk] )", "#,0", fo, "Liczba sprzedanych sztuk.")
    add(SD, "Średnia wartość paragonu", "DIVIDE ( [Sprzedaż netto (dane dzienne)], [Liczba paragonów] )", WSK, fo,
        "Średnia wartość paragonu lub zamówienia netto w PLN.")
    add(SD, "Sztuki na paragon", "DIVIDE ( [Liczba sztuk], [Liczba paragonów] )", WSK, fo,
        "Średnia liczba sztuk na paragon lub zamówienie.")
    add(SD, "Ostatni dzień z danymi dziennymi", "CALCULATE ( MAX ( 'Sprzedaż dzienna'[data] ), REMOVEFILTERS () )",
        DATA_FMT, fo, "Ostatni dzień, dla którego istnieją dane dzienne (stan danych).")
    add(SD, "Sprzedaż netto (dane dzienne) rok wcześniej",
        "VAR _ost = [Ostatni dzień z danymi dziennymi]\nRETURN\n    CALCULATE (\n"
        "        [Sprzedaż netto (dane dzienne)],\n"
        "        DATEADD ( FILTER ( VALUES ( 'Data'[Data] ), 'Data'[Data] <= _ost ), -1, YEAR )\n    )", KWOTA, fo,
        "Sprzedaż netto z danych dziennych za te same dni rok wcześniej. Okres bieżący jest obcinany do "
        "ostatniego dnia z danymi.")
    add(SD, "Dynamika sprzedaży (dane dzienne) r/r %",
        "VAR _ly = [Sprzedaż netto (dane dzienne) rok wcześniej]\nVAR _ost = [Ostatni dzień z danymi dziennymi]\n"
        "VAR _cy = CALCULATE ( [Sprzedaż netto (dane dzienne)], KEEPFILTERS ( 'Data'[Data] <= _ost ) )\n"
        "RETURN\n    DIVIDE ( _cy - _ly, _ly )",
        PROC, fo, "Zmiana sprzedaży netto rok do roku z danych dziennych, dla tych samych dni.")
    lfl_vars = (
        "VAR _od = MIN ( 'Data'[Data] )\n"
        "VAR _do = MIN ( MAX ( 'Data'[Data] ), [Ostatni dzień z danymi dziennymi] )\n"
        "VAR _sklepy =\n    CALCULATETABLE (\n        VALUES ( 'MPK'[Kod MPK] ),\n"
        "        KEEPFILTERS ( 'MPK'[Typ MPK] = \"Sklep\" ),\n"
        "        KEEPFILTERS ( 'MPK'[LFL od] <= _od ),\n"
        "        KEEPFILTERS ( OR ( ISBLANK ( 'MPK'[Data zamknięcia] ), 'MPK'[Data zamknięcia] > _do ) )\n    )\n")
    add(SD, "Sprzedaż LFL",
        lfl_vars + "RETURN\n    CALCULATE ( [Sprzedaż netto (dane dzienne)], _sklepy, "
        "KEEPFILTERS ( 'Data'[Data] <= _do ) )",
        KWOTA, fo,
        "Sprzedaż sklepów porównywalnych (LFL): sklepy, których data LFL od jest nie późniejsza niż początek "
        "okresu i które nie zostały zamknięte przed końcem okresu.")
    add(SD, "Sprzedaż LFL rok wcześniej",
        lfl_vars + "RETURN\n    CALCULATE (\n        [Sprzedaż netto (dane dzienne)],\n        _sklepy,\n"
        "        DATEADD ( FILTER ( VALUES ( 'Data'[Data] ), 'Data'[Data] <= _do ), -1, YEAR )\n    )",
        KWOTA, fo, "Sprzedaż tych samych sklepów porównywalnych (LFL) w analogicznym okresie rok wcześniej.")
    add(SD, "Dynamika LFL r/r %",
        "VAR _ly = [Sprzedaż LFL rok wcześniej]\nRETURN\n    DIVIDE ( [Sprzedaż LFL] - _ly, _ly )", PROC, fo,
        "Dynamika sprzedaży porównywalnej (LFL) rok do roku w procentach.")
    add(SD, "Udział e-commerce %",
        "DIVIDE (\n    CALCULATE ( [Sprzedaż netto (dane dzienne)], KEEPFILTERS ( 'MPK'[Typ MPK] = \"E-commerce\" ) ),\n"
        "    CALCULATE ( [Sprzedaż netto (dane dzienne)], REMOVEFILTERS ( 'MPK'[Typ MPK] ), "
        "REMOVEFILTERS ( 'MPK'[Kanał] ) )\n)",
        PROC, fo, "Udział kanału e-commerce w sprzedaży netto (sklepy plus e-commerce) według danych dziennych.")
    add(SD, "Liczba sklepów ze sprzedażą",
        "CALCULATE ( DISTINCTCOUNT ( 'Sprzedaż dzienna'[mpk_id] ), KEEPFILTERS ( 'MPK'[Typ MPK] = \"Sklep\" ) )",
        "#,0", fo, "Liczba sklepów, które miały sprzedaż w wybranym okresie.")

    fo = "Sprzedaż według kategorii"
    add(SK, "Sprzedaż netto (kategorie)", "SUM ( 'Sprzedaż według kategorii'[sprzedaz_netto_pln] )", KWOTA, fo,
        "Sprzedaż netto w PLN według kategorii towarowych, miesiące zamknięte.")
    add(SK, "Sprzedaż netto (kategorie) rok wcześniej",
        "CALCULATE ( [Sprzedaż netto (kategorie)], DATEADD ( 'Data'[Data], -1, YEAR ) )", KWOTA, fo,
        "Sprzedaż netto według kategorii w analogicznym okresie rok wcześniej.")
    add(SK, "Dynamika sprzedaży (kategorie) r/r %",
        "VAR _ly = [Sprzedaż netto (kategorie) rok wcześniej]\nRETURN\n"
        "    DIVIDE ( [Sprzedaż netto (kategorie)] - _ly, _ly )",
        PROC, fo, "Zmiana sprzedaży kategorii rok do roku w procentach.")
    add(SK, "Udział kategorii %",
        "DIVIDE ( [Sprzedaż netto (kategorie)], CALCULATE ( [Sprzedaż netto (kategorie)], "
        "REMOVEFILTERS ( 'Kategoria' ) ) )",
        PROC, fo, "Udział kategorii w sprzedaży wszystkich kategorii w tym samym kontekście.")
    add(SK, "Marża brutto % (kategorie)",
        "DIVIDE ( [Sprzedaż netto (kategorie)] - SUM ( 'Sprzedaż według kategorii'[koszt_wlasny_pln] ), "
        "[Sprzedaż netto (kategorie)] )",
        PROC, fo, "Marża brutto procentowa według kategorii.")
    add(SK, "Liczba sztuk (kategorie)", "SUM ( 'Sprzedaż według kategorii'[liczba_sztuk] )", "#,0", fo,
        "Liczba sprzedanych sztuk według kategorii.")

    add("MPK", "Liczba sklepów",
        "CALCULATE ( COUNTROWS ( 'MPK' ), KEEPFILTERS ( 'MPK'[Typ MPK] = \"Sklep\" ) )", "#,0",
        "Słownik", "Liczba sklepów w słowniku MPK. Filtruj kolumną Status, aby policzyć np. tylko aktywne.")
    add("Kursy walut", "Średni kurs PLN", "AVERAGE ( 'Kursy walut'[kurs_sredni_pln] )", "0.0000", "Kursy",
        "Średni kurs waluty w PLN za jednostkę.")
    return m


def desc_block(text: str, indent: str) -> list[str]:
    return [f"{indent}/// {line}" for line in text.strip().splitlines()] if text else []


def write_model(model: str, curated: bool, source: dict | None = None, spec_all: dict | None = None,
                rels: list | None = None, tables: list | None = None, meas: list | None = None,
                copilot: bool = False) -> dict:
    source = source or SOURCE
    spec_all = spec_all or CURATED
    rels = RELATIONSHIPS if rels is None else rels
    tables = tables or MODEL_TABLES
    if meas is None:
        meas = measures() if curated else []
    out = ROOT / model
    if out.exists():
        shutil.rmtree(out)
    (out / "definition" / "tables").mkdir(parents=True)
    (out / "definition" / "cultures").mkdir(parents=True)
    # Wersja 4.2 wystarcza dla TMDL, ale Fabric REST API po cichu odrzuca wtedy folder Copilot
    # (sprawdzone przez getDefinition). Przy 6.0 folder jest zachowywany.
    (out / "definition.pbism").write_text(
        '{\n  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/'
        'definitionProperties/1.0.0/schema.json",\n  "version": "6.0",\n  "settings": {\n    "qnaEnabled": true\n  }\n}\n',
        encoding="utf-8")
    (out / "definition" / "database.tmdl").write_text("database\n\tcompatibilityLevel: 1604\n\n", encoding="utf-8")
    (out / "definition" / "cultures" / "pl-PL.tmdl").write_text("cultureInfo pl-PL\n\n", encoding="utf-8")
    (out / "definition" / "expressions.tmdl").write_text(
        "expression DatabaseQuery =\n\t\tlet\n\t\t    database = Sql.Database(\"{{SQL_ENDPOINT}}\", \"{{SQL_ENDPOINT_ID}}\")\n"
        "\t\tin\n\t\t    database\n\tlineageTag: " + tag(model, "expr") + "\n\n", encoding="utf-8")

    names: dict[str, str] = {}
    colnames: dict[tuple[str, str], str] = {}
    for src in tables:
        spec = spec_all[src] if curated else None
        tname = spec["name"] if curated else src
        names[src] = tname
        types = dict(source[src])
        lines: list[str] = []
        if curated:
            lines += desc_block(spec["desc"], "")
        lines.append(f"table {q(tname)}")
        lines.append(f"\tlineageTag: {tag(model, src)}")
        if curated and spec.get("time"):
            lines.append("\tdataCategory: Time")
        lines.append("")
        for t, n, dax, fmt, folder, opis in meas:
            if t != tname:
                continue
            lines += desc_block(opis, "\t")
            if "\n" in dax:
                lines.append(f"\tmeasure {q(n)} =")
                lines += [f"\t\t\t{x}" if x.strip() else "" for x in dax.splitlines()]
            else:
                lines.append(f"\tmeasure {q(n)} = {dax}")
            lines.append(f"\t\tformatString: {fmt}")
            lines.append(f"\t\tdisplayFolder: {folder}")
            lines.append(f"\t\tlineageTag: {tag(model, 'm', n)}")
            lines.append("")
        cols = spec["cols"] if curated else [(c, c, "", {}) for c, _ in source[src]]
        if curated:
            assert [c[0] for c in cols] == [c for c, _ in source[src]], f"kolumny {src} niezgodne ze źródłem"
        for scol, cname, opis, opt in cols:
            dtype = types[scol]
            colnames[(src, scol)] = cname
            if curated:
                lines += desc_block(opis, "\t")
            lines.append(f"\tcolumn {q(cname)}")
            lines.append(f"\t\tdataType: {dtype}")
            if opt.get("key"):
                lines.append("\t\tisKey")
            if opt.get("hidden"):
                lines.append("\t\tisHidden")
            if opt.get("fmt"):
                lines.append(f"\t\tformatString: {opt['fmt']}")
            elif dtype == "dateTime":
                lines.append(f"\t\tformatString: {DATA_FMT}")
            numeric = dtype in ("int64", "double")
            summ = ("sum" if opt.get("sum") else "none") if curated else ("sum" if numeric else "none")
            lines.append(f"\t\tlineageTag: {tag(model, src, scol)}")
            lines.append(f"\t\tsummarizeBy: {summ}")
            lines.append(f"\t\tsourceColumn: {scol}")
            if opt.get("sort"):
                lines.append(f"\t\tsortByColumn: {q(opt['sort'])}")
            lines.append("")
            lines.append("\t\tannotation SummarizationSetBy = Automatic")
            lines.append("")
        lines.append(f"\tpartition {q(tname)} = entity")
        lines.append("\t\tmode: directLake")
        lines.append("\t\tsource")
        lines.append(f"\t\t\tentityName: {src}")
        lines.append("\t\t\tschemaName: dbo")
        lines.append("\t\t\texpressionSource: DatabaseQuery")
        lines.append("")
        (out / "definition" / "tables" / f"{tname}.tmdl").write_text("\n".join(lines) + "\n", encoding="utf-8")

    rel_lines: list[str] = []
    for ft, fc, tt, tc in rels:
        rel_lines.append(f"relationship {tag(model, 'rel', ft, fc, tt, tc)}")
        rel_lines.append(f"\tfromColumn: {q(names[ft])}.{q(colnames[(ft, fc)])}")
        rel_lines.append(f"\ttoColumn: {q(names[tt])}.{q(colnames[(tt, tc)])}")
        rel_lines.append("")
    (out / "definition" / "relationships.tmdl").write_text("\n".join(rel_lines) + "\n", encoding="utf-8")

    model_lines = ["model Model", "\tculture: pl-PL", "\tdefaultPowerBIDataSourceVersion: powerBI_V3"]
    if curated:
        model_lines.append("\tdiscourageImplicitMeasures")
    model_lines += ["\tsourceQueryCulture: pl-PL", "", "annotation __PBI_TimeIntelligenceEnabled = 0", ""]
    model_lines += [f"ref table {q(names[s])}" for s in tables]
    model_lines += ["", "ref cultureInfo pl-PL", ""]
    (out / "definition" / "model.tmdl").write_text("\n".join(model_lines) + "\n", encoding="utf-8")
    if copilot:
        write_copilot(model, out, tables, names, colnames, spec_all, meas)
    print(f"{model}: {len(tables)} tabel, {len(meas)} miar, {len(rels)} relacji"
          + (", folder Copilot (Prep data for AI)" if copilot else ""))
    return {"tables": [names[s] for s in tables], "measures": [x[1] for x in meas]}


# ---------------------------------------------------------------- Prep data for AI (folder Copilot)
# Format plików: https://github.com/microsoft/json-schemas/tree/main/fabric/item/semanticModel/copilot
# Instrukcje AI są po angielsku, bo agent danych Fabric oficjalnie obsługuje tylko język angielski.

AI_HIDDEN_TABLES = {"Kursy walut"}
AI_HIDDEN_COLUMNS = {("Data", "Miesiąc skrót")}
AI_HIDDEN_MEASURES = {"Kwota (jeden scenariusz)", "Średni kurs PLN"}

AI_TABLE_SYNONYMS = {
    "Data": ["kalendarz", "calendar", "date", "okres"],
    "Marka": ["brand", "marki"],
    "Kraj": ["country", "rynek", "market"],
    "Kategoria": ["category", "kategoria towarowa", "grupa towarowa"],
    "Scenariusz": ["scenario", "wersja danych"],
    "Konto": ["account", "pozycja P&L", "konto księgowe"],
    "MPK": ["cost center", "miejsce powstawania kosztów", "sklep", "store", "centrum kosztów"],
    "Rachunek wyników": ["P&L", "RZiS", "rachunek zysków i strat", "profit and loss", "wynik finansowy"],
    "Sprzedaż dzienna": ["daily sales", "sprzedaż bieżąca", "paragony", "transakcje"],
    "Sprzedaż według kategorii": ["category sales", "sprzedaż kategorii", "sprzedaż asortymentu"],
}
AI_COLUMN_SYNONYMS = {
    ("Data", "Rok finansowy"): ["fiscal year", "RF", "rok obrotowy", "FY"],
    ("Data", "Kwartał finansowy pełny"): ["fiscal quarter", "kwartał"],
    ("Data", "Kwartał finansowy"): ["quarter"],
    ("Data", "Półrocze finansowe"): ["half year", "półrocze", "H1", "H2"],
    ("Data", "Miesiąc"): ["month", "nazwa miesiąca"],
    ("Data", "Rok kalendarzowy"): ["calendar year"],
    ("Data", "Black Friday"): ["czarny piątek"],
    ("Data", "Miesiąc zamknięty"): ["closed month", "zamknięcie miesiąca"],
    ("Marka", "Marka"): ["brand name", "nazwa marki"],
    ("Kraj", "Kraj"): ["country name", "nazwa kraju"],
    ("Kategoria", "Kategoria"): ["category name", "nazwa kategorii"],
    ("Konto", "Konto"): ["account name", "pozycja kosztowa", "rodzaj kosztu"],
    ("Konto", "Numer konta"): ["account number", "konto nr"],
    ("Konto", "Grupa kosztów"): ["cost group"],
    ("MPK", "Nazwa MPK"): ["store name", "nazwa sklepu"],
    ("MPK", "Kod MPK"): ["store code", "kod sklepu"],
    ("MPK", "Typ MPK"): ["cost center type", "typ lokalizacji"],
    ("MPK", "Kanał"): ["channel", "kanał sprzedaży"],
    ("MPK", "Data otwarcia planowana"): ["planned opening date", "planowane otwarcie"],
    ("MPK", "Data otwarcia"): ["opening date", "otwarcie sklepu"],
    ("MPK", "Status"): ["store status", "status sklepu"],
    ("MPK", "LFL od"): ["LFL start", "like for like od"],
    ("Sprzedaż według kategorii", "Kanał sprzedaży"): ["channel", "kanał"],
}
AI_MEASURE_SYNONYMS = {
    "Sprzedaż netto ACT": ["sprzedaż", "przychody", "obroty", "net sales", "revenue", "wykonanie sprzedaży"],
    "Sprzedaż netto BUD": ["budżet sprzedaży", "sales budget", "planowana sprzedaż"],
    "Sprzedaż netto FC": ["prognoza sprzedaży", "sales forecast", "forecast 8+4"],
    "Marża brutto ACT": ["gross margin", "marża"],
    "Marża brutto % ACT": ["gross margin %", "GM%", "marża procentowa", "rentowność brutto"],
    "Koszty operacyjne ACT": ["opex", "koszty działalności"],
    "EBITDA ACT": ["EBITDA", "wynik EBITDA"],
    "EBITDA FC": ["prognoza EBITDA", "EBITDA forecast"],
    "EBIT ACT": ["EBIT", "wynik operacyjny", "operating profit"],
    "Kwota ACT": ["koszt", "kwota", "wartość konta", "actual amount"],
    "Odchylenie sprzedaży ACT vs BUD": ["sales variance", "odchylenie od budżetu", "różnica do budżetu"],
    "Odchylenie sprzedaży ACT vs BUD %": ["sales variance %", "odchylenie procentowe sprzedaży"],
    "Odchylenie kwoty ACT vs BUD": ["cost variance", "przekroczenie budżetu", "odchylenie kosztów"],
    "Odchylenie EBITDA FC vs BUD": ["EBITDA forecast variance"],
    "Dynamika sprzedaży ACT r/r %": ["sales growth", "wzrost sprzedaży", "dynamika r/r", "YoY"],
    "Sprzedaż netto (dane dzienne)": ["daily sales", "sprzedaż dzienna", "sprzedaż bieżąca"],
    "Liczba paragonów": ["receipts", "transactions", "transakcje", "liczba transakcji"],
    "Liczba zamówień e-commerce": ["online orders", "zamówienia", "zamówienia internetowe"],
    "Średnia wartość paragonu": ["average basket", "ATV", "średni koszyk", "średni paragon"],
    "Sztuki na paragon": ["UPT", "units per transaction"],
    "Sprzedaż LFL": ["like-for-like sales", "sprzedaż porównywalna", "LFL"],
    "Dynamika LFL r/r %": ["LFL growth", "dynamika LFL", "LFL r/r"],
    "Udział e-commerce %": ["e-commerce share", "udział online", "penetracja e-commerce"],
    "Sprzedaż netto (kategorie)": ["category sales", "sprzedaż kategorii"],
    "Udział kategorii %": ["category share", "udział w sprzedaży"],
    "Koszt logistyki e-commerce na zamówienie ACT": ["cost per order", "koszt na zamówienie",
                                                     "koszt dostawy na zamówienie"],
    "Liczba sklepów": ["store count", "liczba lokalizacji"],
}
AI_EXAMPLE_PROMPTS = [
    "Jaka była sprzedaż netto grupy w 2Q 2026/27 i jak wypadła względem budżetu?",
    "Która marka ma największe odchylenie sprzedaży od budżetu narastająco w 2026/27?",
    "Dlaczego Vento w Niemczech jest poniżej budżetu w 1H 2026/27?",
    "Które 5 sklepów ma największe przekroczenie budżetu czynszów w 2026/27?",
    "Jaka jest prognoza EBITDA grupy na 2026/27 i jak wypada względem budżetu?",
]
COPILOT_SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/copilot"
# Format jak w microsoft/fabric-data-agent-workshop (ManufacturingOpsAIReady.SemanticModel/Copilot)
VERSION_JSON = {"$schema": "https://developer.microsoft.com/json-schemas/fabric/item/version/1.0.0/schema.json",
                "version": "1.0.0"}


def write_copilot(model: str, out: Path, tables: list, names: dict, colnames: dict, spec_all: dict,
                  meas: list) -> None:
    cop = out / "Copilot"
    (cop / "Instructions").mkdir(parents=True)
    instr = (ROOT / "prep_for_ai" / f"{model}_instructions.md").read_text(encoding="utf-8").strip()
    assert len(instr) <= 10000, f"instrukcje AI {model} mają {len(instr)} znaków, limit to 10 000"
    (cop / "Instructions" / "instructions.md").write_text(instr + "\n", encoding="utf-8")
    known_cols = {(names[s], c) for (s, _), c in colnames.items()}
    known_meas = {m[1] for m in meas}
    for (t, c) in list(AI_COLUMN_SYNONYMS) + list(AI_HIDDEN_COLUMNS):
        assert (t, c) in known_cols, f"Copilot: brak kolumny {t}[{c}]"
    for n in list(AI_MEASURE_SYNONYMS) + list(AI_HIDDEN_MEASURES):
        assert n in known_meas, f"Copilot: brak miary [{n}]"
    out_tables = []
    for src in tables:
        tname = names[src]
        spec = spec_all[src]
        hidden_table = tname in AI_HIDDEN_TABLES
        cols = []
        for scol, cname, _opis, opt in spec["cols"]:
            hidden = hidden_table or opt.get("hidden") or (tname, cname) in AI_HIDDEN_COLUMNS
            cols.append({"id": tag(model, src, scol), "name": cname,
                         "visibility": "Hidden" if hidden else "Visible",
                         "synonyms": AI_COLUMN_SYNONYMS.get((tname, cname), [])})
        ms = [{"id": tag(model, "m", n), "name": n,
               "visibility": "Hidden" if hidden_table or n in AI_HIDDEN_MEASURES else "Visible",
               "synonyms": AI_MEASURE_SYNONYMS.get(n, [])}
              for t, n, *_ in meas if t == tname]
        out_tables.append({"id": tag(model, src), "name": tname, "visibility": "Hidden" if hidden_table else "Visible",
                           "synonyms": AI_TABLE_SYNONYMS.get(tname, []), "columns": cols, "measures": ms,
                           "hierarchies": []})
    files = {
        "schema.json": {"$schema": f"{COPILOT_SCHEMA}/schema/1.0.0/schema.json", "tables": out_tables},
        "settings.json": {"$schema": f"{COPILOT_SCHEMA}/settings/1.0.0/schema.json", "indexingEnabled": True},
        "examplePrompts.json": {"$schema": f"{COPILOT_SCHEMA}/examplePrompts/1.0.0/schema.json",
                                "prompts": AI_EXAMPLE_PROMPTS},
        "version.json": VERSION_JSON,
        "Instructions/version.json": VERSION_JSON,
    }
    for fname, obj in files.items():
        (cop / fname).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- SM_Planowanie (Fabric IQ Plan)
# Learn: "If the semantic model contains unsupported Unicode characters, inserting a Data input column in a
# planning sheet might fail." Dlatego nazwy, opisy i wartości tekstowe tego modelu są wyłącznie w ASCII.

PLAN_SOURCE: dict[str, list[tuple[str, str]]] = {
    "plan_kalendarz": [
        ("miesiac", "dateTime"), ("rok_finansowy", "string"), ("rok_finansowy_nr", "int64"), ("kwartal", "string"),
        ("kwartal_pelny", "string"), ("kwartal_sort", "int64"), ("miesiac_fin_nr", "int64"),
        ("miesiac_nazwa", "string"), ("okres", "string"), ("rok", "int64"), ("miesiac_nr", "int64"),
        ("czy_miesiac_zamkniety", "boolean"),
    ],
    "dim_marka": [("marka_kod", "string"), ("marka_nazwa", "string"), ("kolejnosc", "int64")],
    "dim_kraj": [("kraj_kod", "string"), ("waluta_lokalna", "string")],
    "agg_sprzedaz_mies": [("miesiac", "dateTime"), ("marka_kod", "string"), ("kraj_kod", "string"),
                          ("kanal", "string"), ("scenariusz_kod", "string"), ("sprzedaz_netto_pln", "double"),
                          ("koszt_wlasny_pln", "double")],
}
PLAN_TABLES = ["plan_kalendarz", "dim_marka", "dim_kraj", "agg_sprzedaz_mies"]
PLAN_SPEC: dict[str, dict] = {
    "plan_kalendarz": {
        "name": "Kalendarz",
        "desc": "Monthly fiscal calendar, April 2023 to March 2028. Fiscal year runs April to March.",
        "cols": [
            ("miesiac", "Data miesiaca", "First day of the month, key.", {"key": True, "fmt": DATA_FMT}),
            ("rok_finansowy", "Rok finansowy", "Fiscal year, for example 2026/27.", {"sort": "Rok finansowy nr"}),
            ("rok_finansowy_nr", "Rok finansowy nr", "Calendar year in which the fiscal year starts.",
             {"hidden": True}),
            ("kwartal", "Kwartal", "Fiscal quarter 1Q to 4Q (1Q = Apr to Jun).", {}),
            ("kwartal_pelny", "Kwartal pelny", "Fiscal quarter with year, for example 3Q 2026/27.",
             {"sort": "Kwartal sort"}),
            ("kwartal_sort", "Kwartal sort", "Sort key.", {"hidden": True}),
            ("miesiac_fin_nr", "Miesiac fin nr", "Month number in the fiscal year, 1 = April.", {"hidden": True}),
            ("miesiac_nazwa", "Miesiac", "Month short name without diacritics, sorted from April.",
             {"sort": "Miesiac fin nr"}),
            ("okres", "Okres", "Calendar period YYYY-MM.", {}),
            ("rok", "Rok kalendarzowy", "Calendar year.", {}),
            ("miesiac_nr", "Miesiac kalendarzowy nr", "Calendar month number, 1 = January.", {}),
            ("czy_miesiac_zamkniety", "Miesiac zamkniety", "True for closed months (up to November 2026).", {}),
        ],
    },
    "dim_marka": {
        "name": "Marka",
        "desc": "Brands. GRP is headquarters and has no sales.",
        "cols": [
            ("marka_kod", "Kod marki", "Brand code: AUR, VEN, LUM, KRO.", {}),
            ("marka_nazwa", "Marka", "Brand name.", {"sort": "Kolejnosc marki"}),
            ("kolejnosc", "Kolejnosc marki", "Display order.", {"hidden": True}),
        ],
    },
    "dim_kraj": {
        "name": "Kraj",
        "desc": "Countries, shown as ISO codes.",
        "cols": [
            ("kraj_kod", "Kraj", "Country code, for example PL, DE, SE.", {}),
            ("waluta_lokalna", "Waluta", "Local currency. All amounts in this model are in PLN.", {}),
        ],
    },
    "agg_sprzedaz_mies": {
        "name": "Sprzedaz",
        "desc": ("Monthly net sales and cost of goods sold by brand, country, channel and scenario (ACT, BUD, FC), "
                 "in PLN. Source for planning sheets."),
        "cols": [
            ("miesiac", "miesiac", "Month key.", {"hidden": True, "fmt": DATA_FMT}),
            ("marka_kod", "marka_kod", "Brand key.", {"hidden": True}),
            ("kraj_kod", "kraj_kod", "Country key.", {"hidden": True}),
            ("kanal", "Kanal", "Channel: Sklep (stores) or E-commerce.", {}),
            ("scenariusz_kod", "Scenariusz", "ACT actuals, BUD budget, FC forecast 8+4.", {}),
            ("sprzedaz_netto_pln", "sprzedaz_netto_pln", "Net sales PLN.", {"hidden": True, "fmt": KWOTA}),
            ("koszt_wlasny_pln", "koszt_wlasny_pln", "Cost of goods sold PLN.", {"hidden": True, "fmt": KWOTA}),
        ],
    },
}
PLAN_RELATIONSHIPS = [
    ("agg_sprzedaz_mies", "miesiac", "plan_kalendarz", "miesiac"),
    ("agg_sprzedaz_mies", "marka_kod", "dim_marka", "marka_kod"),
    ("agg_sprzedaz_mies", "kraj_kod", "dim_kraj", "kraj_kod"),
]


def plan_measures() -> list[tuple[str, str, str, str, str, str]]:
    t = "Sprzedaz"
    sales = "SUM ( 'Sprzedaz'[sprzedaz_netto_pln] )"
    m = []
    for s, opis in (("ACT", "actuals, closed months only"), ("BUD", "budget"), ("FC", "forecast 8+4 for 2026/27")):
        m.append((t, f"Sprzedaz {s}", f"CALCULATE ( {sales}, KEEPFILTERS ( 'Sprzedaz'[Scenariusz] = \"{s}\" ) )",
                  KWOTA, "1. Scenariusze", f"Net sales PLN, {opis}."))
    m.append((t, "Marza brutto ACT",
              "CALCULATE ( SUM ( 'Sprzedaz'[sprzedaz_netto_pln] ) - SUM ( 'Sprzedaz'[koszt_wlasny_pln] ), "
              "KEEPFILTERS ( 'Sprzedaz'[Scenariusz] = \"ACT\" ) )", KWOTA, "1. Scenariusze",
              "Gross margin PLN, actuals."))
    m.append((t, "Marza brutto % ACT", "DIVIDE ( [Marza brutto ACT], [Sprzedaz ACT] )", PROC, "1. Scenariusze",
              "Gross margin as a share of net sales, actuals."))
    rok = ("REMOVEFILTERS ( 'Kalendarz'[Rok finansowy], 'Kalendarz'[Rok finansowy nr], 'Kalendarz'[Kwartal pelny], "
           "'Kalendarz'[Kwartal sort], 'Kalendarz'[Data miesiaca], 'Kalendarz'[Okres], 'Kalendarz'[Rok kalendarzowy], "
           "'Kalendarz'[Miesiac zamkniety] )")
    for nazwa, baza, rf in (("Sprzedaz ACT 2024/25", "Sprzedaz ACT", "2024/25"),
                            ("Sprzedaz ACT 2025/26", "Sprzedaz ACT", "2025/26"),
                            ("Sprzedaz BUD 2026/27", "Sprzedaz BUD", "2026/27"),
                            ("Sprzedaz FC 2026/27", "Sprzedaz FC", "2026/27")):
        m.append((t, nazwa, f"CALCULATE ( [{baza}], {rok}, 'Kalendarz'[Rok finansowy] = \"{rf}\" )", KWOTA,
                  "2. Bazy do planu",
                  f"{baza} for fiscal year {rf} regardless of the year in context. Month and quarter of the fiscal "
                  f"year (Miesiac, Kwartal) still apply, so the measure can seed a plan for another year."))
    return m


def assert_ascii(model: str) -> None:
    for f in (ROOT / model).rglob("*"):
        if f.is_file():
            txt = f.read_text(encoding="utf-8")
            bad = sorted({ch for ch in txt if ord(ch) > 127})
            assert not bad, f"{f.relative_to(ROOT)} zawiera znaki spoza ASCII: {bad}"


if __name__ == "__main__":
    write_model("SM_Kontroling", curated=True, copilot=True)
    write_model("SM_Kontroling_surowy", curated=False)
    write_model("SM_Planowanie", curated=True, source=PLAN_SOURCE, spec_all=PLAN_SPEC, rels=PLAN_RELATIONSHIPS,
                tables=PLAN_TABLES, meas=plan_measures())
    assert_ascii("SM_Planowanie")
