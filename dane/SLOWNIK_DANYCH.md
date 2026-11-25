# Słownik danych syntetycznych

Dane w pełni syntetyczne, wymyślone na potrzeby warsztatu. Nie odzwierciedlają wyników żadnej firmy. Skala jest umowna.

Zestaw służy do ćwiczeń Microsoft Fabric: analizy sprzedaży, odchyleń rachunku wyników, planowania i oceny odpowiedzi agenta. Firma i marki są fikcyjne, prawdziwe są tylko nazwy krajów i miast; liczby, MPK, otwarcia oraz historie biznesowe zostały wymyślone. Źródłem wartości są jawne reguły w generatorze, a nie dokumenty klienta.

## Zakres i kalendarz finansowy

Data stanu to 2026-12-09. Sprzedaż dzienna obejmuje 2023-04-01 do 2026-12-08. P&L ACT i kategorie obejmują zamknięte miesiące od kwietnia 2023 do listopada 2026. BUD obejmuje pełne RF 2024/25, 2025/26 i 2026/27. FC 8+4 dotyczy RF 2026/27. Kalendarz kończy się 31.03.2028.

RF zaczyna się 1 kwietnia i kończy 31 marca. RF 2026/27 to 01.04.2026 do 31.03.2027; rok_finansowy_nr ma wtedy wartość 2026. Kwiecień jest miesiącem finansowym 1, marzec 12. 1Q obejmuje kwiecień do czerwca, 2Q lipiec do września, 3Q październik do grudnia, 4Q styczeń do marca. 1H to kwiecień do września, 2H październik do marca. kwartal_finansowy_sort = rok_finansowy_nr × 10 + numer kwartału, np. 20263.

Polskie święta obejmują daty stałe oraz Wielkanoc, Poniedziałek Wielkanocny, Zielone Świątki i Boże Ciało. Od 2025 wolny jest także 24 grudnia. Uproszczone niedziele handlowe to ostatnia niedziela stycznia, kwietnia, czerwca i sierpnia, niedziela przed Wielkanocą oraz dwie niedziele przed 25 grudnia w latach 2023 i 2024, a od 2025 trzy niedziele przed 24 grudnia. Święto ma pierwszeństwo przed niedzielą handlową. Literalne uproszczenie oznacza handlowy 24.12.2023, z połową zwykłej wagi sprzedaży. Nie jest to kalendarz do celów prawnych. Poza Polską sklepy są zamknięte tylko 1 stycznia, 25 grudnia i w Wielkanoc. E-commerce sprzedaje codziennie.

## Konwencje i rachunek wyników

Parquet używa date32, string, int64, float64 i bool. Wszystkie kwoty są w PLN, bez VAT, zaokrąglone do groszy. Kursy mają sześć miejsc dziesiętnych, a udziały planu zachowują precyzję float64. Puste daty i powierzchnie są nullami, nie tekstem. Puste miasto, format i dział oznaczają atrybut, który nie dotyczy danego MPK. Numer konta jest tekstem. Kwoty kont są dodatnie; znak pochodzi z dim_konto.

Marża brutto = konto 4010 minus 4510. EBITDA = przychody minus koszt własny i wszystkie koszty operacyjne, bez konta 6010. EBIT = EBITDA minus amortyzacja. Tych sum nie ma jako dodatkowych wierszy faktu. Scenariuszy ACT, BUD i FC nie należy sumować ze sobą. Daty otwarcia i zamknięcia są włącznie: zamknięcie jest ostatnim dniem działalności.

LFL zaczyna się po 12 pełnych miesiącach. Dla otwarcia pierwszego dnia miesiąca jest to pierwszy dzień tego samego miesiąca rok później. Dla otwarcia w trakcie miesiąca jest to pierwszy dzień następnego miesiąca rok później. Kohortę porównuje się w obu latach na tym samym zbiorze MPK. Null lfl_od oznacza MPK nieporównywalne.

