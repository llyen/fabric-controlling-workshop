# Specyfikacja danych syntetycznych

Dane opisują fikcyjną grupę handlową Fabrikam Fashion z czterema markami o różnym profilu (odzież biznesowa, sport, bielizna, obuwie), działającą w sześciu krajach. Liczby są wymyślone i nie odzwierciedlają wyników żadnej firmy. Skala jest umowna (około 0,8 do 1 mld PLN sprzedaży rocznie), bo w ćwiczeniu liczą się proporcje, sezonowość i zjawiska do analizy, a nie wielkości.

Generator jest deterministyczny (`numpy.random.default_rng(731905)`), uruchamia się go jednym poleceniem `python generator/generate_data.py` z katalogu głównego repozytorium i kończy pracę w czasie poniżej 3 minut.

## Parametry globalne

| Parametr | Wartość |
|---|---|
| Data stanu danych (AS_OF) | 2026-12-09 |
| Dane dzienne | 2023-04-01 do 2026-12-08 |
| Ostatni zamknięty miesiąc (P&L ACT) | 2026-11 |
| Zakres kalendarza `dim_data` | 2023-04-01 do 2028-03-31 |
| Waluta raportowa | PLN (wszystkie kwoty w PLN) |

Rok finansowy (RF) trwa od 1 kwietnia do 31 marca. Etykieta `2026/27` oznacza okres 2026-04-01 do 2027-03-31, `rok_finansowy_nr` = 2026. Kwartały finansowe: 1Q kwiecień do czerwca, 2Q lipiec do września, 3Q październik do grudnia, 4Q styczeń do marca. Półrocza: 1H kwiecień do września, 2H październik do marca. Miesiąc finansowy nr 1 to kwiecień, nr 12 to marzec.

## Konwencje techniczne

Nazwy tabel i kolumn w plikach: ASCII, snake_case, po polsku bez znaków diakrytycznych. Wartości tekstowe (nazwy marek, miast, kont) mogą mieć polskie znaki. Daty jako typ `date` (w parquet `date32`), kwoty jako `float64` zaokrąglone do 2 miejsc, liczniki jako `int64`, flagi jako `bool`. Klucze tekstowe jako `string`.

Wyjście:

* `dane/parquet/<tabela>.parquet` dla każdej tabeli (źródło ładowania do Fabric, kompresja snappy),
* `dane/csv/<tabela>.csv` dla każdej tabeli poza `fakt_sprzedaz_dzienna` (UTF-8 z BOM, separator przecinek, kropka dziesiętna); tabela dzienna jako `dane/csv/fakt_sprzedaz_dzienna.csv.gz`,
* `dane/excel/*.xlsx` (wejścia planistyczne, opis niżej),
* `dane/SLOWNIK_DANYCH.md` (słownik po polsku),
* `dane/oczekiwane_odpowiedzi.md` oraz `dane/oczekiwane_odpowiedzi.csv` (klucz odpowiedzi do pytań testowych agenta).

Łączny rozmiar katalogu `dane/` poniżej 60 MB.

## Wymiary

### dim_marka

| Kolumna | Typ | Opis |
|---|---|---|
| marka_kod | string | AUR, VEN, LUM, KRO, GRP |
| marka_nazwa | string | Aurea, Vento, Lumi, Kroko, Centrala (bez marki) |
| grupa_docelowa | string | Odzież biznesowa premium, Sport i outdoor, Bielizna i odzież domowa, Obuwie i dodatki, nie dotyczy |
| kolejnosc | int64 | 1 do 5 |

GRP jest technicznym piątym wierszem dla centrali bez marki. Nie występuje w `fakt_sprzedaz_kategorie_mies`, `agg_sprzedaz_mies`, celach Excel ani `ref_plan_2027_28_rozklad`, które obejmują wyłącznie cztery marki handlowe.

### dim_kraj

| Kolumna | Typ | Opis |
|---|---|---|
| kraj_kod | string | PL, DE, AT, NL, SE, DK |
| kraj_nazwa | string | Polska, Niemcy, Austria, Holandia, Szwecja, Dania |
| waluta_lokalna | string | PLN, EUR, EUR, EUR, SEK, DKK |
| region | string | Polska; Europa Zachodnia (DE, AT, NL); Skandynawia (SE, DK) |

### dim_kategoria

