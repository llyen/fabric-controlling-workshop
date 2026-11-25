"""Eksport tabel, plików wejściowych Excel i słownika danych."""

from datetime import datetime
from io import BytesIO
import math
import os
import tempfile
from xml.etree import ElementTree
from zipfile import ZipFile

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

import config as cfg
from kalendarz import fiscal_year
from odpowiedzi import md_table, number, pct, pln
from schemat import DESCRIPTIONS, GRAINS, RELATIONSHIPS, SCHEMAS, arrow_schema

DISCLAIMER = ("Dane w pełni syntetyczne, wymyślone na potrzeby warsztatu. "
              "Nie odzwierciedlają wyników żadnej firmy. Skala jest umowna.")
INTEGER_FORMAT = "#,##0"
MONEY_FORMAT = "#,##0.00"
PERCENT_FORMAT = "0.0%"


def write_tables(tables):
    parquet_dir, csv_dir = cfg.DATA_DIR / "parquet", cfg.DATA_DIR / "csv"
    parquet_dir.mkdir(parents=True, exist_ok=True)
    csv_dir.mkdir(parents=True, exist_ok=True)
    for name, frame in tables.items():
        table = pa.Table.from_pandas(frame, schema=arrow_schema(name), preserve_index=False, safe=True)
        pq.write_table(table, parquet_dir / f"{name}.parquet", compression="snappy",
                       row_group_size=65536, write_statistics=True)
        kwargs = {"index": False, "encoding": "utf-8-sig", "lineterminator": "\n", "date_format": "%Y-%m-%d"}
        if name == "fakt_sprzedaz_dzienna":
            frame.to_csv(csv_dir / f"{name}.csv.gz", float_format="%.2f",
                         compression={"method": "gzip", "compresslevel": 6, "mtime": 0}, **kwargs)
        elif name == "ref_plan_2027_28_rozklad":
            csv_frame = frame.copy()
            for column in csv_frame.columns:
                if column.endswith("_pln"):
                    csv_frame[column] = csv_frame[column].map(lambda value: f"{value:.2f}")
            csv_frame.to_csv(csv_dir / f"{name}.csv", **kwargs)
        else:
            frame.to_csv(csv_dir / f"{name}.csv", float_format="%.6f" if name == "fakt_kursy_walut" else "%.2f",
                         **kwargs)


def sheet(wb, title, frame, formats=None):
    ws = wb.create_sheet(title)
    ws.append(list(frame.columns))
    for row in frame.itertuples(index=False, name=None):
        ws.append([None if pd.isna(value) else value.item() if isinstance(value, np.generic)
                   else value.to_pydatetime() if isinstance(value, pd.Timestamp) else value for value in row])
    for cell in ws[1]:
        cell.font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="17365D")
        cell.alignment = Alignment(vertical="center", wrap_text=True)
    ws.row_dimensions[1].height = 44
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    formats = formats or {}
    for index, name in enumerate(frame.columns, start=1):
        letter = get_column_letter(index)
        sample = [str(name)] + [str(value) for value in frame[name].head(80) if pd.notna(value)]
        ws.column_dimensions[letter].width = min(48, max(16, max(map(len, sample)) + 2))
        if name in formats:
            for cells in ws.iter_rows(min_row=2, min_col=index, max_col=index):
                cells[0].number_format = formats[name]
        for cells in ws.iter_rows(min_row=2, min_col=index, max_col=index):
            cells[0].alignment = Alignment(vertical="top", wrap_text=isinstance(cells[0].value, str))
    for row in ws.iter_rows(min_row=2):
        lines = max(math.ceil(len(str(cell.value or "")) / max(ws.column_dimensions[cell.column_letter].width - 2, 1))
                    if isinstance(cell.value, str) else 1 for cell in row)
        ws.row_dimensions[row[0].row].height = max(16, 15 * lines)
    ws.sheet_view.showGridLines = False
    return ws