## Tabele

| Tabela | Liczba wierszy | Ziarno |
| --- | --- | --- |
| dim_data | 1 827 | data |
| dim_marka | 5 | marka_kod |
| dim_kraj | 6 | kraj_kod |
| dim_kategoria | 9 | kategoria_kod |
| dim_scenariusz | 3 | scenariusz_kod |
| dim_konto | 13 | konto_id |
| dim_mpk | 181 | mpk_id |
| fakt_sprzedaz_dzienna | 192 841 | data × mpk_id |
| fakt_sprzedaz_kategorie_mies | 11 616 | miesiac × marka_kod × kraj_kod × kanal × kategoria_kod |
| fakt_pnl | 100 195 | miesiac × mpk_id × konto_id × scenariusz_kod |
| fakt_kursy_walut | 135 | miesiac × waluta |
| agg_sprzedaz_mies | 4 232 | miesiac × marka_kod × kraj_kod × kanal × scenariusz_kod |
| plan_kalendarz | 60 | miesiac |
| ref_plan_2027_28_rozklad | 552 | marka_kod × kraj_kod × kanal × miesiac |

### dim_data

Pełny kalendarz dzienny, finansowy i handlowy.

Ziarno: data. Liczba wierszy: 1 827.

| Kolumna | Typ | Opis |
| --- | --- | --- |
| data | date32 | Dzień, klucz wymiaru. |
| rok | int64 | Rok kalendarzowy. |
| miesiac | int64 | Numer miesiąca kalendarzowego, od 1 do 12. |
| miesiac_nazwa | string | Polska nazwa miesiąca. |
| miesiac_skrot | string | Skrót polskiej nazwy miesiąca. |
| miesiac_poczatek | date32 | Pierwszy dzień miesiąca. |
| okres_rrrrmm | int64 | Okres w postaci RRRRMM. |
| dzien_tygodnia_nr | int64 | Od 1 dla poniedziałku do 7 dla niedzieli. |
| dzien_tygodnia_nazwa | string | Polska nazwa dnia tygodnia. |
| tydzien_iso | int64 | Numer tygodnia ISO. |
| rok_finansowy | string | Etykieta roku finansowego, np. 2026/27. |
| rok_finansowy_nr | int64 | Rok kalendarzowy rozpoczęcia roku finansowego. |
| kwartal_finansowy | string | 1Q, 2Q, 3Q albo 4Q. |
| kwartal_finansowy_pelny | string | Kwartał wraz z rokiem, np. 3Q 2026/27. |
| kwartal_finansowy_sort | int64 | Rok rozpoczęcia RF razy 10 plus numer kwartału, np. 20263. |
| polrocze_finansowe | string | 1H albo 2H. |
| miesiac_finansowy_nr | int64 | Kwiecień ma numer 1, marzec numer 12. |
| czy_swieto_pl | bool | Święto ustawowo wolne w Polsce według reguł generatora. |
| nazwa_swieta | string | Nazwa święta albo null. |
| czy_niedziela_handlowa_pl | bool | Niedziela handlowa według uproszczenia w SPEC.md. |
| czy_dzien_handlowy_pl | bool | Dzień otwarcia sklepów w Polsce. |
| czy_black_friday | bool | Ostatni piątek listopada. |
| czy_miesiac_zamkniety | bool | Miesiąc do listopada 2026 włącznie. |

Relacje i klucze: Klucz data jest stroną jeden relacji do dat faktów. Fakt miesięczny łączy się przez miesiac = data, nie przez nieunikalny miesiac_poczatek.

### dim_marka

Cztery marki fikcyjnej sieci i techniczny wiersz GRP dla centrali.

Ziarno: marka_kod. Liczba wierszy: 5.

| Kolumna | Typ | Opis |
| --- | --- | --- |
| marka_kod | string | AUR, VEN, LUM, KRO albo techniczny kod GRP. |
| marka_nazwa | string | Nazwa marki. |
| grupa_docelowa | string | Umowny segment odbiorców. |
| kolejnosc | int64 | Kolejność prezentacji. |