| kategoria_kod | kategoria_nazwa | grupa |
|---|---|---|
| OW | Odzież wierzchnia | Odzież |
| SW | Swetry i bluzy | Odzież |
| SP | Spodnie | Odzież |
| SU | Sukienki i spódnice | Odzież |
| TS | T-shirty i koszule | Odzież |
| OB | Obuwie | Obuwie |
| AK | Akcesoria | Akcesoria |
| BI | Bielizna i odzież domowa | Odzież |
| SR | Odzież sportowa | Odzież |

Asortyment zależy od marki. SR sprzedaje tylko Vento, Kroko sprzedaje wyłącznie OB i AK, Lumi nie ma odzieży wierzchniej ani obuwia, a BI dominuje w jej sprzedaży.

### dim_scenariusz

| scenariusz_kod | scenariusz_nazwa | opis | kolejnosc |
|---|---|---|---|
| ACT | Wykonanie | Dane rzeczywiste z zamkniętych miesięcy | 1 |
| BUD | Budżet | Budżet zatwierdzony przed rozpoczęciem roku finansowego | 2 |
| FC | Prognoza 8+4 | Dla RF 2026/27: wykonanie kwiecień do listopada 2026 oraz prognoza grudzień 2026 do marca 2027 | 3 |

### dim_konto

Kwoty w faktach są dodatnie, znak nadaje kolumna `znak`. Plan kont jest uproszczony i czterocyfrowy.

| konto_id | konto_nazwa | sekcja | grupa_kosztow | znak | kolejnosc |
|---|---|---|---|---|---|
| 4010 | Przychody ze sprzedaży netto | Przychody | Przychody | 1 | 10 |
| 4510 | Koszt własny sprzedaży | Koszt własny | Koszt własny | -1 | 20 |
| 5110 | Wynagrodzenia personelu sklepów | Koszty operacyjne | Koszty sklepów | -1 | 40 |
| 5120 | Czynsze | Koszty operacyjne | Koszty sklepów | -1 | 41 |
| 5130 | Media i utrzymanie | Koszty operacyjne | Koszty sklepów | -1 | 42 |
| 5210 | Marketing | Koszty operacyjne | Marketing | -1 | 50 |
| 5220 | Logistyka e-commerce | Koszty operacyjne | Koszty e-commerce | -1 | 55 |
| 5230 | Prowizje płatnicze | Koszty operacyjne | Koszty e-commerce | -1 | 56 |
| 5310 | Logistyka magazynowa | Koszty operacyjne | Logistyka | -1 | 58 |
| 5410 | Wynagrodzenia centrali | Koszty operacyjne | Koszty centrali | -1 | 60 |
| 5420 | IT i licencje | Koszty operacyjne | Koszty centrali | -1 | 61 |
| 5910 | Pozostałe koszty operacyjne | Koszty operacyjne | Pozostałe | -1 | 70 |
| 6010 | Amortyzacja | Amortyzacja | Amortyzacja | -1 | 90 |

Marża brutto = 4010 minus 4510. EBITDA = przychody minus koszt własny minus koszty operacyjne. EBIT = EBITDA minus amortyzacja. Te pozycje liczy model semantyczny, nie ma ich w faktach.

### dim_mpk

Miejsca powstawania kosztów (MPK): sklepy, kanały e-commerce, działy centrali.

| Kolumna | Typ | Opis |
|---|---|---|
| mpk_id | string | Sklep `SK-<MARKA>-<KRAJ>-<NNN>`, np. `SK-AUR-AT-001`; e-commerce `EC-<MARKA>-<KRAJ>`; centrala `HQ-<DZIAL>` lub `HQ-MKT-<MARKA>` |
| mpk_nazwa | string | Np. `Aurea Wiedeń 2`, `Lumi e-commerce Szwecja`, `Centrala Finanse` |
| typ_mpk | string | Sklep, E-commerce, Centrala |
| kanal | string | Sklep, E-commerce, Centrala (dla centrali) |
| marka_kod | string | Kod marki; dla działów centrali bez marki wartość `GRP` |
| kraj_kod | string | Kod kraju; centrala zawsze PL |
| miasto | string | Miasto (dla e-commerce i centrali: pusty) |
| format_sklepu | string | Centrum handlowe, Park handlowy, Ulica handlowa (tylko sklepy) |
| powierzchnia_m2 | int64 | Powierzchnia sprzedaży (tylko sklepy, inaczej null) |
| dzial_centrali | string | Dla centrali: Finanse, Technologia, Łańcuch dostaw, Kadry, Produkt i projektowanie, Administracja i prawo, Marketing |
| data_otwarcia_plan | date | Planowana data otwarcia |
| data_otwarcia | date | Rzeczywista data otwarcia (null dla sklepów planowanych) |
| data_zamkniecia | date | Data zamknięcia lub null |
| status | string | Aktywny, Zamknięty, Planowany |
| lfl_od | date | Pierwszy dzień miesiąca, od którego sklep jest porównywalny (LFL): pierwszy dzień miesiąca następującego po upływie 12 pełnych miesięcy od otwarcia; null dla innych niż sklepy |