def workbook():
    wb = Workbook()
    wb.remove(wb.active)
    wb.properties.creator = "Generator danych syntetycznych"
    wb.properties.title = "Warsztat Fabric, finanse i kontroling"
    wb.properties.subject = DISCLAIMER
    stamp = datetime.fromisoformat(cfg.AS_OF).replace(hour=12)
    wb.properties.created = stamp
    wb.properties.modified = stamp
    return wb


def workbook_content(payload):
    with ZipFile(BytesIO(payload)) as archive:
        parts = {name: archive.read(name) for name in archive.namelist()}
    core = ElementTree.fromstring(parts["docProps/core.xml"])
    modified = core.find("{http://purl.org/dc/terms/}modified")
    if modified is not None:
        modified.text = ""
    parts["docProps/core.xml"] = ElementTree.tostring(core)
    return parts


def save_workbook(wb, path):
    # openpyxl zapisuje pośrednie XML; kierujemy je wyłącznie do katalogu projektu.
    scratch = cfg.ROOT / "generator" / f"_xlsx_work_{os.getpid()}"
    scratch.mkdir(exist_ok=False)
    prior_tempdir = tempfile.tempdir
    tempfile.tempdir = str(scratch)
    output = BytesIO()
    try:
        wb.save(output)
    finally:
        tempfile.tempdir = prior_tempdir
        for file in scratch.iterdir():
            file.unlink()
        scratch.rmdir()
    payload = output.getvalue()
    # Sam czas zapisania ZIP lub metadanych nie uzasadnia zmiany istniejącego pliku.
    if path.exists() and workbook_content(path.read_bytes()) == workbook_content(payload):
        return
    path.write_bytes(payload)


def write_import_workbook(budget, directory):
    draft = budget[["mpk_id", "mpk_nazwa", "konto_id", "konto_nazwa",
                    "act_2025_26_pln", "fc_2026_27_pln"]].copy()
    months = [f"m{index:02d}_{month:%Y_%m}" for index, month in enumerate(
        pd.date_range(cfg.PLAN_START, cfg.PLAN_END, freq="MS"), start=1)]
    indexation = np.where(draft["konto_id"].eq("5410"), cfg.IMPORT_WAGE_INDEX, cfg.IMPORT_OTHER_INDEX)
    monthly_base = np.round(draft["fc_2026_27_pln"] / 12. * (1. + indexation), -2)
    for month in months:
        draft[month] = monthly_base
    renewal = draft["mpk_id"].eq(cfg.IMPORT_IT_RENEWAL_MPK) & draft["konto_id"].eq("5420")
    draft.loc[renewal, cfg.IMPORT_IT_RENEWAL_MONTH] += cfg.IMPORT_IT_RENEWAL_PLN
    draft["komentarz"] = np.where(renewal, cfg.IMPORT_IT_RENEWAL_COMMENT, "")
    wb = workbook()
    ws = wb.create_sheet("Import")
    ws.append(list(draft.columns))
    for row in draft.itertuples(index=False, name=None):
        ws.append(list(row))
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for row in ws.iter_rows(min_row=2, min_col=5, max_col=18):
        for cell in row:
            cell.number_format = MONEY_FORMAT
    description = wb.create_sheet("Opis")
    description.append(["temat", "opis"])
    description.append(["Dane", DISCLAIMER])
    description.append([
        "Kolumny",
        "Klucz to mpk_id i konto_id. ACT i FC są rocznymi wartościami historycznymi. "
        "Kolumny m01 do m12 zawierają projekt od kwietnia 2027 do marca 2028; komentarz wyjaśnia korektę.",
    ])
    description.append([
        "Projekt",
        f"Każdy miesiąc: FC / 12 razy (1 + indeksacja), {pct(cfg.IMPORT_WAGE_INDEX)} dla konta 5410 "
        f"lub {pct(cfg.IMPORT_OTHER_INDEX)} dla pozostałych, zaokrąglone do 100 PLN. "
        f"Wyłącznie w wierszu {cfg.IMPORT_IT_RENEWAL_MPK}, konto 5420, październik zawiera dodatkowe "
        f"{pln(cfg.IMPORT_IT_RENEWAL_PLN)} na odnowienie licencji i komentarz. Pozostałe wiersze nie mają dopłaty. "
        "Są to zapisane wartości, bez formuł.",
    ])
    for cell in description[1]:
        cell.font = Font(bold=True)
    save_workbook(wb, directory / "budzet_opex_centrala_2027_28_import.xlsx")