Relacje i klucze: marka_kod łączy się z dim_mpk oraz faktami zagregowanymi.

### dim_kraj

Sześć rynków wraz z walutami informacyjnymi.

Ziarno: kraj_kod. Liczba wierszy: 6.

| Kolumna | Typ | Opis |
| --- | --- | --- |
| kraj_kod | string | Dwuliterowy kod kraju. |
| kraj_nazwa | string | Polska nazwa kraju. |
| waluta_lokalna | string | Kod waluty lokalnej. |
| region | string | Region geograficzny. |

Relacje i klucze: kraj_kod łączy się z dim_mpk oraz faktami zagregowanymi.

### dim_kategoria

Dziewięć kategorii asortymentowych.

Ziarno: kategoria_kod. Liczba wierszy: 9.

| Kolumna | Typ | Opis |
| --- | --- | --- |
| kategoria_kod | string | Kod kategorii asortymentowej. |
| kategoria_nazwa | string | Nazwa kategorii. |
| grupa | string | Grupa asortymentu. |

Relacje i klucze: kategoria_kod łączy się z faktem kategorii.

### dim_scenariusz

Znaczenie wykonania, budżetu i prognozy.

Ziarno: scenariusz_kod. Liczba wierszy: 3.

| Kolumna | Typ | Opis |
| --- | --- | --- |
| scenariusz_kod | string | ACT, BUD albo FC. |
| scenariusz_nazwa | string | Polska nazwa scenariusza. |
| opis | string | Zakres i znaczenie scenariusza. |
| kolejnosc | int64 | Kolejność prezentacji. |

Relacje i klucze: scenariusz_kod łączy się z P&L i agregatem sprzedaży.

### dim_konto

Konta rachunku wyników i znaki używane w miarach.

Ziarno: konto_id. Liczba wierszy: 13.

| Kolumna | Typ | Opis |
| --- | --- | --- |
| konto_id | string | Tekstowy identyfikator konta, np. 4010. |
| konto_nazwa | string | Nazwa pozycji rachunku wyników. |
| sekcja | string | Sekcja rachunku wyników. |
| grupa_kosztow | string | Grupa analityczna kosztu lub przychodu. |
| znak | int64 | 1 dla przychodów, -1 dla kosztów. |
| kolejnosc | int64 | Kolejność prezentacji konta. |

Relacje i klucze: konto_id łączy się z fakt_pnl.

### dim_mpk

Historia sklepów, kanały internetowe i działy centrali.

Ziarno: mpk_id. Liczba wierszy: 181.

| Kolumna | Typ | Opis |
| --- | --- | --- |
| mpk_id | string | Klucz sklepu, kanału e-commerce lub działu centrali. |
| mpk_nazwa | string | Czytelna nazwa MPK. |
| typ_mpk | string | Sklep, E-commerce albo Centrala. |
| kanal | string | Kanał sprzedaży lub Centrala. |
| marka_kod | string | Kod marki; GRP oznacza centralę bez przypisania do marki. |
| kraj_kod | string | Kod kraju; centrala ma PL. |
| miasto | string | Miasto sklepu; pusty tekst dla innych MPK. |
| format_sklepu | string | Format sklepu; pusty tekst dla innych MPK. |
| powierzchnia_m2 | int64 | Powierzchnia sprzedaży; null poza sklepami. |
| dzial_centrali | string | Nazwa działu; pusty tekst poza centralą. |
| data_otwarcia_plan | date32 | Planowany pierwszy dzień działalności. |
| data_otwarcia | date32 | Rzeczywisty pierwszy dzień; null dla sklepów planowanych. |
| data_zamkniecia | date32 | Ostatni dzień działalności albo null. |
| status | string | Status na 08.12.2026: Aktywny, Zamknięty albo Planowany. |
| lfl_od | date32 | Pierwszy miesiąc po 12 pełnych miesiącach działalności; null poza otwartymi sklepami. |