Wielkość sieci (sklepy aktywne na 2026-12-08, razem 135):

| Marka | PL | DE | AT | NL | SE | DK |
|---|---|---|---|---|---|---|
| AUR | 12 | 6 | 5 | 3 | 2 | 1 |
| VEN | 20 | 12 | 4 | 3 | 3 | 2 |
| LUM | 16 | 4 | 2 | 2 | 0 | 0 |
| KRO | 24 | 6 | 3 | 2 | 2 | 1 |

Vento DE obejmuje 4 sklepy otwarte w RF 2026/27 z opóźnieniem (opis w historiach). Lumi w Szwecji i Danii sprzedaje tylko przez e-commerce. E-commerce: po jednym MPK na każdą parę marka i kraj (24 MPK). Centrala: 6 działów `GRP` oraz 4 MPK marketingu marek (`HQ-MKT-AUR` itd.), razem 10.

Historia sieci: większość sklepów otwarta przed 2023-04-01 (losowo 2008 do 2022). Otwarcia w trakcie okresu danych: 8 sklepów VEN, 3 sklepy LUM i 2 sklepy AUR, z datą rzeczywistą równą planowanej lub przesuniętą najwyżej o miesiąc. Zamknięcia: 4 sklepy KRO od maja 2025 do czerwca 2026 i 1 sklep LUM w sierpniu 2025. Dodatkowo 7 sklepów o statusie Planowany z otwarciem w RF 2027/28 (VEN 4, LUM 2, AUR 1), bez danych w faktach.

Powierzchnie (m2): AUR 250 do 500, VEN 600 do 1200, LUM 80 do 200, KRO 150 do 350. Nazwy miast realne (np. Warszawa, Kielce, Berlin, Wiedeń, Utrecht, Malmö), bez nazw centrów handlowych.

### dim_data

Jeden wiersz na dzień od 2023-04-01 do 2028-03-31.

| Kolumna | Typ | Opis |
|---|---|---|
| data | date | Klucz |
| rok | int64 | Rok kalendarzowy |
| miesiac | int64 | 1 do 12 |
| miesiac_nazwa | string | styczeń, luty, ... |
| miesiac_skrot | string | sty, lut, mar, kwi, maj, cze, lip, sie, wrz, paź, lis, gru |
| miesiac_poczatek | date | Pierwszy dzień miesiąca (klucz do faktów miesięcznych) |
| okres_rrrrmm | int64 | Np. 202612 |
| dzien_tygodnia_nr | int64 | 1 poniedziałek do 7 niedziela |
| dzien_tygodnia_nazwa | string | poniedziałek ... niedziela |
| tydzien_iso | int64 | Numer tygodnia ISO |
| rok_finansowy | string | Np. `2026/27` |
| rok_finansowy_nr | int64 | Np. 2026 |
| kwartal_finansowy | string | 1Q, 2Q, 3Q, 4Q |
| kwartal_finansowy_pelny | string | Np. `3Q 2026/27` |
| kwartal_finansowy_sort | int64 | rok_finansowy_nr × 10 + numer kwartału, np. `20263` dla `3Q 2026/27` |
| polrocze_finansowe | string | 1H, 2H |
| miesiac_finansowy_nr | int64 | 1 (kwiecień) do 12 (marzec) |
| czy_swieto_pl | bool | Święto ustawowo wolne w Polsce |
| nazwa_swieta | string | Nazwa święta lub null |
| czy_niedziela_handlowa_pl | bool | Niedziela handlowa w Polsce |
| czy_dzien_handlowy_pl | bool | Sklepy stacjonarne w Polsce otwarte |
| czy_black_friday | bool | Ostatni piątek listopada |
| czy_miesiac_zamkniety | bool | Miesiąc zamknięty księgowo (do 2026-11 włącznie) |