def write_excel(tables, targets):
    directory = cfg.DATA_DIR / "excel"
    directory.mkdir(parents=True, exist_ok=True)
    target_frame = targets.rename(columns={"marka_kod": "marka", "kraj_kod": "kraj",
                                           "cel_roczny_pln": "cel_2027_28_pln"}).copy()
    target_frame = target_frame[["marka", "kraj", "kanal", "sprzedaz_fc_2026_27_pln",
                                 "wzrost_docelowy_pct", "cel_2027_28_pln"]]
    target_frame["sprzedaz_fc_2026_27_pln"] = target_frame["sprzedaz_fc_2026_27_pln"].round(2)
    growth_text = ", ".join(
        f"{brand} {pct(value)}" for brand, value in cfg.TARGET_GROWTH_2027.items()
    ) + f". E-commerce dodatkowo {number(cfg.TARGET_ECOM_EXTRA_PP * 100)} pp."
    wb = workbook()
    sheet(wb, "Cele", target_frame, {"sprzedaz_fc_2026_27_pln": INTEGER_FORMAT,
                                    "wzrost_docelowy_pct": PERCENT_FORMAT, "cel_2027_28_pln": INTEGER_FORMAT})
    sheet(wb, "Opis", pd.DataFrame({"Temat": ["Dane", "Ziarno", "Cel", "Wzrost", "Zadanie", "Miara roczna"],
                                   "Opis": [
                                       DISCLAIMER,
                                       "Jeden wiersz na markę, kraj i kanał; kody zgodne z wymiarami. Bez GRP.",
                                       "FC RF 2026/27 razy (1 + wzrost docelowy), zaokrąglone do tysiąca PLN.",
                                       growth_text,
                                       "Rozłóż cel na miesiące RF 2027/28 według udziałów ACT RF 2025/26 lub średnich udziałów z dwóch lat.",
                                       "Cel roczny nie jest sumą powtórzeń z tabeli miesięcznego rozkładu. Nie dodawaj scenariuszy do siebie.",
                                   ]}))
    save_workbook(wb, directory / "cele_sprzedazy_2027_28.xlsx")

    combinations = pd.MultiIndex.from_product(
        [[row[0] for row in cfg.BRANDS], [row[0] for row in cfg.COUNTRIES]],
        names=["marka", "kraj"]
    ).to_frame(index=False)
    assumptions = combinations.copy()
    assumptions["wzrost_lfl_pct"] = assumptions["marka"].map(cfg.BUD_STORE_GROWTH)
    assumptions["docelowa_marza_brutto_pct"] = assumptions["marka"].map(cfg.GROSS_MARGIN)
    assumptions["indeksacja_czynszow_pct"] = cfg.BUD_RENT_GROWTH
    assumptions["wzrost_plac_pct"] = cfg.WAGE_GROWTH
    new = tables["dim_mpk"].loc[tables["dim_mpk"]["status"].eq("Planowany"),
                                ["mpk_id", "marka_kod", "kraj_kod", "miasto", "powierzchnia_m2", "data_otwarcia_plan"]].copy()
    new = new.rename(columns={"marka_kod": "marka", "kraj_kod": "kraj", "powierzchnia_m2": "m2",
                               "data_otwarcia_plan": "planowany_miesiac_otwarcia"})
    new["planowany_miesiac_otwarcia"] = new["planowany_miesiac_otwarcia"].dt.to_period("M").dt.to_timestamp()
    wb = workbook()
    sheet(wb, "Zalozenia", assumptions, {name: PERCENT_FORMAT for name in assumptions.columns if name.endswith("_pct")})
    sheet(wb, "Nowe_sklepy", new, {"m2": INTEGER_FORMAT, "planowany_miesiac_otwarcia": "yyyy-mm"})
    sheet(wb, "Opis", pd.DataFrame({"Temat": ["Dane", "Jednostki", "Zakres", "Nowe sklepy", "Uwaga"],
                                   "Opis": [
                                       DISCLAIMER,
                                       "Procenty zapisano jako ułamki, np. 0,06 oznacza 6%.",
                                       "Założenia są roboczym wejściem na RF 2027/28, nie zatwierdzonym forecastem. LFL dotyczy sklepów.",
                                       f"{len(cfg.PLANNED_OPENINGS)} planowanych MPK nie ma sprzedaży ani kosztów w faktach. Daty są pierwszym dniem miesiąca.",
                                       "Wzrost LFL i wzrost celu rocznego to różne wielkości. Cel zawiera także zmianę sieci i miks kanałów.",
                                   ]}))
    save_workbook(wb, directory / "zalozenia_plan_2027_28.xlsx")

    pnl = tables["fakt_pnl"]
    hq = pnl.loc[pnl["mpk_id"].str.startswith("HQ-")].copy()
    hq["fy"] = fiscal_year(hq["miesiac"])
    act = hq.loc[hq["scenariusz_kod"].eq("ACT") & hq["fy"].eq(2025)].groupby(["mpk_id", "konto_id"])["kwota_pln"].sum()
    fc = hq.loc[hq["scenariusz_kod"].eq("FC") & hq["fy"].eq(2026)].groupby(["mpk_id", "konto_id"])["kwota_pln"].sum()
    budget = pd.concat([act.rename("act_2025_26_pln"), fc.rename("fc_2026_27_pln")], axis=1).reset_index()
    budget = budget.merge(tables["dim_mpk"][["mpk_id", "mpk_nazwa"]], on="mpk_id", validate="many_to_one")
    budget = budget.merge(tables["dim_konto"][["konto_id", "konto_nazwa"]], on="konto_id", validate="many_to_one")
    budget = budget[["mpk_id", "mpk_nazwa", "konto_id", "konto_nazwa", "act_2025_26_pln", "fc_2026_27_pln"]]
    budget[["act_2025_26_pln", "fc_2026_27_pln"]] = budget[["act_2025_26_pln", "fc_2026_27_pln"]].round(2)
    month_columns = [value.strftime("%Y-%m") for value in pd.date_range(cfg.PLAN_START, cfg.PLAN_END, freq="MS")]
    for name in month_columns:
        budget[name] = None
    budget["suma_pln"] = [f"=SUM(G{row}:R{row})" for row in range(2, len(budget) + 2)]
    budget["komentarz"] = None
    wb = workbook()
    ws = sheet(wb, "Budzet", budget,
               {name: INTEGER_FORMAT for name in ["act_2025_26_pln", "fc_2026_27_pln"] + month_columns + ["suma_pln"]})
    ws.column_dimensions["T"].width = 42
    for row in ws.iter_rows(min_row=2, min_col=7, max_col=18):
        for cell in row:
            cell.fill = PatternFill("solid", fgColor="FFF2CC")
    sheet(wb, "Instrukcja", pd.DataFrame({"Krok": ["Dane", "Historia", "Wprowadzenie", "Suma", "Kontrola"],
                                        "Opis": [
                                            DISCLAIMER,
                                            "ACT RF 2025/26 i FC RF 2026/27 są sumami kont centrali; nie wpisuj ich ponownie do miesięcy.",
                                            "Wypełnij 12 żółtych komórek w każdym wierszu kosztu i dodaj komentarz do istotnych zmian.",
                                            "Kolumna suma_pln zawiera formułę SUM. Excel obliczy ją po otwarciu; generator nie zapisuje wyniku w pamięci podręcznej formuły.",
                                            "Wiersze zawierają tylko konta rzeczywiście używane przez dane MPK. Nie dodawaj przychodów ani kont sklepów.",
                                        ]}))
    save_workbook(wb, directory / "budzet_opex_centrala_2027_28_szablon.xlsx")
    write_import_workbook(budget, directory)