Relacje i klucze: mpk_id łączy się z P&L i faktem dziennym; kraj_kod z dim_kraj, marka_kod z dim_marka. GRP to techniczny wiersz wymiaru dla sześciu działów centrali, nie marka handlowa.

### fakt_sprzedaz_dzienna

Sprzedaż tylko w dniach rzeczywistej działalności, także niezamknięty grudzień.

Ziarno: data × mpk_id. Liczba wierszy: 192 841.

| Kolumna | Typ | Opis |
| --- | --- | --- |
| data | date32 | Dzień sprzedaży. |
| mpk_id | string | Sklep lub e-commerce. |
| sprzedaz_netto_pln | float64 | Sprzedaż netto bez VAT w PLN. |
| koszt_wlasny_pln | float64 | Koszt sprzedanych towarów w PLN. |
| liczba_paragonow | int64 | Liczba paragonów lub zamówień e-commerce. |
| liczba_sztuk | int64 | Liczba sprzedanych sztuk. |

Relacje i klucze: data do dim_data.data; mpk_id do dim_mpk.mpk_id.

### fakt_sprzedaz_kategorie_mies

Podział zamkniętych miesięcy na asortyment, uzgodniony do sprzedaży dziennej.

Ziarno: miesiac × marka_kod × kraj_kod × kanal × kategoria_kod. Liczba wierszy: 11 616.

| Kolumna | Typ | Opis |
| --- | --- | --- |
| miesiac | date32 | Pierwszy dzień zamkniętego miesiąca. |
| marka_kod | string | Kod marki. |
| kraj_kod | string | Kod kraju. |
| kanal | string | Sklep albo E-commerce. |
| kategoria_kod | string | Kod kategorii. |
| sprzedaz_netto_pln | float64 | Sprzedaż kategorii w PLN. |
| koszt_wlasny_pln | float64 | Koszt towarów kategorii w PLN. |
| liczba_sztuk | int64 | Liczba sztuk przypisana do kategorii. |

Relacje i klucze: miesiac do dim_data.data; marka_kod, kraj_kod i kategoria_kod do odpowiednich wymiarów. Kanal jest atrybutem, nie oddzielnym wymiarem.

### fakt_pnl

Rachunek wyników w scenariuszach ACT, BUD i FC, bez wyliczonych sum EBITDA i EBIT.

Ziarno: miesiac × mpk_id × konto_id × scenariusz_kod. Liczba wierszy: 100 195.

| Kolumna | Typ | Opis |
| --- | --- | --- |
| miesiac | date32 | Pierwszy dzień miesiąca. |
| mpk_id | string | Klucz miejsca powstawania kosztów. |
| konto_id | string | Tekstowy numer konta. |
| scenariusz_kod | string | ACT, BUD albo FC. |
| kwota_pln | float64 | Dodatnia kwota; znak wynika z dim_konto. |

Relacje i klucze: miesiac do dim_data.data; mpk_id do dim_mpk; konto_id do dim_konto; scenariusz_kod do dim_scenariusz.

### fakt_kursy_walut

Informacyjne syntetyczne kursy, nie służą do ponownego przeliczania faktów.

Ziarno: miesiac × waluta. Liczba wierszy: 135.

| Kolumna | Typ | Opis |
| --- | --- | --- |
| miesiac | date32 | Pierwszy dzień miesiąca. |
| waluta | string | EUR, SEK albo DKK. |
| kurs_sredni_pln | float64 | PLN za jedną jednostkę waluty, sześć miejsc dziesiętnych. |

Relacje i klucze: miesiac do dim_data.data; waluta to domena kodów walut z dim_kraj, bez relacji jeden do wielu po nieunikalnej walucie kraju.

### agg_sprzedaz_mies