Święta w Polsce: 1 i 6 stycznia, Wielkanoc i Poniedziałek Wielkanocny, 1 i 3 maja, Zielone Świątki (niedziela), Boże Ciało, 15 sierpnia, 1 i 11 listopada, 25 i 26 grudnia, a od 2025 roku także 24 grudnia. Niedziele handlowe (uproszczenie generatora, opisane w słowniku): ostatnia niedziela stycznia, niedziela przed Wielkanocą, ostatnia niedziela kwietnia, czerwca i sierpnia, w latach 2023 i 2024 dwie niedziele przed Bożym Narodzeniem, od 2025 trzy niedziele grudnia poprzedzające 24 grudnia. Jeśli niedziela handlowa wypada w święto, nie jest handlowa. Poza Polską uproszczenie: sklepy zamknięte 25 grudnia, 1 stycznia i w Wielkanoc, w pozostałe dni otwarte.

## Fakty

### fakt_sprzedaz_dzienna

Ziarno: dzień × MPK (tylko sklepy i e-commerce). Brak wiersza w dniu, w którym sklep był zamknięty (niedziele niehandlowe i święta w PL, przed otwarciem, po zamknięciu). Zakres 2023-04-01 do 2026-12-08.

| Kolumna | Typ | Opis |
|---|---|---|
| data | date | Dzień sprzedaży |
| mpk_id | string | Sklep lub e-commerce |
| sprzedaz_netto_pln | float64 | Sprzedaż netto (bez VAT) |
| koszt_wlasny_pln | float64 | Koszt własny sprzedanych towarów |
| liczba_paragonow | int64 | Paragony w sklepie lub zamówienia w e-commerce |
| liczba_sztuk | int64 | Sprzedane sztuki |

Model sprzedaży (parametry w `config.py`):

* gęstość sprzedaży sklepów (PLN/m2/rok w 2023): AUR 15 000, VEN 7 000, LUM 19 000, KRO 12 500; mnożnik kraju PL 1,00, DE 1,25, AT 1,20, NL 1,20, SE 1,30, DK 1,30,
* sezonowość miesięczna (sty 0,78, lut 0,74, mar 0,88, kwi 0,96, maj 1,02, cze 0,98, lip 0,92, sie 0,94, wrz 1,00, paź 1,04, lis 1,22, gru 1,48, znormalizowana),
* dzień tygodnia (pon 0,86, wt 0,86, śr 0,90, czw 0,96, pt 1,12, sob 1,32, nd 1,00; niedziela handlowa w PL 1,30); e-commerce w niedzielę 1,15,
* ostatnie dwa tygodnie przed 24 grudnia ×1,30; 24 grudnia ×0,5 tam, gdzie sklepy otwarte,
* Black Friday: sklepy ×2,0, e-commerce ×3,0; tydzień przed BF ×1,2; sobota i niedziela po BF ×1,4; Cyber Monday e-commerce ×2,0,
* trend LFL sklepów +3% r/r (Kroko inaczej, patrz historie), e-commerce +14% r/r (Lumi e-commerce +28% r/r); udział e-commerce w sprzedaży grupy skalibrowany do 18% w RF 2023/24,
* nowe sklepy: rozruch od 70% do 100% docelowej sprzedaży liniowo przez 6 miesięcy,
* szum dzienny logarytmiczno-normalny (sigma 0,08 sklepy, 0,12 e-commerce),
* średni paragon (PLN): AUR 320, VEN 210, LUM 95, KRO 240; e-commerce ×1,25; sztuk na paragon 1,7 (LUM 2,8),
* marża brutto % bazowa: AUR 60, VEN 50, LUM 62, KRO 54; korekty miesięczne w punktach procentowych: sty -5, lut -2, mar +1, kwi +2, maj +1, cze -1, lip -5, sie -2, wrz +1, paź +2, lis -1; dzień Black Friday -8; e-commerce -1.

### fakt_sprzedaz_kategorie_mies

Ziarno: miesiąc × marka × kraj × kanał × kategoria, dla zamkniętych miesięcy 2023-04 do 2026-11. Suma po kategoriach jest równa sumie z `fakt_sprzedaz_dzienna` dla tego samego miesiąca, marki, kraju i kanału (tolerancja 1 PLN).