def write_dictionary(tables, metrics):
    text = [
        "# Słownik danych syntetycznych\n",
        DISCLAIMER + "\n",
        "Zestaw służy do ćwiczeń Microsoft Fabric: analizy sprzedaży, odchyleń rachunku wyników, "
        "planowania i oceny odpowiedzi agenta. Firma i marki są fikcyjne, prawdziwe są tylko nazwy krajów i miast; "
        "liczby, MPK, otwarcia oraz historie biznesowe zostały wymyślone. "
        "Źródłem wartości są jawne reguły w generatorze, a nie dokumenty klienta.\n",
        "## Zakres i kalendarz finansowy\n",
        f"Data stanu to {cfg.AS_OF}. Sprzedaż dzienna obejmuje {cfg.DAILY_START} do {cfg.DAILY_END}. "
        "P&L ACT i kategorie obejmują zamknięte miesiące od kwietnia 2023 do listopada 2026. "
        "BUD obejmuje pełne RF 2024/25, 2025/26 i 2026/27. FC 8+4 dotyczy RF 2026/27. "
        "Kalendarz kończy się 31.03.2028.\n",
        "RF zaczyna się 1 kwietnia i kończy 31 marca. RF 2026/27 to 01.04.2026 do 31.03.2027; "
        "rok_finansowy_nr ma wtedy wartość 2026. Kwiecień jest miesiącem finansowym 1, marzec 12. "
        "1Q obejmuje kwiecień do czerwca, 2Q lipiec do września, 3Q październik do grudnia, "
        "4Q styczeń do marca. 1H to kwiecień do września, 2H październik do marca. "
        "kwartal_finansowy_sort = rok_finansowy_nr × 10 + numer kwartału, np. 20263.\n",
        "Polskie święta obejmują daty stałe oraz Wielkanoc, Poniedziałek Wielkanocny, "
        "Zielone Świątki i Boże Ciało. Od 2025 wolny jest także 24 grudnia. "
        "Uproszczone niedziele handlowe to ostatnia niedziela stycznia, kwietnia, czerwca i sierpnia, "
        "niedziela przed Wielkanocą oraz dwie niedziele przed 25 grudnia w latach 2023 i 2024, "
        "a od 2025 trzy niedziele przed 24 grudnia. Święto ma pierwszeństwo przed niedzielą handlową. "
        "Literalne uproszczenie oznacza handlowy 24.12.2023, z połową zwykłej wagi sprzedaży. "
        "Nie jest to kalendarz do celów prawnych. Poza Polską sklepy są zamknięte tylko "
        "1 stycznia, 25 grudnia i w Wielkanoc. E-commerce sprzedaje codziennie.\n",
        "## Konwencje i rachunek wyników\n",
        "Parquet używa date32, string, int64, float64 i bool. Wszystkie kwoty są w PLN, "
        "bez VAT, zaokrąglone do groszy. Kursy mają sześć miejsc dziesiętnych, a udziały planu "
        "zachowują precyzję float64. Puste daty i powierzchnie są nullami, nie tekstem. "
        "Puste miasto, format i dział oznaczają atrybut, który nie dotyczy danego MPK. "
        "Numer konta jest tekstem. Kwoty kont są dodatnie; znak pochodzi z dim_konto.\n",
        "Marża brutto = konto 4010 minus 4510. EBITDA = przychody minus koszt własny i wszystkie "
        "koszty operacyjne, bez konta 6010. EBIT = EBITDA minus amortyzacja. Tych sum nie ma jako "
        "dodatkowych wierszy faktu. Scenariuszy ACT, BUD i FC nie należy sumować ze sobą. "
        "Daty otwarcia i zamknięcia są włącznie: zamknięcie jest ostatnim dniem działalności.\n",
        "LFL zaczyna się po 12 pełnych miesiącach. Dla otwarcia pierwszego dnia miesiąca jest "
        "to pierwszy dzień tego samego miesiąca rok później. Dla otwarcia w trakcie miesiąca "
        "jest to pierwszy dzień następnego miesiąca rok później. Kohortę porównuje się w obu "
        "latach na tym samym zbiorze MPK. Null lfl_od oznacza MPK nieporównywalne.\n",
        "## Tabele\n",
        md_table(["Tabela", "Liczba wierszy", "Ziarno"],
                 [[name, number(len(tables[name])), " × ".join(GRAINS[name])] for name in SCHEMAS]) + "\n",
    ]
    for name, columns in SCHEMAS.items():
        text.extend([
            f"### {name}\n",
            DESCRIPTIONS[name] + "\n",
            f"Ziarno: {' × '.join(GRAINS[name])}. Liczba wierszy: {number(len(tables[name]))}.\n",
            md_table(["Kolumna", "Typ", "Opis"], [[col, kind, description] for col, kind, description in columns]) + "\n",
            "Relacje i klucze: " + RELATIONSHIPS[name] + "\n",
        ])
    pnl = tables["fakt_pnl"].merge(tables["dim_mpk"], on="mpk_id", validate="many_to_one")
    rents = pnl.loc[pnl["marka_kod"].eq(cfg.RENT_SHOCK_BRAND) & pnl["kraj_kod"].eq(cfg.RENT_SHOCK_COUNTRY)
                    & pnl["konto_id"].eq("5120") & pnl["miesiac"].between("2026-04-01", "2026-11-01")] \
        .groupby("scenariusz_kod")["kwota_pln"].sum()
    lum = pnl.loc[pnl["marka_kod"].eq(cfg.DECLINING_BRAND) & pnl["konto_id"].eq("4010") & pnl["typ_mpk"].eq("Sklep")
                  & pnl["scenariusz_kod"].eq("ACT") & pnl["miesiac"].dt.month.between(4, 11)] \
        .groupby(pnl["miesiac"].dt.year)["kwota_pln"].sum()
    log_act = sum(value["act"] for value in metrics["q8"])
    log_bud = sum(value["bud"] for value in metrics["q8"])
    text.extend([
        "## Historie do wykorzystania przez prowadzącego\n",
        md_table(["Historia", "Mechanizm", "Wynik w zestawie", "Oczekiwany przedział"],
                 [
                     ["Vento DE", "4 otwarcia przesunięte z maja i czerwca na sierpień i wrzesień 2026.",
                      "1H ACT/BUD: " + pct(metrics["q3"]["pct"], True), "Od -20% do -9%"],
                     ["Aurea AT", "Czynsze od kwietnia 2026 rosną o 15%; BUD zakłada 3%.",
                      pct(rents.ACT / rents.BUD - 1., True), "Od +9% do +14%"],
                     ["E-commerce DE", "Od października 2026 stawka za zamówienie w Niemczech wyższa o 18%.",
                      "Koszt października i listopada ACT/BUD: " + pct(log_act / log_bud - 1., True), "Od +15% do +30% w każdym miesiącu"],
                     ["Ciepły listopad", "Mnożnik sprzedaży od 0,92 do 0,99 zależnie od marki; mniejszy udział OW i marża niższa o 1 pp.",
                      "OW r/r: " + pct(metrics["q5"]["pct"], True), "Od -35% do -20%"],
                     ["Kroko", "Trend sklepów w RF 2025/26: -2%, w RF 2026/27: -7%; także cztery zamknięcia.",
                      "Sklepy, kwiecień do listopada r/r: " + pct(lum[2026] / lum[2025] - 1., True), "Od -18% do -9%"],
                     ["Black Friday 2025", "Sklepy razy 2, e-commerce razy 3; wsparcie tygodnia promocji.",
                      pln(metrics["q7"]["sales"]) + ", " + number(metrics["q7"]["multiple"], 2) + " razy pozostałe piątki",
                      "Najwyższy dzień grupy w listopadzie i e-commerce w RF 2025/26"],
                     ["Udział e-commerce", "Trend roczny 14%, dla Lumi 28%, baza RF 2023/24 skalibrowana do 18%.",
                      pct(metrics["q6"].loc[2023, "share"]) + " do " + pct(metrics["q6"].loc[2026, "share"]),
                      "Od 16% do 20% w RF 2023/24, od 21% do 26% w RF 2026/27"],
                     ["Grudzień", "Sezonowość, prezenty i ostatnie dwa tygodnie przed Wigilią.",
                      "Najwyższa miesięczna sprzedaż każdego pełnego RF", "RF 2023/24, 2024/25, 2025/26"],
                 ]) + "\n",
        "Wyniki powyżej są obliczone z tabel. Przyczyny są założeniami własnymi generatora, "
        "nie udokumentowanymi zdarzeniami żadnej firmy. Szczegółowy klucz zawiera 14 pytań "
        "w oczekiwane_odpowiedzi.md; sam wynik liczbowy nie zastępuje poprawnego filtra czasu i scenariusza.\n",
        "## Wejścia Excel\n",
        "cele_sprzedazy_2027_28.xlsx zawiera arkusze Cele i Opis. Cel roczny wynika z FC, wzrostu marki "
        f"i dodatkowych {number(cfg.TARGET_ECOM_EXTRA_PP * 100)} pp dla e-commerce, po zaokrągleniu do tysięcy. "
        f"zalozenia_plan_2027_28.xlsx zawiera {len(cfg.BRANDS) * len(cfg.COUNTRIES)} kombinacji marki i kraju oraz {len(cfg.PLANNED_OPENINGS)} planowanych sklepów. "
        "budzet_opex_centrala_2027_28_szablon.xlsx pokazuje wyłącznie konta używane przez centralę, "
        "sumy ACT i FC, 12 pustych miesięcy, formuły SUM oraz miejsce na komentarz. "
        "Procenty w Excelu są ułamkami. Puste miesiące nie są zerowym budżetem.\n",
        "budzet_opex_centrala_2027_28_import.xlsx jest oddzielnym wejściem do PowerTable. "
        "Pierwszy arkusz Import ma te same MPK i konta co szablon, jeden nagłówek w A1, "
        "19 kolumn i wyłącznie zapisane wartości, bez formuł i pustych wierszy. "
        "Nazwy kolumn to mpk_id, mpk_nazwa, konto_id, konto_nazwa, act_2025_26_pln, "
        "fc_2026_27_pln, m01_2027_04 do m12_2028_03 oraz komentarz; są ASCII i zaczynają się od litery. "
        "Polskie znaki w danych tekstowych pozostają dozwolone.\n",
        "Projekt miesięczny w pliku importowym = FC RF 2026/27 / 12 × (1 + indeksacja), "
        f"zaokrąglony do 100 PLN. Indeksacja wynosi {pct(cfg.IMPORT_WAGE_INDEX)} dla konta 5410 i {pct(cfg.IMPORT_OTHER_INDEX)} dla pozostałych. "
        f"Wyłącznie wiersz {cfg.IMPORT_IT_RENEWAL_MPK}, konto 5420, zawiera dodatkowe {pln(cfg.IMPORT_IT_RENEWAL_PLN)} w październiku "
        f"({cfg.IMPORT_IT_RENEWAL_MONTH}) oraz komentarz o odnowieniu licencji. Łączna dopłata w całym pliku "
        f"wynosi {pln(cfg.IMPORT_IT_RENEWAL_PLN)}. Pozostałe wiersze konta 5420 zachowują w październiku zwykłą bazę miesięczną. "
        "Wszystkie pozostałe komentarze są puste. Arkusz Opis wyjaśnia syntetyczny charakter danych, "
        "znaczenie kolumn i metodę obliczeń. Ten roboczy projekt nie jest nowym scenariuszem fakt_pnl.\n",
        "## Uproszczenia i znane ograniczenia\n",
        "Budżet RF N opiera się na ACT RF N poprzedniego roku. Roczna baza każdego MPK jest "
        "oczyszczana o długość działalności i rozruch, a następnie rozkładana gładkim profilem "
        "sezonowości, dni tygodnia, promocji i kalendarza handlowego. Nie ma nowego szumu dziennego "
        "w BUD. Dla nowych sklepów bez bazy używa się średniej produktywności na m2 innych sklepów "
        "tej samej marki i kraju. To uproszczenie dydaktyczne, nie opis realnego procesu budżetowego.\n",
        "BUD korzysta z planowanych dat otwarcia i znanych dat zamknięcia. Czynsze rosną w nim o 3%, "
        "koszt zamówienia o 3%, płace o 7%, media i pozostałe koszty stałe o 3%. "
        f"FC od grudnia uwzględnia Kroko na poziomie {pct(cfg.FC_DECLINING_FACTOR)} BUD, rzeczywisty rozruch Vento DE, "
        "nowe stawki czynszów Aurea AT i logistyki e-commerce DE. Pozostałe pozycje zachowują BUD; "
        "koszty bezpośrednio zależne od sprzedaży zmieniają się razem z nią.\n",
        "Koszty stałe sklepów są proporcjonalne do dni działalności w miesiącu, a nie do dni handlowych. "
        "Rozruch jest liniowy od 70% do 100% w sześć miesięcy kalendarzowych. "
        "Cztery opóźnione sklepy mają mniejszy format niż typowy sklep Vento; "
        "pozostałe parametry ekonomiczne losowane są raz dla MPK.\n",
        "Podział kategorii zachowuje dokładne sumy sprzedaży, kosztu i sztuk. "
        "Marża kategorii w danej kombinacji miesiąca, marki, kraju i kanału jest wspólna; "
        "nie modeluje się osobnej marży SKU. Reszty zaokrągleń przypisuje się największej kategorii. "
        "SR występuje tylko w VEN, BI głównie w LUM, a KRO sprzedaje wyłącznie obuwie i akcesoria.\n",
        "Kursy są informacyjne; kwoty są już w PLN. Nie modeluje się konsolidacyjnych eliminacji, "
        "VAT, zwrotów, transakcji klienta, zapasów, cash flow, podatku dochodowego ani cen realnych licencji. "
        "GRP jest wyłącznie technicznym wierszem dim_marka dla centrali i nie trafia do sprzedaży "
        "ani plików celów. Nie tworzy się relacji po nazwach tekstowych ani po nieunikalnym początku miesiąca.\n",
        "Rozkład celu rocznego jest demonstracją sezonowości, nie osobnym kompletnym planem nowych sklepów. "
        "Udział LY pochodzi z RF 2025/26; średnia dwuletnia to średnia udziałów, nie udział "
        "w dwuletniej sumie. Cel powtarza się w każdym z 12 miesięcy i nie jest addytywny po czasie. "
        "Zaokrąglenie miesięcznych planów do groszy może zmienić sumę roczną o kilka groszy.\n",
        "## Luki i pytania do dalszych ćwiczeń\n",
        "Brak rzeczywistego planu kont, zasad alokacji kosztów i uzgodnionego kalendarza poza Polską. "
        "Przed użyciem na danych rzeczywistych trzeba ustalić definicję LFL, obsługę zwrotów, "
        "kalendarze lokalne, datę zamknięcia miesiąca oraz role dostępu. Ten zestaw nie pozwala "
        "wnioskować o wynikach firmy, kosztach usług Azure ani uprawnieniach licencyjnych.\n",
    ])
    (cfg.DATA_DIR / "SLOWNIK_DANYCH.md").write_text("\n".join(text), encoding="utf-8")