Uzgodniony do P&L agregat przychodów i kosztu własnego do planowania.

Ziarno: miesiac × marka_kod × kraj_kod × kanal × scenariusz_kod. Liczba wierszy: 4 232.

| Kolumna | Typ | Opis |
| --- | --- | --- |
| miesiac | date32 | Pierwszy dzień miesiąca. |
| marka_kod | string | Kod marki. |
| kraj_kod | string | Kod kraju. |
| kanal | string | Sklep albo E-commerce. |
| scenariusz_kod | string | ACT, BUD albo FC. |
| sprzedaz_netto_pln | float64 | Suma konta 4010 w PLN. |
| koszt_wlasny_pln | float64 | Suma konta 4510 w PLN. |

Relacje i klucze: miesiac do dim_data.data; marka_kod, kraj_kod i scenariusz_kod do odpowiednich wymiarów.

### plan_kalendarz

Miesięczny kalendarz dla SM_Planowanie: 60 miesięcy od kwietnia 2023 do marca 2028. Wszystkie wartości tekstowe są czystym ASCII; atrybuty finansowe pochodzą z dim_data.

Ziarno: miesiac. Liczba wierszy: 60.

| Kolumna | Typ | Opis |
| --- | --- | --- |
| miesiac | date32 | Pierwszy dzień miesiąca, unikalny klucz. |
| rok_finansowy | string | Etykieta RF od kwietnia do marca, np. 2026/27; ASCII. |
| rok_finansowy_nr | int64 | Rok kalendarzowy rozpoczęcia RF. |
| kwartal | string | 1Q, 2Q, 3Q albo 4Q; ASCII. |
| kwartal_pelny | string | Kwartał wraz z RF, np. 3Q 2026/27; ASCII. |
| kwartal_sort | int64 | Rok rozpoczęcia RF razy 10 plus numer kwartału, np. 20263. |
| miesiac_fin_nr | int64 | Kwiecień ma numer 1, marzec numer 12. |
| miesiac_nazwa | string | Skrót ASCII: Kwi, Maj, Cze, Lip, Sie, Wrz, Paz, Lis, Gru, Sty, Lut, Mar. |
| okres | string | Miesiąc kalendarzowy RRRR-MM, np. 2026-12; ASCII. |
| rok | int64 | Rok kalendarzowy. |
| miesiac_nr | int64 | Numer miesiąca kalendarzowego od 1 do 12. |
| czy_miesiac_zamkniety | bool | Zamknięty do listopada 2026 włącznie, zgodnie z dim_data. |

Relacje i klucze: miesiac jest stroną jeden relacji do agg_sprzedaz_mies.miesiac i ref_plan_2027_28_rozklad.miesiac w modelu planistycznym. Daty i atrybuty odpowiadają pierwszym dniom miesięcy w dim_data.

### ref_plan_2027_28_rozklad

Referencyjne rozłożenie celu rocznego na miesiące dwiema metodami.

Ziarno: marka_kod × kraj_kod × kanal × miesiac. Liczba wierszy: 552.

| Kolumna | Typ | Opis |
| --- | --- | --- |
| marka_kod | string | Kod marki. |
| kraj_kod | string | Kod kraju. |
| kanal | string | Sklep albo E-commerce. |
| miesiac | date32 | Pierwszy dzień miesiąca RF 2027/28. |
| cel_roczny_pln | float64 | Cel z arkusza Cele; powtórzony w 12 miesiącach, nie sumować po miesiącach. |
| udzial_ly | float64 | Udział miesiąca w ACT RF 2025/26. |
| plan_ly_pln | float64 | Cel roczny razy udział LY, zaokrąglony do groszy. |
| udzial_sr2 | float64 | Średnia udziałów ACT RF 2024/25 i 2025/26. |
| plan_sr2_pln | float64 | Cel roczny razy średni udział, zaokrąglony do groszy. |