| Kolumna | Typ | Opis |
|---|---|---|
| miesiac | date | Pierwszy dzień miesiąca |
| marka_kod | string | |
| kraj_kod | string | |
| kanal | string | Sklep lub E-commerce |
| kategoria_kod | string | |
| sprzedaz_netto_pln | float64 | |
| koszt_wlasny_pln | float64 | |
| liczba_sztuk | int64 | |

Udziały kategorii zależą od marki i miesiąca. Odzież wierzchnia, sprzedawana tylko przez Aureę i Vento, ma w skali grupy od 13% do 19% sprzedaży w październiku do stycznia i od 2% do 4% w maju do sierpnia. Swetry i bluzy są wysokie zimą, sukienki i T-shirty latem, akcesoria i bielizna w grudniu.

### fakt_pnl

Ziarno: miesiąc × MPK × konto × scenariusz. Kwoty dodatnie.

| Kolumna | Typ | Opis |
|---|---|---|
| miesiac | date | Pierwszy dzień miesiąca |
| mpk_id | string | |
| konto_id | string | Np. `4010` |
| scenariusz_kod | string | ACT, BUD, FC |
| kwota_pln | float64 | Kwota dodatnia |

Zakres scenariuszy:

* ACT: 2023-04 do 2026-11, każde MPK aktywne w danym miesiącu,
* BUD: RF 2024/25, 2025/26 i 2026/27 (pełne 12 miesięcy),
* FC: RF 2026/27; kwiecień do listopada 2026 to kopia ACT, grudzień 2026 do marca 2027 to prognoza.

Reguły ACT:

* 4010 i 4510 dla sklepów i e-commerce to dokładne sumy miesięczne z `fakt_sprzedaz_dzienna`,
* sklepy: 5110 = część stała (m2 × stawka × indeks płac kraju i roku) plus 2,5% sprzedaży; 5120 = m2 × stawka czynszu, indeksacja co kwiecień (+4% 2024, +3,5% 2025, +3% 2026), około 12,5% sprzedaży; 5130 = m2 × stawka, zimą +20%, latem +10%; 5910 = 1,5% sprzedaży plus mała kwota stała na m2; 6010 stała miesięczna od otwarcia,
* e-commerce: 5220 = liczba zamówień × koszt zamówienia (PL 16 PLN, zagranica 24 PLN w RF 2023/24, +3% rocznie), 5230 = 1,4% sprzedaży, 5210 = 4,5% sprzedaży (marketing efektywnościowy),
* centrala: 5410 wynagrodzenia (stałe miesięcznie, podwyżka z początkiem każdego RF, premia roczna w czerwcu), 5420 IT i licencje (głównie w `HQ-TEC`, stałe plus odnowienia licencji w kwietniu i październiku), 5210 dla MPK marketingu marek (kampanie w marcu, wrześniu, listopadzie i grudniu), 5310 dla działu Łańcuch dostaw 2,8% sprzedaży sklepów grupy, 5910 pozostałe, 6010 amortyzacja systemów i biura; łącznie koszty centrali od 9% do 12% sprzedaży grupy,
* EBITDA grupy w RF 2025/26 w przedziale 12% do 22% sprzedaży.

Reguły BUD: budżet roku N liczony od ACT roku N-1 (uproszczenie) z założeniami: wzrost sklepów AUR +3%, VEN +6%, LUM +4%, KRO +2%, e-commerce +13%; otwarcia według dat planowanych; indeksacja czynszów +3%; koszt zamówienia e-commerce +3%; normalna pogoda. Budżet jest gładki (bez szumu dziennego), miesięczny rozkład według sezonowości. Dla RF 2024/25 bazą jest ACT RF 2023/24.

Reguły FC (RF 2026/27, grudzień do marca): BUD skorygowany o znane trendy (Kroko 9% poniżej BUD, sklepy Vento DE w rozruchu według rzeczywistych dat otwarcia, czynsze Aurea AT według nowej stawki, koszt zamówienia e-commerce DE według nowej stawki, pozostałe bez zmian poza kosztami zależnymi od sprzedaży).

### fakt_kursy_walut

Ziarno: miesiąc × waluta (EUR, SEK, DKK), 2023-04 do 2026-12. Kolumny: `miesiac` (date), `waluta` (string), `kurs_sredni_pln` (float64, PLN za 1 jednostkę). Błądzenie losowe wokół EUR 4,30, SEK 0,392, DKK 0,577. Informacyjnie, kwoty w faktach są już w PLN.

