"""Kontrakt kolumn wspólny dla eksportu, słownika i walidatora."""

import pandas as pd
import pyarrow as pa


def fields(*items):
    return list(items)


SCHEMAS = {
    "dim_data": fields(
        ("data", "date32", "Dzień, klucz wymiaru."),
        ("rok", "int64", "Rok kalendarzowy."),
        ("miesiac", "int64", "Numer miesiąca kalendarzowego, od 1 do 12."),
        ("miesiac_nazwa", "string", "Polska nazwa miesiąca."),
        ("miesiac_skrot", "string", "Skrót polskiej nazwy miesiąca."),
        ("miesiac_poczatek", "date32", "Pierwszy dzień miesiąca."),
        ("okres_rrrrmm", "int64", "Okres w postaci RRRRMM."),
        ("dzien_tygodnia_nr", "int64", "Od 1 dla poniedziałku do 7 dla niedzieli."),
        ("dzien_tygodnia_nazwa", "string", "Polska nazwa dnia tygodnia."),
        ("tydzien_iso", "int64", "Numer tygodnia ISO."),
        ("rok_finansowy", "string", "Etykieta roku finansowego, np. 2026/27."),
        ("rok_finansowy_nr", "int64", "Rok kalendarzowy rozpoczęcia roku finansowego."),
        ("kwartal_finansowy", "string", "1Q, 2Q, 3Q albo 4Q."),
        ("kwartal_finansowy_pelny", "string", "Kwartał wraz z rokiem, np. 3Q 2026/27."),
        ("kwartal_finansowy_sort", "int64", "Rok rozpoczęcia RF razy 10 plus numer kwartału, np. 20263."),
        ("polrocze_finansowe", "string", "1H albo 2H."),
        ("miesiac_finansowy_nr", "int64", "Kwiecień ma numer 1, marzec numer 12."),
        ("czy_swieto_pl", "bool", "Święto ustawowo wolne w Polsce według reguł generatora."),
        ("nazwa_swieta", "string", "Nazwa święta albo null."),
        ("czy_niedziela_handlowa_pl", "bool", "Niedziela handlowa według uproszczenia w SPEC.md."),
        ("czy_dzien_handlowy_pl", "bool", "Dzień otwarcia sklepów w Polsce."),
        ("czy_black_friday", "bool", "Ostatni piątek listopada."),
        ("czy_miesiac_zamkniety", "bool", "Miesiąc do listopada 2026 włącznie."),
    ),
    "dim_marka": fields(
        ("marka_kod", "string", "AUR, VEN, LUM, KRO albo techniczny kod GRP."),
        ("marka_nazwa", "string", "Nazwa marki."),
        ("grupa_docelowa", "string", "Umowny segment odbiorców."),
        ("kolejnosc", "int64", "Kolejność prezentacji."),
    ),
    "dim_kraj": fields(
        ("kraj_kod", "string", "Dwuliterowy kod kraju."),
        ("kraj_nazwa", "string", "Polska nazwa kraju."),
        ("waluta_lokalna", "string", "Kod waluty lokalnej."),
        ("region", "string", "Region geograficzny."),
    ),
    "dim_kategoria": fields(
        ("kategoria_kod", "string", "Kod kategorii asortymentowej."),
        ("kategoria_nazwa", "string", "Nazwa kategorii."),
        ("grupa", "string", "Grupa asortymentu."),
    ),
    "dim_scenariusz": fields(
        ("scenariusz_kod", "string", "ACT, BUD albo FC."),
        ("scenariusz_nazwa", "string", "Polska nazwa scenariusza."),
        ("opis", "string", "Zakres i znaczenie scenariusza."),
        ("kolejnosc", "int64", "Kolejność prezentacji."),
    ),
    "dim_konto": fields(
        ("konto_id", "string", "Tekstowy identyfikator konta, np. 4010."),
        ("konto_nazwa", "string", "Nazwa pozycji rachunku wyników."),
        ("sekcja", "string", "Sekcja rachunku wyników."),
        ("grupa_kosztow", "string", "Grupa analityczna kosztu lub przychodu."),
        ("znak", "int64", "1 dla przychodów, -1 dla kosztów."),
        ("kolejnosc", "int64", "Kolejność prezentacji konta."),
    ),
    "dim_mpk": fields(
        ("mpk_id", "string", "Klucz sklepu, kanału e-commerce lub działu centrali."),
        ("mpk_nazwa", "string", "Czytelna nazwa MPK."),
        ("typ_mpk", "string", "Sklep, E-commerce albo Centrala."),
        ("kanal", "string", "Kanał sprzedaży lub Centrala."),
        ("marka_kod", "string", "Kod marki; GRP oznacza centralę bez przypisania do marki."),
        ("kraj_kod", "string", "Kod kraju; centrala ma PL."),
        ("miasto", "string", "Miasto sklepu; pusty tekst dla innych MPK."),
        ("format_sklepu", "string", "Format sklepu; pusty tekst dla innych MPK."),
        ("powierzchnia_m2", "int64", "Powierzchnia sprzedaży; null poza sklepami."),
        ("dzial_centrali", "string", "Nazwa działu; pusty tekst poza centralą."),
        ("data_otwarcia_plan", "date32", "Planowany pierwszy dzień działalności."),
        ("data_otwarcia", "date32", "Rzeczywisty pierwszy dzień; null dla sklepów planowanych."),
        ("data_zamkniecia", "date32", "Ostatni dzień działalności albo null."),
        ("status", "string", "Status na 08.12.2026: Aktywny, Zamknięty albo Planowany."),
        ("lfl_od", "date32", "Pierwszy miesiąc po 12 pełnych miesiącach działalności; null poza otwartymi sklepami."),
    ),
    "fakt_sprzedaz_dzienna": fields(
        ("data", "date32", "Dzień sprzedaży."),
        ("mpk_id", "string", "Sklep lub e-commerce."),
        ("sprzedaz_netto_pln", "float64", "Sprzedaż netto bez VAT w PLN."),
        ("koszt_wlasny_pln", "float64", "Koszt sprzedanych towarów w PLN."),
        ("liczba_paragonow", "int64", "Liczba paragonów lub zamówień e-commerce."),
        ("liczba_sztuk", "int64", "Liczba sprzedanych sztuk."),
    ),
    "fakt_sprzedaz_kategorie_mies": fields(
        ("miesiac", "date32", "Pierwszy dzień zamkniętego miesiąca."),
        ("marka_kod", "string", "Kod marki."),
        ("kraj_kod", "string", "Kod kraju."),
        ("kanal", "string", "Sklep albo E-commerce."),
        ("kategoria_kod", "string", "Kod kategorii."),
        ("sprzedaz_netto_pln", "float64", "Sprzedaż kategorii w PLN."),
        ("koszt_wlasny_pln", "float64", "Koszt towarów kategorii w PLN."),
        ("liczba_sztuk", "int64", "Liczba sztuk przypisana do kategorii."),
    ),
    "fakt_pnl": fields(
        ("miesiac", "date32", "Pierwszy dzień miesiąca."),
        ("mpk_id", "string", "Klucz miejsca powstawania kosztów."),
        ("konto_id", "string", "Tekstowy numer konta."),
        ("scenariusz_kod", "string", "ACT, BUD albo FC."),
        ("kwota_pln", "float64", "Dodatnia kwota; znak wynika z dim_konto."),
    ),
    "fakt_kursy_walut": fields(
        ("miesiac", "date32", "Pierwszy dzień miesiąca."),
        ("waluta", "string", "EUR, SEK albo DKK."),
        ("kurs_sredni_pln", "float64", "PLN za jedną jednostkę waluty, sześć miejsc dziesiętnych."),
    ),
    "agg_sprzedaz_mies": fields(
        ("miesiac", "date32", "Pierwszy dzień miesiąca."),
        ("marka_kod", "string", "Kod marki."),
        ("kraj_kod", "string", "Kod kraju."),
        ("kanal", "string", "Sklep albo E-commerce."),
        ("scenariusz_kod", "string", "ACT, BUD albo FC."),
        ("sprzedaz_netto_pln", "float64", "Suma konta 4010 w PLN."),
        ("koszt_wlasny_pln", "float64", "Suma konta 4510 w PLN."),
    ),
    "plan_kalendarz": fields(
        ("miesiac", "date32", "Pierwszy dzień miesiąca, unikalny klucz."),
        ("rok_finansowy", "string", "Etykieta RF od kwietnia do marca, np. 2026/27; ASCII."),
        ("rok_finansowy_nr", "int64", "Rok kalendarzowy rozpoczęcia RF."),
        ("kwartal", "string", "1Q, 2Q, 3Q albo 4Q; ASCII."),
        ("kwartal_pelny", "string", "Kwartał wraz z RF, np. 3Q 2026/27; ASCII."),
        ("kwartal_sort", "int64", "Rok rozpoczęcia RF razy 10 plus numer kwartału, np. 20263."),
        ("miesiac_fin_nr", "int64", "Kwiecień ma numer 1, marzec numer 12."),
        ("miesiac_nazwa", "string", "Skrót ASCII: Kwi, Maj, Cze, Lip, Sie, Wrz, Paz, Lis, Gru, Sty, Lut, Mar."),
        ("okres", "string", "Miesiąc kalendarzowy RRRR-MM, np. 2026-12; ASCII."),
        ("rok", "int64", "Rok kalendarzowy."),
        ("miesiac_nr", "int64", "Numer miesiąca kalendarzowego od 1 do 12."),
        ("czy_miesiac_zamkniety", "bool", "Zamknięty do listopada 2026 włącznie, zgodnie z dim_data."),
    ),
    "ref_plan_2027_28_rozklad": fields(
        ("marka_kod", "string", "Kod marki."),
        ("kraj_kod", "string", "Kod kraju."),
        ("kanal", "string", "Sklep albo E-commerce."),
        ("miesiac", "date32", "Pierwszy dzień miesiąca RF 2027/28."),
        ("cel_roczny_pln", "float64", "Cel z arkusza Cele; powtórzony w 12 miesiącach, nie sumować po miesiącach."),
        ("udzial_ly", "float64", "Udział miesiąca w ACT RF 2025/26."),
        ("plan_ly_pln", "float64", "Cel roczny razy udział LY, zaokrąglony do groszy."),
        ("udzial_sr2", "float64", "Średnia udziałów ACT RF 2024/25 i 2025/26."),
        ("plan_sr2_pln", "float64", "Cel roczny razy średni udział, zaokrąglony do groszy."),
    ),
}