Relacje i klucze: miesiac do dim_data.data; marka_kod i kraj_kod do wymiarów. Cel roczny odpowiada jednej kombinacji w arkuszu Cele.

## Historie do wykorzystania przez prowadzącego

| Historia | Mechanizm | Wynik w zestawie | Oczekiwany przedział |
| --- | --- | --- | --- |
| Vento DE | 4 otwarcia przesunięte z maja i czerwca na sierpień i wrzesień 2026. | 1H ACT/BUD: -14,4% | Od -20% do -9% |
| Aurea AT | Czynsze od kwietnia 2026 rosną o 15%; BUD zakłada 3%. | +11,7% | Od +9% do +14% |
| E-commerce DE | Od października 2026 stawka za zamówienie w Niemczech wyższa o 18%. | Koszt października i listopada ACT/BUD: +23,1% | Od +15% do +30% w każdym miesiącu |
| Ciepły listopad | Mnożnik sprzedaży od 0,92 do 0,99 zależnie od marki; mniejszy udział OW i marża niższa o 1 pp. | OW r/r: -27,9% | Od -35% do -20% |
| Kroko | Trend sklepów w RF 2025/26: -2%, w RF 2026/27: -7%; także cztery zamknięcia. | Sklepy, kwiecień do listopada r/r: -13,8% | Od -18% do -9% |
| Black Friday 2025 | Sklepy razy 2, e-commerce razy 3; wsparcie tygodnia promocji. | 7 388 000 PLN, 2,10 razy pozostałe piątki | Najwyższy dzień grupy w listopadzie i e-commerce w RF 2025/26 |
| Udział e-commerce | Trend roczny 14%, dla Lumi 28%, baza RF 2023/24 skalibrowana do 18%. | 18,0% do 23,1% | Od 16% do 20% w RF 2023/24, od 21% do 26% w RF 2026/27 |
| Grudzień | Sezonowość, prezenty i ostatnie dwa tygodnie przed Wigilią. | Najwyższa miesięczna sprzedaż każdego pełnego RF | RF 2023/24, 2024/25, 2025/26 |

Wyniki powyżej są obliczone z tabel. Przyczyny są założeniami własnymi generatora, nie udokumentowanymi zdarzeniami żadnej firmy. Szczegółowy klucz zawiera 14 pytań w oczekiwane_odpowiedzi.md; sam wynik liczbowy nie zastępuje poprawnego filtra czasu i scenariusza.

## Wejścia Excel

cele_sprzedazy_2027_28.xlsx zawiera arkusze Cele i Opis. Cel roczny wynika z FC, wzrostu marki i dodatkowych 5 pp dla e-commerce, po zaokrągleniu do tysięcy. zalozenia_plan_2027_28.xlsx zawiera 24 kombinacji marki i kraju oraz 7 planowanych sklepów. budzet_opex_centrala_2027_28_szablon.xlsx pokazuje wyłącznie konta używane przez centralę, sumy ACT i FC, 12 pustych miesięcy, formuły SUM oraz miejsce na komentarz. Procenty w Excelu są ułamkami. Puste miesiące nie są zerowym budżetem.

budzet_opex_centrala_2027_28_import.xlsx jest oddzielnym wejściem do PowerTable. Pierwszy arkusz Import ma te same MPK i konta co szablon, jeden nagłówek w A1, 19 kolumn i wyłącznie zapisane wartości, bez formuł i pustych wierszy. Nazwy kolumn to mpk_id, mpk_nazwa, konto_id, konto_nazwa, act_2025_26_pln, fc_2026_27_pln, m01_2027_04 do m12_2028_03 oraz komentarz; są ASCII i zaczynają się od litery. Polskie znaki w danych tekstowych pozostają dozwolone.