### agg_sprzedaz_mies

Agregat dla planowania. Ziarno: miesiąc × marka × kraj × kanał (Sklep, E-commerce) × scenariusz. Źródło: konta 4010 i 4510 z `fakt_pnl` (ACT, BUD, FC). Kolumny: `miesiac`, `marka_kod`, `kraj_kod`, `kanal`, `scenariusz_kod`, `sprzedaz_netto_pln`, `koszt_wlasny_pln`.

### plan_kalendarz

Miesięczny kalendarz dla modelu `SM_Planowanie`. Ziarno: miesiąc, od 2023-04-01 do 2028-03-01 włącznie, dokładnie 60 wierszy. Wszystkie wartości tekstowe są czystym ASCII. Daty i atrybuty finansowe są zgodne z `dim_data` dla pierwszego dnia miesiąca.

| Kolumna | Typ | Opis |
|---|---|---|
| miesiac | date32 | Pierwszy dzień miesiąca, unikalny klucz |
| rok_finansowy | string | Np. `2026/27`, RF od kwietnia do marca |
| rok_finansowy_nr | int64 | Np. `2026`, rok rozpoczęcia RF |
| kwartal | string | `1Q`, `2Q`, `3Q`, `4Q`; 1Q kwiecień do czerwca |
| kwartal_pelny | string | Np. `3Q 2026/27` |
| kwartal_sort | int64 | rok_finansowy_nr × 10 + numer kwartału, np. `20263` |
| miesiac_fin_nr | int64 | 1 do 12, kwiecień = 1, marzec = 12 |
| miesiac_nazwa | string | Skróty ASCII w kolejności finansowej: `Kwi`, `Maj`, `Cze`, `Lip`, `Sie`, `Wrz`, `Paz`, `Lis`, `Gru`, `Sty`, `Lut`, `Mar` |
| okres | string | `RRRR-MM`, np. `2026-12` |
| rok | int64 | Rok kalendarzowy |
| miesiac_nr | int64 | Numer miesiąca kalendarzowego 1 do 12 |
| czy_miesiac_zamkniety | bool | Jak w dim_data, do listopada 2026 włącznie |

Wyjście: `dane/parquet/plan_kalendarz.parquet` z datą `date32` i `dane/csv/plan_kalendarz.csv`. Każdy miesiąc z `agg_sprzedaz_mies` istnieje w `plan_kalendarz`.

### ref_plan_2027_28_rozklad

Klucz odpowiedzi do demonstracji rozbicia celu rocznego na miesiące. Ziarno: marka × kraj × kanał × miesiąc RF 2027/28 (2027-04-01 do 2028-03-01), 46 kombinacji.

| Kolumna | Typ | Opis |
|---|---|---|
| marka_kod, kraj_kod, kanal | string | |
| miesiac | date | |
| cel_roczny_pln | float64 | Z pliku celów |
| udzial_ly | float64 | Udział miesiąca w sprzedaży ACT RF 2025/26 tej kombinacji |
| plan_ly_pln | float64 | cel_roczny_pln × udzial_ly |
| udzial_sr2 | float64 | Średni udział z RF 2024/25 i 2025/26 |
| plan_sr2_pln | float64 | cel_roczny_pln × udzial_sr2 |

## Wejścia Excel (katalog dane/excel)

`cele_sprzedazy_2027_28.xlsx`, arkusz `Cele`: marka, kraj, kanał, sprzedaż FC RF 2026/27 (PLN), wzrost docelowy %, cel RF 2027/28 (PLN, zaokrąglony do tysięcy). Wzrost: AUR +5%, VEN +10%, LUM +8%, KRO -3%; dla kanału e-commerce dodatkowo +5 pp. Arkusz `Opis` z krótką instrukcją.

`zalozenia_plan_2027_28.xlsx`: arkusz `Zalozenia` (marka × kraj, 24 wiersze: wzrost LFL %, docelowa marża brutto %, indeksacja czynszów %, wzrost płac %), arkusz `Nowe_sklepy` (sklepy o statusie Planowany: mpk_id, marka, kraj, miasto, m2, planowany miesiąc otwarcia), arkusz `Opis`.