GRAINS = {
    "dim_data": ["data"], "dim_marka": ["marka_kod"], "dim_kraj": ["kraj_kod"],
    "dim_kategoria": ["kategoria_kod"], "dim_scenariusz": ["scenariusz_kod"],
    "dim_konto": ["konto_id"], "dim_mpk": ["mpk_id"],
    "fakt_sprzedaz_dzienna": ["data", "mpk_id"],
    "fakt_sprzedaz_kategorie_mies": ["miesiac", "marka_kod", "kraj_kod", "kanal", "kategoria_kod"],
    "fakt_pnl": ["miesiac", "mpk_id", "konto_id", "scenariusz_kod"],
    "fakt_kursy_walut": ["miesiac", "waluta"],
    "agg_sprzedaz_mies": ["miesiac", "marka_kod", "kraj_kod", "kanal", "scenariusz_kod"],
    "plan_kalendarz": ["miesiac"],
    "ref_plan_2027_28_rozklad": ["marka_kod", "kraj_kod", "kanal", "miesiac"],
}
DESCRIPTIONS = {
    "dim_data": "Pełny kalendarz dzienny, finansowy i handlowy.",
    "dim_marka": "Cztery marki fikcyjnej sieci i techniczny wiersz GRP dla centrali.",
    "dim_kraj": "Sześć rynków wraz z walutami informacyjnymi.",
    "dim_kategoria": "Dziewięć kategorii asortymentowych.",
    "dim_scenariusz": "Znaczenie wykonania, budżetu i prognozy.",
    "dim_konto": "Konta rachunku wyników i znaki używane w miarach.",
    "dim_mpk": "Historia sklepów, kanały internetowe i działy centrali.",
    "fakt_sprzedaz_dzienna": "Sprzedaż tylko w dniach rzeczywistej działalności, także niezamknięty grudzień.",
    "fakt_sprzedaz_kategorie_mies": "Podział zamkniętych miesięcy na asortyment, uzgodniony do sprzedaży dziennej.",
    "fakt_pnl": "Rachunek wyników w scenariuszach ACT, BUD i FC, bez wyliczonych sum EBITDA i EBIT.",
    "fakt_kursy_walut": "Informacyjne syntetyczne kursy, nie służą do ponownego przeliczania faktów.",
    "agg_sprzedaz_mies": "Uzgodniony do P&L agregat przychodów i kosztu własnego do planowania.",
    "plan_kalendarz": "Miesięczny kalendarz dla SM_Planowanie: 60 miesięcy od kwietnia 2023 do marca 2028. Wszystkie wartości tekstowe są czystym ASCII; atrybuty finansowe pochodzą z dim_data.",
    "ref_plan_2027_28_rozklad": "Referencyjne rozłożenie celu rocznego na miesiące dwiema metodami.",
}
RELATIONSHIPS = {
    "dim_data": "Klucz data jest stroną jeden relacji do dat faktów. Fakt miesięczny łączy się przez miesiac = data, nie przez nieunikalny miesiac_poczatek.",
    "dim_marka": "marka_kod łączy się z dim_mpk oraz faktami zagregowanymi.",
    "dim_kraj": "kraj_kod łączy się z dim_mpk oraz faktami zagregowanymi.",
    "dim_kategoria": "kategoria_kod łączy się z faktem kategorii.",
    "dim_scenariusz": "scenariusz_kod łączy się z P&L i agregatem sprzedaży.",
    "dim_konto": "konto_id łączy się z fakt_pnl.",
    "dim_mpk": "mpk_id łączy się z P&L i faktem dziennym; kraj_kod z dim_kraj, marka_kod z dim_marka. GRP to techniczny wiersz wymiaru dla sześciu działów centrali, nie marka handlowa.",
    "fakt_sprzedaz_dzienna": "data do dim_data.data; mpk_id do dim_mpk.mpk_id.",
    "fakt_sprzedaz_kategorie_mies": "miesiac do dim_data.data; marka_kod, kraj_kod i kategoria_kod do odpowiednich wymiarów. Kanal jest atrybutem, nie oddzielnym wymiarem.",
    "fakt_pnl": "miesiac do dim_data.data; mpk_id do dim_mpk; konto_id do dim_konto; scenariusz_kod do dim_scenariusz.",
    "fakt_kursy_walut": "miesiac do dim_data.data; waluta to domena kodów walut z dim_kraj, bez relacji jeden do wielu po nieunikalnej walucie kraju.",
    "agg_sprzedaz_mies": "miesiac do dim_data.data; marka_kod, kraj_kod i scenariusz_kod do odpowiednich wymiarów.",
    "plan_kalendarz": "miesiac jest stroną jeden relacji do agg_sprzedaz_mies.miesiac i ref_plan_2027_28_rozklad.miesiac w modelu planistycznym. Daty i atrybuty odpowiadają pierwszym dniom miesięcy w dim_data.",
    "ref_plan_2027_28_rozklad": "miesiac do dim_data.data; marka_kod i kraj_kod do wymiarów. Cel roczny odpowiada jednej kombinacji w arkuszu Cele.",
}
ARROW_TYPES = {"string": pa.string(), "int64": pa.int64(), "float64": pa.float64(),
               "bool": pa.bool_(), "date32": pa.date32()}


def arrow_schema(name):
    return pa.schema([(column, ARROW_TYPES[kind]) for column, kind, _ in SCHEMAS[name]])


def normalize(name, frame):
    frame = frame[[column for column, _, _ in SCHEMAS[name]]].copy()
    for column, kind, _ in SCHEMAS[name]:
        if kind == "date32":
            frame[column] = pd.to_datetime(frame[column]).astype("datetime64[ns]")
        elif kind == "int64":
            frame[column] = frame[column].astype("Int64" if frame[column].isna().any() else "int64")
        else:
            frame[column] = frame[column].astype(kind)
    return frame.sort_values(GRAINS[name], kind="stable").reset_index(drop=True)