Projekt miesięczny w pliku importowym = FC RF 2026/27 / 12 × (1 + indeksacja), zaokrąglony do 100 PLN. Indeksacja wynosi 6,0% dla konta 5410 i 3,0% dla pozostałych. Wyłącznie wiersz HQ-TEC, konto 5420, zawiera dodatkowe 180 000 PLN w październiku (m07_2027_10) oraz komentarz o odnowieniu licencji. Łączna dopłata w całym pliku wynosi 180 000 PLN. Pozostałe wiersze konta 5420 zachowują w październiku zwykłą bazę miesięczną. Wszystkie pozostałe komentarze są puste. Arkusz Opis wyjaśnia syntetyczny charakter danych, znaczenie kolumn i metodę obliczeń. Ten roboczy projekt nie jest nowym scenariuszem fakt_pnl.

## Uproszczenia i znane ograniczenia

Budżet RF N opiera się na ACT RF N poprzedniego roku. Roczna baza każdego MPK jest oczyszczana o długość działalności i rozruch, a następnie rozkładana gładkim profilem sezonowości, dni tygodnia, promocji i kalendarza handlowego. Nie ma nowego szumu dziennego w BUD. Dla nowych sklepów bez bazy używa się średniej produktywności na m2 innych sklepów tej samej marki i kraju. To uproszczenie dydaktyczne, nie opis realnego procesu budżetowego.

BUD korzysta z planowanych dat otwarcia i znanych dat zamknięcia. Czynsze rosną w nim o 3%, koszt zamówienia o 3%, płace o 7%, media i pozostałe koszty stałe o 3%. FC od grudnia uwzględnia Kroko na poziomie 91,0% BUD, rzeczywisty rozruch Vento DE, nowe stawki czynszów Aurea AT i logistyki e-commerce DE. Pozostałe pozycje zachowują BUD; koszty bezpośrednio zależne od sprzedaży zmieniają się razem z nią.

Koszty stałe sklepów są proporcjonalne do dni działalności w miesiącu, a nie do dni handlowych. Rozruch jest liniowy od 70% do 100% w sześć miesięcy kalendarzowych. Cztery opóźnione sklepy mają mniejszy format niż typowy sklep Vento; pozostałe parametry ekonomiczne losowane są raz dla MPK.

Podział kategorii zachowuje dokładne sumy sprzedaży, kosztu i sztuk. Marża kategorii w danej kombinacji miesiąca, marki, kraju i kanału jest wspólna; nie modeluje się osobnej marży SKU. Reszty zaokrągleń przypisuje się największej kategorii. SR występuje tylko w VEN, BI głównie w LUM, a KRO sprzedaje wyłącznie obuwie i akcesoria.

Kursy są informacyjne; kwoty są już w PLN. Nie modeluje się konsolidacyjnych eliminacji, VAT, zwrotów, transakcji klienta, zapasów, cash flow, podatku dochodowego ani cen realnych licencji. GRP jest wyłącznie technicznym wierszem dim_marka dla centrali i nie trafia do sprzedaży ani plików celów. Nie tworzy się relacji po nazwach tekstowych ani po nieunikalnym początku miesiąca.

Rozkład celu rocznego jest demonstracją sezonowości, nie osobnym kompletnym planem nowych sklepów. Udział LY pochodzi z RF 2025/26; średnia dwuletnia to średnia udziałów, nie udział w dwuletniej sumie. Cel powtarza się w każdym z 12 miesięcy i nie jest addytywny po czasie. Zaokrąglenie miesięcznych planów do groszy może zmienić sumę roczną o kilka groszy.

## Luki i pytania do dalszych ćwiczeń

Brak rzeczywistego planu kont, zasad alokacji kosztów i uzgodnionego kalendarza poza Polską. Przed użyciem na danych rzeczywistych trzeba ustalić definicję LFL, obsługę zwrotów, kalendarze lokalne, datę zamknięcia miesiąca oraz role dostępu. Ten zestaw nie pozwala wnioskować o wynikach firmy, kosztach usług Azure ani uprawnieniach licencyjnych.