`budzet_opex_centrala_2027_28_szablon.xlsx`: przykład ręcznego obiegu budżetu w arkuszu. Arkusz `Budzet` z wierszami MPK centrali × konto (tylko konta używane przez dane MPK, 45 wierszy), kolumnami: ACT RF 2025/26 (suma), FC RF 2026/27 (suma), 12 pustych kolumn miesięcy RF 2027/28 do wypełnienia, suma formułą Excela, komentarz. Arkusz `Instrukcja`. Formatowanie czytelne (nagłówki, szerokości kolumn, format liczb z separatorem tysięcy).

`budzet_opex_centrala_2027_28_import.xlsx`: osobny plik do importu w PowerTable. Pierwszy arkusz `Import` zawiera płaską tabelę od A1, jeden wiersz nagłówka, bez scalonych komórek, formuł i pustych wierszy. Ziarno i wiersze są takie same jak w szablonie, MPK centrali × konto. Nagłówki są ASCII, mają małe litery, cyfry i podkreślniki oraz zaczynają się od litery. Wartości tekstowe mogą mieć polskie znaki.

Kolejność kolumn:

`mpk_id`, `mpk_nazwa`, `konto_id`, `konto_nazwa`, `act_2025_26_pln`, `fc_2026_27_pln`, `m01_2027_04`, `m02_2027_05`, `m03_2027_06`, `m04_2027_07`, `m05_2027_08`, `m06_2027_09`, `m07_2027_10`, `m08_2027_11`, `m09_2027_12`, `m10_2028_01`, `m11_2028_02`, `m12_2028_03`, `komentarz`.

Każdy miesiąc zawiera `fc_2026_27_pln / 12 × (1 + indeksacja)`, zaokrąglone do 100 PLN. Indeksacja wynosi 6% dla konta 5410 oraz 3% dla pozostałych. Wyłącznie w wierszu `HQ-TEC` × `5420` do `m07_2027_10` dodaje się jednorazowo 180 000 PLN i komentarz o odnowieniu licencji. Suma 12 miesięcy tego wiersza to 12 razy zaokrąglona baza plus 180 000 PLN. Pozostałe wiersze konta 5420 nie mają skoku w październiku, a pozostałe komentarze są puste. Nie ma kolumny sumy ani żadnych formuł.

Drugi arkusz `Opis` ma nagłówek i trzy wiersze: dane syntetyczne, znaczenie kolumn i sposób wyliczenia projektu. Formatowanie pliku ogranicza się do pogrubionych nagłówków i liczb z separatorem tysięcy.

## Historie zaszyte w danych

Każda historia jest wykrywalna zapytaniem i sprawdzana testem. Przyczyny są założeniami generatora.

1. Vento Niemcy: 4 nowe sklepy planowane na maj i czerwiec 2026, faktycznie otwarte w sierpniu i wrześniu 2026 (opóźnienie 3 miesiące). BUD zakłada daty planowane. Sprzedaż VEN DE w 1H 2026/27 (kwiecień do września 2026) ACT względem BUD między -20% a -9%.
2. Aurea Austria: od kwietnia 2026 czynsze wyższe o 15%, budżet zakładał +3%. Konto 5120 dla sklepów AUR AT w RF 2026/27 (kwiecień do listopada) ACT względem BUD między +9% a +14%.
3. E-commerce Niemcy: od października 2026 koszt zamówienia wyższy o 18%. Konto 5220 dla MPK `EC-*-DE` w październiku i listopadzie 2026 ACT względem BUD między +15% a +30%.
4. Ciepły listopad 2026: sprzedaż odzieży wierzchniej w listopadzie 2026 względem listopada 2025 między -35% a -20%; sprzedaż marek względem trendu niższa o około 5% (AUR, KRO), 8% (VEN) i 1% (LUM); marża brutto w listopadzie 2026 poza Black Friday o 1 pp niższa.
5. Kroko: trend sklepów -2% w RF 2025/26 i -7% w RF 2026/27, do tego cztery zamknięcia. Sprzedaż sklepów KRO od kwietnia do listopada 2026 względem tego samego okresu 2025 między -18% a -9%.
6. Black Friday 2025 (28 listopada 2025) to dzień o najwyższej sprzedaży grupy w listopadzie 2025, a dla e-commerce dzień o najwyższej sprzedaży w RF 2025/26.
7. Rosnący udział e-commerce: RF 2023/24 między 16% a 20%, RF 2026/27 (kwiecień do listopada) między 21% a 26%, wzrost w każdym kolejnym RF.
8. Grudzień to miesiąc o najwyższej sprzedaży w każdym pełnym RF.

## Pytania testowe agenta (klucz odpowiedzi)

Generator liczy odpowiedzi i zapisuje je w `dane/oczekiwane_odpowiedzi.md` (pytanie, wynik liczbowy, krótkie uzasadnienie, sposób liczenia) oraz w CSV. Kwoty w PLN zaokrąglone do tysięcy, procenty do 0,1 pp.

1. Jaka była sprzedaż netto grupy w 2Q 2026/27 i jak wypadła względem budżetu?
2. Która marka ma największe procentowe odchylenie sprzedaży od budżetu narastająco w RF 2026/27 (kwiecień do listopada)? Podaj odchylenia wszystkich marek w PLN i %.
3. Dlaczego Vento w Niemczech jest poniżej budżetu w 1H 2026/27? (Oczekiwane: odchylenie sprzedaży i lista 4 sklepów z datą planowaną i rzeczywistą otwarcia.)
4. Które 5 sklepów ma największe przekroczenie kosztów czynszu względem budżetu w RF 2026/27 (kwiecień do listopada)?
5. Jak zmieniła się sprzedaż odzieży wierzchniej w listopadzie 2026 r/r, w podziale na marki?
6. Jak zmieniał się udział e-commerce w sprzedaży grupy w kolejnych latach finansowych?
7. Ile wyniosła sprzedaż grupy w Black Friday 2025 i ile to razy więcej niż średnia z pozostałych piątków listopada 2025?
8. Jaki był koszt logistyki e-commerce na jedno zamówienie w Niemczech w październiku i listopadzie 2026 w porównaniu z budżetem? (Koszt na zamówienie ACT = konto 5220 ACT / liczba zamówień z faktu dziennego; budżetowy = konto 5220 BUD / liczba zamówień ACT.)
9. Jaka jest prognoza EBITDA grupy na RF 2026/27 (FC 8+4) i jak wypada względem budżetu?
10. Które 5 sklepów Kroko ma najniższą marżę brutto % w RF 2026/27 (kwiecień do listopada)?
11. Jaka była dynamika sprzedaży LFL Kroko w 2Q 2026/27? (Sklepy LFL to sklepy z `lfl_od` <= 2026-07-01 i bez zamknięcia przed 2026-10-01; porównanie lipca do września 2026 z lipcem do września 2025.)
12. Ile wyniosły koszty IT i licencji (konto 5420) w RF 2025/26 w porównaniu z RF 2024/25?
13. Jaka będzie sprzedaż w 2029 roku? (Oczekiwane: brak danych, agent nie powinien zgadywać.)
14. Jaka jest sprzedaż w bieżącym kwartale? (Oczekiwane: 3Q 2026/27, czyli październik do grudnia 2026; P&L ACT tylko za październik i listopad, grudzień tylko z danych dziennych do 08.12.2026; podać oba składniki osobno.)

## Walidacja

`python generator/validate.py` sprawdza: integralność referencyjną wszystkich kluczy, brak ujemnych kwot, zgodność 4010 i 4510 ACT z sumami dziennymi, zgodność kategorii z danymi dziennymi, brak wierszy sklepów PL w niedziele niehandlowe i święta, kompletność BUD i FC, wszystkie historie z sekcji wyżej z podanymi przedziałami, sprzedaż grupy RF 2025/26 między 0,7 a 1,1 mld PLN, EBITDA grupy RF 2025/26 między 12% a 22%. Kończy się kodem 0 tylko wtedy, gdy wszystkie testy przechodzą, i wypisuje tabelę wyników.

Dla `plan_kalendarz` walidacja obejmuje 60 miesięcy w zadanym zakresie, unikalność klucza, ASCII wszystkich wartości tekstowych, pokrycie miesięcy `agg_sprzedaz_mies` oraz zgodność atrybutów z pierwszym dniem miesiąca w `dim_data`.

Plik importowy PowerTable jest sprawdzany pod względem nagłówków, układu arkuszy, braku formuł, scalonych komórek i pustych wierszy, kompletności wartości liczbowych, zgodności kluczy i liczby wierszy z szablonem oraz miesięcznej indeksacji. Testy sprawdzają dopłatę 180 000 PLN w październiku wyłącznie dla `HQ-TEC` × `5420`, jeden niepusty komentarz przy tym wierszu oraz brak skoku październikowego w pozostałych wierszach konta 5420.
