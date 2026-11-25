# Microsoft Fabric dla kontrolingu i finansów. Scenariusz warsztatu

## O dokumencie

Dokument opisuje 90-minutowy warsztat z Microsoft Fabric dla zespołu kontrolingu i finansów fikcyjnej firmy Fabrikam Fashion, rozpisany na godziny 13:00-14:30. Zespół pracuje z budżetem w Excelu i z danymi rozproszonymi w kilku systemach, a rozdział 1 opisuje to dokładniej.

Warsztat ma dwie postacie. Wersja wdrożona to obszar roboczy Fabrikam Kontroling Warsztat w Fabric, na capacity Fabric (F SKU lub trial) w regionie West Europe. Lakehouse, trzy modele semantyczne, bazę SQL i obu agentów danych utworzyły skrypty zapisane w repozytorium, więc to samo środowisko da się zbudować w dowolnej dzierżawie Fabric. Wersją do przeklikania jest rozdział 4, w którym każdy krok ma ścieżkę kliknięć i liczbę kontrolną, jaką powinien pokazać ekran. Klika prowadzący, a uczestnicy decydują, jakie cele wpisać i o co zapytać agenta. Inny podział ról nie wchodzi w grę, bo Plan nie obsługuje kont gości Entra B2B [Learn].

Wszystkie dane są syntetyczne. Firma i jej marki są fikcyjne, prawdziwe są tylko nazwy krajów i miast, a sklepy, MPK, kwoty i zdarzenia wymyślił generator z repozytorium. Liczby z tego dokumentu nie opisują wyników żadnej firmy.

| Oznaczenie | Znaczenie |
|---|---|
| [Learn] | potwierdzone w dokumentacji Microsoft Learn, adresy w załączniku C |
| [test] | sprawdzone w środowisku warsztatowym przed warsztatem |
| [do próby] | do sprawdzenia tuż przed warsztatem, w chwili przygotowania dokumentu jeszcze niesprawdzone |
| [wniosek] | wniosek własny wyprowadzony z faktów, nie deklaracja Microsoft |
| [do ponownego przebiegu] | wynik z tenantu uzyskany na wcześniejszej wersji danych syntetycznych; po zmianie danych trzeba go zmierzyć od nowa |

## 1. Punkt wyjścia

Fabrikam Fashion to fikcyjna sieć odzieżowa z czterema markami, która działa w sześciu krajach. Scenariusz zakłada kłopoty typowe dla działu kontrolingu. Budżet kosztów powstaje w Excelu: kontroling rozsyła szablony do właścicieli MPK, a po powrocie przepisuje kwoty ręcznie. Cel sprzedaży trzeba rozłożyć na miesiące, kraje i kanały, najlepiej na gotowej bazie, którą później koryguje się w górę albo w dół.

Poza budżetem i rozkładem sprzedaży zespół potrzebuje symulacji i prognozy, chce przekazywać plan dalej i trzymać historię razem z planem w jednym miejscu. Chce też wiedzieć, na ile można polegać na odpowiedziach agentów AI i Microsoft 365 Copilot, co dalej z raportami Power BI wobec Fabric Apps i jakie licencje są potrzebne. Scenariusz przyjmuje, że dane źródłowe leżą w systemie ERP, w hurtowni danych i w arkuszach Excel. To założenia ćwiczenia, a nie opis istniejącej firmy.

Tabela łączy te wątki z miejscem w scenariuszu.

| Potrzeba | Gdzie na warsztacie | Co w Fabric | Status |
|---|---|---|---|
| Budżet kosztów rozsyłany w Excelu do MPK i przepisywany po powrocie | Blok 2, P2 | Plan, PowerTable: import Excela, edycja, audyt, zapis do bazy | GA [Learn] |
| Rozłożenie celu sprzedaży na miesiące, kraje i kanały | Blok 2, P1 | Plan, kolumna wejściowa z rozkładem proporcjonalnym do historii | GA [Learn] |
| Korekty bazy, z góry i z dołu | Blok 2, P1 | blokowanie gałęzi, wpis na niższym poziomie | GA [Learn] |
| Symulacje typu „co jeśli” | Blok 2, P3 | Simulate, Scenario | GA [Learn] |
| Prognoza do końca roku | Blok 2, P3 | Forecast, Predict | GA [Learn]; konfiguracja na kalendarzu finansowym [do próby] |
| Komentarze i akceptacja planu | Blok 2, P4 | komentarze, Approval | GA [Learn]; akceptacja [do próby] |
| Przekazanie planu dalej, do systemu planistycznego | Blok 2, P4 | writeback do Fabric SQL database | GA [Learn]; odbiór przez system Fabrikam Fashion to pytanie otwarte |
| Historia i plan w jednym miejscu | Blok 1 | lakehouse, model Direct Lake, Plan na modelu z tych samych danych | GA [Learn] |
| Excel jako wejście do procesu | Blok 1 i P2 | pliki w OneLake, Dataflow Gen2, import do PowerTable | GA [Learn] |
| Pytania do danych zadawane zwykłym językiem | Blok 3, A1 | Fabric data agent | GA [Learn] |
| Wiarygodność odpowiedzi AI | Blok 3, A2 | przygotowanie modelu, Prep data for AI | Prep data for AI w preview [Learn] |
| Agent dostępny w Microsoft 365 Copilot i Teams | Blok 3, A3 | Agent Store, Copilot Studio, MCP | zależnie od kanału, od preview do GA [Learn] |
| Raporty Power BI czy Fabric Apps | Blok 4 | raport z Copilotem, org apps, Fabric Apps | raporty i org apps GA, Fabric Apps preview [Learn] |
| „Czy to wymaga Premium?” | rozdział 5 | capacity F, licencje użytkowników, sesje Planu | [Learn] |

## 2. Agenda

| Godzina | Blok | Co pokazujemy | Z czym wychodzą uczestnicy |
|---|---|---|---|
| 13:00-13:10 | Otwarcie | cel spotkania, dane syntetyczne, wątki z rozdziału 1 | wiedzą, czego się spodziewać i czego nie będzie |
| 13:10-13:20 | Blok 1. Dane | lakehouse, zapytanie SQL, model Direct Lake, pliki Excel w OneLake | jedna kopia danych, te same liczby w każdym narzędziu |
| 13:20-13:50 | Blok 2. Planning | P1 rozkład celu sprzedaży (10 min), P2 budżet OPEX w PowerTable (8 min), P3 symulacja i prognoza (7 min), P4 komentarze, akceptacja i zapis (5 min) | obraz procesu budżetowego bez krążących Exceli |
| 13:50-14:15 | Blok 3. Agenci danych | A1 agent na przygotowanym modelu (10 min), A2 ten sam agent bez przygotowania (8 min), A3 kanały dostępu (7 min) | wiedzą, od czego zależy wiarygodność odpowiedzi |
| 14:15-14:25 | Blok 4. Raport, Copilot, aplikacje, Excel | Copilot w raporcie, org apps i Fabric Apps, Analyze in Excel | rozumieją, gdzie zostają Power BI i Excel |
| 14:25-14:30 | Blok 5. Dalsze kroki | warianty pilotażu, pytania do Fabrikam Fashion | mają na stole decyzję o następnym kroku |

Planning idzie zaraz po danych, bo to najważniejsza potrzeba z rozdziału 1.

## 3. Środowisko warsztatowe

### 3.1 Elementy obszaru roboczego

| Element | Typ | Zawartość | Stan |
|---|---|---|---|
| LH_Kontroling | lakehouse | 14 tabel Delta; w Files folder dane (parquet) i folder wejscia (5 plików Excel) | wdrożony skryptem [test] |
| SM_Kontroling | model semantyczny, Direct Lake | 11 tabel, 88 miar z opisami, instrukcje AI dla Copilota i agentów | wdrożony [test]; kontrole DAX na obecnych danych [do ponownego przebiegu] |
| SM_Kontroling_surowy | model semantyczny, Direct Lake | te same 11 tabel pod nazwami z lakehouse, bez miar, opisów, oznaczonej tabeli dat i instrukcji | wdrożony, służy do porównania w A2 [test] |
| SM_Planowanie | model semantyczny, Direct Lake | 4 tabele i 9 miar pod Plan, nazwy bez polskich znaków | wdrożony [test]; kontrole DAX [do ponownego przebiegu]; połączenie OAuth 2.0 bez SSO ustawione ręcznie (P0) [test] |
| SQLDB_Planowanie | Fabric SQL database | pusta baza na tabele PowerTable i writeback | wdrożona [test] |
| Agent_Kontroling | data agent | źródło SM_Kontroling, opublikowany | test 14 pytań [do ponownego przebiegu] |
| Agent_Kontroling_bez_przygotowania | data agent | źródło SM_Kontroling_surowy, opublikowany | test 14 pytań [do ponownego przebiegu] |
| Plan_Kontroling | Plan | arkusz Warsztat, opcjonalnie arkusz Prognoza (P3); arkusz PowerTable z budżetem OPEX powstaje w P2 | tworzony ręcznie przed warsztatem (P0) |
| Raport_Kontroling | raport Power BI | kilka wizualizacji na SM_Kontroling pod Copilota | tworzony ręcznie przed warsztatem, opcjonalny |

Modele pracują w trybie Direct Lake na punkcie końcowym SQL lakehouse'u, więc nie kopiują danych przy odświeżeniu. Nazwy w SM_Planowanie są pisane bez polskich znaków celowo: Learn ostrzega, że nieobsługiwane znaki Unicode w modelu mogą zablokować wstawienie kolumny wejściowej w arkuszu planu [Learn].

### 3.2 Dane

Zestaw obejmuje 4 marki (Aurea, Vento, Lumi, Kroko), 6 krajów i 181 MPK. Na MPK składa się 147 sklepów, 24 kanały e-commerce (marka w kraju) i 10 działów centrali. Siedem sklepów czeka na otwarcie, pięć zamknięto.

Aurea to odzież biznesowa premium, Vento sport i outdoor, Lumi bielizna, a Kroko obuwie i dodatki. Kraje to Polska, Niemcy, Austria, Holandia, Szwecja i Dania, więc kwoty w walutach lokalnych pochodzą z PLN, EUR, SEK i DKK.

Rok finansowy trwa od kwietnia do marca. Kwartał 1Q to kwiecień-czerwiec, 2Q lipiec-wrzesień, 3Q październik-grudzień, 4Q styczeń-marzec; 1H obejmuje kwiecień-wrzesień. Dniem bieżącym w danych jest 9.12.2026. Ostatni zamknięty miesiąc to listopad 2026, a sprzedaż dzienna kończy się 8.12.2026.

Wykonanie (ACT) w rachunku wyników sięga od kwietnia 2023 do listopada 2026. Budżet (BUD) obejmuje lata 2024/25, 2025/26 i 2026/27. Prognoza FC 8+4 dotyczy tylko roku 2026/27 i dla zamkniętych miesięcy powtarza wykonanie. Kalendarz kończy się 31.03.2028, bo plan dotyczy roku 2027/28.

| Tabela | Wiersze | Zawartość |
|---|---:|---|
| dim_data | 1 827 | kalendarz dzienny z rokiem finansowym, kwartałami i świętami |
| dim_marka | 5 | cztery marki i techniczny wiersz centrali |
| dim_kraj | 6 | kraje z walutą lokalną |
| dim_kategoria | 9 | kategorie produktów, w tym odzież wierzchnia |
| dim_scenariusz | 3 | ACT, BUD, FC |
| dim_konto | 13 | konta rachunku wyników ze znakiem i grupą kosztów |
| dim_mpk | 181 | sklepy, e-commerce i centrala, z planowaną i rzeczywistą datą otwarcia |
| fakt_sprzedaz_dzienna | 192 841 | sprzedaż, paragony i sztuki w układzie dzień x MPK |
| fakt_sprzedaz_kategorie_mies | 11 616 | sprzedaż miesięczna po kategoriach, bez poziomu sklepu |
| fakt_pnl | 100 195 | rachunek wyników w układzie miesiąc x MPK x konto x scenariusz |
| fakt_kursy_walut | 135 | kursy informacyjne; kwoty są już w PLN |
| agg_sprzedaz_mies | 4 232 | agregat sprzedaży marka x kraj x kanał x scenariusz dla SM_Planowanie |
| plan_kalendarz | 60 | kalendarz miesięczny kwiecień 2023-marzec 2028 dla Planu |
| ref_plan_2027_28_rozklad | 552 | wzorcowy rozkład celu 2027/28 na miesiące |

Konta rachunku wyników: 4010 przychody ze sprzedaży netto, 4510 koszt własny sprzedaży, 5110 wynagrodzenia personelu sklepów, 5120 czynsze, 5130 media i utrzymanie, 5210 marketing, 5220 logistyka e-commerce, 5230 prowizje płatnicze, 5310 logistyka magazynowa, 5410 wynagrodzenia centrali, 5420 IT i licencje, 5910 pozostałe koszty operacyjne, 6010 amortyzacja. Marża brutto to 4010 minus 4510, a EBITDA nie obejmuje konta 6010. Pełny opis kolumn jest w `dane/SLOWNIK_DANYCH.md`.

### 3.3 Historie ukryte w danych

Generator wpisał w dane kilka zdarzeń, które dają prowadzącemu materiał do rozmowy. Wszystkie są wymyślone.

| Historia | Co widać w danych | Gdzie wraca |
|---|---|---|
| Vento w Niemczech: cztery otwarcia przesunięte z maja-czerwca na sierpień-wrzesień 2026 | sprzedaż 1H 2026/27 o 14,4% poniżej budżetu | A1, pytanie o przyczynę odchylenia; P1, cel z góry a cel z dołu |
| Aurea w Austrii: czynsze rosną o 15%, budżet zakładał 3% | koszt czynszu o 11,7% ponad budżet | pytanie rezerwowe w A1 |
| E-commerce w Niemczech: stawka przewoźnika wyższa o 18% od października | koszt na zamówienie o 25,4% (październik) i 21,3% (listopad) ponad budżet | pytanie o koszt zamówienia |
| Ciepły listopad 2026 | odzież wierzchnia r/r -27,9% | pytanie o kategorie |
| Kroko: słabszy trend i cztery zamknięcia | kwiecień-listopad r/r -9,5% | P1, jedyny cel z ujemną zmianą |
| Black Friday 2025 | 7 388 000 PLN, 2,10 raza więcej niż średnia pozostałych piątków listopada | pytanie rezerwowe w A1 |
| Udział e-commerce | od 18,0% w 2023/24 do 23,1% w 2026/27 | pytanie o trend |
| Grudzień | najwyższy miesiąc każdego pełnego roku finansowego | P1, grudzień dostaje 136,31 mln PLN z celu |

### 3.4 Pliki Excel w Files/wejscia

| Plik | Zawartość | Rola na warsztacie |
|---|---|---|
| cele_sprzedazy_2027_28.xlsx | 46 celów rocznych w układzie marka x kraj x kanał, arkusze Cele i Opis | źródło celów marek wpisywanych w P1 |
| zalozenia_plan_2027_28.xlsx | 24 kombinacje marki i kraju, 7 planowanych sklepów | tło rozmowy o założeniach w P1 |
| budzet_opex_centrala_2027_28_szablon.xlsx | szablon budżetu centrali z formułami SUM i pustymi miesiącami | obraz dzisiejszego procesu na początku P2 |
| budzet_opex_centrala_2027_28_import.xlsx | arkusz Import: 45 wierszy, 10 MPK centrali, 6 kont, 19 kolumn | import do PowerTable w P2 |
| awaryjny_plan_zrodlo_2027_28.xlsx | 552 wiersze sprzedaży 2025/26, suma 866 150 412 PLN | zapasowe źródło arkusza planu, gdyby połączenie z modelem zawiodło |

### 3.5 Dlaczego Plan powstaje ręcznie

Wszystko poza Planem i raportem wdrażają skrypty. Plan ma publiczną definicję JSON w API [Learn], ale składa się z wielu części (arkusze, wizualizacje, kolumny wejściowe, writeback, scenariusze), a integracja z Git i potokami wdrożeń jest dla niego wciąż w preview [Learn]. Pisanie takiej definicji od zera, bez wzorca wyeksportowanego z działającego planu, byłoby zgadywaniem [wniosek].

Drugi powód to rozliczenie. Otwarcie, utworzenie albo edycja elementu Plan uruchamia 30-dniową sesję użytkownika liczoną w CU, której nie da się zakończyć wcześniej [Learn]. Automat tworzący plan przy każdym przebiegu skryptu uruchamiałby takie sesje bez potrzeby.

Wreszcie samo podłączenie planu do modelu trwa kilka minut i dobrze pokazuje, że plan korzysta z modelu semantycznego zbudowanego na tych samych danych w lakehouse co raporty, dlatego ścieżka tworzenia jest opisana w kroku P0.

Ręcznie powstaje też połączenie chmurowe, z którego korzysta SM_Planowanie (krok 1 w P0). Wybraliśmy uwierzytelnianie OAuth 2.0 na koncie prowadzącego. API Fabric tworzy połączenia między innymi z poświadczeniami jednostki usługi albo tożsamości obszaru roboczego, ale OAuth 2.0 nie ma na liście poświadczeń, które przyjmuje [Learn]. Skrypt wdrożenia sprawdza więc tylko, czy model korzysta z takiego połączenia, i ostrzega, gdy go brakuje.

## 4. Przebieg warsztatu krok po kroku

Każdy krok ma ścieżkę kliknięć i oczekiwany wynik, a tam, gdzie się da, także liczbę kontrolną. Polecenia zapisano tak, jak nazywa je angielski interfejs i dokumentacja Learn; w polskiej wersji portalu brzmią inaczej. Kwoty są w PLN i zaokrąglone do pełnych złotych, o ile nie zaznaczono inaczej.

### 4.0 Otwarcie (13:00-13:10)

Na ekranie jest obszar roboczy Fabrikam Kontroling Warsztat w widoku listy. Prowadzący zaczyna od zastrzeżenia, że dane są syntetyczne, a potem ustawia zegar: w danych jest 9.12.2026, trwa 3Q roku finansowego 2026/27, ostatni zamknięty miesiąc to listopad. Następnie wraca do potrzeb z rozdziału 1 i zapowiada, że najwięcej czasu dostaną planowanie i agenci.

> Wskazówka. Na starcie warto zapytać, który wątek z rozdziału 1 jest dziś najpilniejszy. Jeśli wygra agent, P3 w bloku 2 można pominąć, a odzyskane 7 minut oddać na pytania uczestników w A1.

### 4.1 Blok 1. Dane (13:10-13:20)

Blok ma pokazać jedną kopię danych w OneLake, z której korzystają SQL, model, plan i agent.

Lakehouse

1. W obszarze roboczym otwórz LH_Kontroling.
2. W panelu Explorer rozwiń Tables. Jest tam 14 tabel Delta, w tym fakt_pnl ze 100 195 wierszami i fakt_sprzedaz_dzienna ze 192 841 wierszami.
3. Rozwiń Files. Folder dane zawiera pliki parquet, z których powstały tabele, a folder wejscia pięć plików Excel z punktu 3.4.

Zapytanie SQL

1. Przełącznikiem w prawym górnym rogu zmień widok z Lakehouse na SQL analytics endpoint.
2. Wybierz New SQL query, wklej poniższe zapytanie i uruchom je przyciskiem Run.

```sql
SELECT f.scenariusz_kod, SUM(f.kwota_pln) AS sprzedaz_netto_pln
FROM dbo.fakt_pnl AS f
WHERE f.konto_id = '4010' AND f.miesiac BETWEEN '2026-04-01' AND '2026-11-01'
GROUP BY f.scenariusz_kod
ORDER BY f.scenariusz_kod;
```

| scenariusz_kod | sprzedaz_netto_pln |
|---|---:|
| ACT | 604 856 151,10 |
| BUD | 626 729 505,61 |
| FC | 604 856 151,10 |

Od kwietnia do listopada 2026 sprzedaż jest o 21,9 mln PLN, czyli 3,5%, niższa od budżetu. Wartości policzono z plików parquet; wynik zapytania w środowisku trzeba potwierdzić [do ponownego przebiegu]. FC pokrywa się z ACT, bo w prognozie 8+4 osiem zamkniętych miesięcy to wykonanie.

Model semantyczny

1. Wróć do obszaru roboczego, otwórz SM_Kontroling i przejdź do edycji modelu w przeglądarce (Open data model) [do próby].
2. Pokaż relacje wokół tabel Rachunek wyników i Sprzedaż dzienna, foldery miar oraz opis jednej miary, np. Odchylenie sprzedaży ACT vs BUD %.
3. Zwróć uwagę na polskie nazwy i opisy. To z nich, a nie z instrukcji agenta, korzysta generator zapytań DAX [Learn], do czego wrócimy w bloku 3.

Model działa w trybie Direct Lake, czyli czyta tabele Delta bezpośrednio z OneLake, bez importu kopii danych do modelu [Learn].

Excel w OneLake

1. W LH_Kontroling otwórz Files/wejscia.
2. Opowiedz, jak plik Excel trafia do tabeli. Polecenie Load to Tables obsługuje w lakehouse tylko pliki CSV i Parquet [Learn], więc dla xlsx służy Dataflow Gen2: New item > Dataflow Gen2 > Get data > More > Excel workbook, wybór arkusza w oknie Navigator, Transform Data, Choose data destination (Lakehouse), Publish [Learn].
3. Wspomnij o OneLake file explorer. To aplikacja dla Windows, która pokazuje OneLake w Eksploratorze plików podobnie jak OneDrive, więc plik zapisany z Excela w takim folderze ląduje w Files [Learn].

> Wskazówka. Dataflow pokazujemy najwyżej do okna Navigator, bez publikacji. Gdy padnie pytanie o dodatki do Excela, z których zespół korzysta dziś, nie obiecujemy zamiennika; najbliższe w Fabric jest otwarcie modelu w Excelu przez Analyze in Excel, pokazywane w bloku 4.

### 4.2 Blok 2. Planning (13:20-13:50)

Plan to element Fabric IQ dostępny w GA. Arkusz planistyczny działa na modelu semantycznym, przy tworzeniu planu powstaje wewnętrzna baza metadanych, a uzgodnione liczby można zapisać do własnej bazy Fabric SQL [Learn].

#### P0. Plan i arkusz (przygotowane przed warsztatem)

Na warsztacie prowadzący otwiera gotowy arkusz Warsztat i tylko omawia poniższe kroki, w czasie przeznaczonym na P1.

1. W obszarze roboczym otwórz Settings modelu SM_Planowanie i rozwiń Gateway and cloud connections. W polu Maps to wybierz Create a connection [Learn], nazwij połączenie Fabrikam_Planowanie_SQL, wybierz uwierzytelnianie OAuth 2.0 i zaloguj się przez Edit credentials. Opcji SSO nie zaznaczaj, poziom prywatności ustaw na Organizational i wybierz Create. Potem wskaż nowe połączenie w Maps to i zatwierdź przez Apply.
2. W obszarze roboczym wybierz New item > Plan, wpisz nazwę Plan_Kontroling i Create. Razem z planem powstaje baza metadanych [Learn].
3. W planie wybierz Planning, nadaj arkuszowi nazwę Warsztat i Create.
4. Data > Add > Select Semantic Model, wskaż SM_Planowanie, potem Add > Connect.
5. Przeciągnij pola: do Rows Marka (tabela Marka), Kraj (Kraj) i Kanal (Sprzedaz), do Columns Kwartal i Miesiac (Kalendarz), do Values miarę Sprzedaz ACT 2025/26.

Krok 1 wynika z trybu modelu. Model Direct Lake domyślnie korzysta z SSO, czyli czyta dane tożsamością osoby, która wysyła zapytanie [Learn]. Na takim modelu plan się nie podłączył, a komunikat błędu podawał jako możliwą przyczynę „direct lake dataset with SSO only Gateway/Cloud connections” [test]. Opis kodów błędów Planu każe w takim przypadku zapewnić wszystkim użytkownikom uprawnienia do danych w OneLake, a jeśli to niemożliwe, utworzyć połączenie chmurowe z uwierzytelnianiem OAuth 2.0 albo jednostką usługi. Przy modelu Direct Lake połączenie ma używać stałej tożsamości [Learn]. Tożsamość połączenia musi mieć w obszarze roboczym rolę Member albo Admin [Learn]. Po przypisaniu modelu do połączenia Fabrikam_Planowanie_SQL plan podłączył się bez błędu [test].

Stała tożsamość zmienia zasady dostępu do danych. Gdy SSO jest wyłączone, o tym, które dane Direct Lake odczyta, decydują uprawnienia tej tożsamości, a nie osoby pracującej z planem [Learn]. Ograniczenia według marki, kraju albo MPK trzeba wtedy zapisać w modelu, bo przy stałej tożsamości Learn zaleca reguły RLS i OLS w samym modelu semantycznym [Learn]. Ma to znaczenie przy pytaniu 9 z punktu 7.1. SM_Kontroling, na którym pracują agenci danych i Copilot, zostaje przy domyślnym SSO [test].

Gdy plan poprosi o połączenie do pracy zespołowej, tutorial prowadzi przez Set up connection > Fabric SQL connection > Create new connection [Learn].

| Wiersz | Sprzedaz ACT 2025/26 |
|---|---:|
| Aurea | 247 413 778 |
| Vento | 344 103 948 |
| Lumi | 110 434 702 |
| Kroko | 164 197 984 |
| Suma | 866 150 412 |

Kolumny niosą kwartał i miesiąc roku finansowego, bez roku. Rok ustala sama miara, która zawsze pokazuje 2025/26, dlatego ta sama siatka kwiecień-marzec posłuży za szablon roku 2027/28 [wniosek z konstrukcji modelu].

> Wskazówka. Gdyby połączenie z modelem zawiodło, arkusz można zbudować z pliku awaryjny_plan_zrodlo_2027_28.xlsx. Excel jest udokumentowanym źródłem danych planu [Learn], ale tej ścieżki nie testowaliśmy.

#### P1. Rozkład celu sprzedaży 2027/28 (10 min)

Ten krok odpowiada na potrzebę rozłożenia sprzedaży w czasie z rozdziału 1.

1. Planning > Totals > Column Grand Total. Kolumna sumy roku pojawia się po lewej stronie.
2. Planning > Insert Column > Number. Wybierz Copy from another series i miarę Sprzedaz ACT 2025/26. Title: Plan 2027/28, Insert as: Visual Measure, zaznaczone Distribute parent value to children. Create.
3. Kliknij dwukrotnie komórkę Plan 2027/28 w wierszu Aurea i kolumnie sumy roku, wpisz 274514000 i zatwierdź przyciskiem z symbolem zaznaczenia.
4. Powtórz to dla pozostałych marek. Jedną z nich warto oddać uczestnikom, niech sami podadzą cel.

| Marka | ACT 2025/26 | Cel 2027/28 do wpisania | Zmiana |
|---|---:|---:|---:|
| Aurea | 247 413 778 | 274 514 000 | +11,0% |
| Vento | 344 103 948 | 422 704 000 | +22,8% |
| Lumi | 110 434 702 | 134 204 000 | +21,5% |
| Kroko | 164 197 984 | 145 272 000 | -11,5% |
| Grupa | 866 150 412 | 976 694 000 | +12,8% |

Cele to sumy 46 wierszy pliku cele_sprzedazy_2027_28.xlsx (marka x kraj x kanał), policzone jako prognoza 2026/27 powiększona o docelowy wzrost. Kroko jako jedyna marka ma cel niższy od bazy, co pasuje do słabszego trendu i czterech zamknięć.

Plan rozdziela wpisaną kwotę na kraje, kanały i miesiące proporcjonalnie do sprzedaży 2025/26 [Learn]. Spodziewany rozkład w mln PLN dla pierwszego półrocza, kwiecień-wrzesień:

| Marka | Kwi | Maj | Cze | Lip | Sie | Wrz |
|---|---:|---:|---:|---:|---:|---:|
| Aurea | 20,87 | 23,26 | 21,38 | 20,82 | 21,61 | 21,96 |
| Vento | 31,57 | 34,66 | 32,58 | 32,00 | 33,14 | 33,95 |
| Lumi | 10,43 | 11,19 | 10,62 | 10,27 | 10,68 | 10,67 |
| Kroko | 11,70 | 12,40 | 11,34 | 11,13 | 11,55 | 11,68 |
| Grupa | 74,57 | 81,52 | 75,91 | 74,21 | 76,98 | 78,25 |

Drugie półrocze, październik-marzec, i suma roku:

| Marka | Paź | Lis | Gru | Sty | Lut | Mar | Razem |
|---|---:|---:|---:|---:|---:|---:|---:|
| Aurea | 23,81 | 29,83 | 38,01 | 17,76 | 15,23 | 19,98 | 274,51 |
| Vento | 36,90 | 45,74 | 59,35 | 27,69 | 23,87 | 31,26 | 422,70 |
| Lumi | 11,50 | 14,39 | 18,66 | 8,60 | 7,37 | 9,83 | 134,20 |
| Kroko | 12,66 | 15,18 | 20,30 | 9,33 | 7,78 | 10,22 | 145,27 |
| Grupa | 84,87 | 105,14 | 136,31 | 63,38 | 54,25 | 71,30 | 976,69 |

Zaokrąglenia w Planie mogą odbiegać od tabeli o pojedyncze złote [do próby].

Cel z góry a cel z dołu

5. Rozwiń Vento i odszukaj Niemcy. Rozkład według historii daje im około 102,15 mln PLN, czyli 24,2% celu marki, tyle, ile wynosił ich udział w 2025/26.
6. Plik z celami, budowany kraj po kraju, zakłada dla Niemiec 114 756 000 PLN, bo liczy też sklepy otwarte w 2026. Różnica 12,6 mln PLN otwiera rozmowę o tym, gdzie powinien powstawać cel.
7. Wpisz 114756000 w sumie roku dla Niemiec. Suma Vento powinna urosnąć o różnicę [do próby].
8. Zablokuj Niemcy przed ponownym rozkładem i wpisz jeszcze raz cel Vento. Odblokowane kraje dzielą wtedy między siebie resztę [wniosek, do próby]. Tutorial pokazuje blokadę przez ikonę rozkładu (Lock all children) i regułę Model > Rules > Locking Rule [Learn]; ścieżkę dla pojedynczego kraju trzeba jeszcze sprawdzić.

> Wskazówka. Jeśli blokada pojedynczego kraju nie zadziała tak, jak opisano, kończymy na punkcie 6. Sama różnica 12,6 mln PLN między rozkładem z historii a planem oddolnym wystarcza do rozmowy o celu z góry i z dołu.

#### P2. Budżet kosztów centrali w PowerTable (8 min)

Tu wracamy do Excela krążącego między działami, od którego zaczyna się rozdział 1.

1. Na komputerze prowadzącego otwórz budzet_opex_centrala_2027_28_szablon.xlsx. Arkusz Budzet ma 45 wierszy do wypełnienia przez 10 MPK centrali, arkusz Instrukcja opisuje zasady. Plik odwzorowuje obieg z rozdziału 1, czyli szablon wysyłany do właściciela MPK i odsyłany po wypełnieniu. Sam szablon jest wymyślony.
2. W Plan_Kontroling wybierz New PowerTable Sheet, nazwij arkusz Budzet OPEX centrali i wybierz Create > Create a New App.
3. Select a Connection, w polu Database Name wskaż SQLDB_Planowanie, Add > Connect.
4. New Table, schemat dbo, Table Name budzet_opex_2027_28.
5. Import Data > Upload File, plik budzet_opex_centrala_2027_28_import.xlsx z arkuszem Import, Next.
6. Jako klucz wskaż mpk_id i konto_id, potem Finish > Save.

Arkusz Import ma 45 wierszy i 19 kolumn: identyfikatory i nazwy MPK oraz kont, wykonanie 2025/26, prognozę 2026/27, dwanaście miesięcy od m01_2027_04 (kwiecień 2027) do m12_2028_03 (marzec 2028) i komentarz. Kwoty miesięczne to prognoza 2026/27 podzielona na 12 i powiększona o indeksację, 6% dla wynagrodzeń centrali i 3% dla pozostałych kont, zaokrąglona do 100 PLN.

| Konto | Budżet 2027/28 |
|---|---:|
| 5210 marketing | 14 330 400 |
| 5310 logistyka magazynowa | 20 464 800 |
| 5410 wynagrodzenia centrali | 39 818 400 |
| 5420 IT i licencje | 12 718 800 |
| 5910 pozostałe koszty operacyjne | 6 574 800 |
| 6010 amortyzacja | 4 107 600 |
| Razem | 98 014 800 |

7. Znajdź wiersz HQ-TEC z kontem 5420. Październik (m07_2027_10) ma 1 120 500 wobec 940 500 we wrześniu i listopadzie, a komentarz wyjaśnia: „Jednorazowe odnowienie licencji w październiku 2027.” Uzasadnienie podróżuje razem z liczbą.
8. W wierszu HQ-MKT-VEN z kontem 5210 kliknij dwukrotnie listopad (m08_2027_11) i zmień 433 700 na 600 000, np. pod kampanię Black Friday. Enter, potem Preview Changes > Save to Database > Proceed [Learn].
9. Otwórz PowerTable > Audit. Wpis pokazuje kolumnę, wartość przed zmianą i po niej, użytkownika i czas [Learn].
10. W SQLDB_Planowanie uruchom zapytanie kontrolne.

```sql
SELECT konto_id,
       SUM(m01_2027_04 + m02_2027_05 + m03_2027_06 + m04_2027_07 + m05_2027_08 + m06_2027_09
         + m07_2027_10 + m08_2027_11 + m09_2027_12 + m10_2028_01 + m11_2028_02 + m12_2028_03)
         AS budzet_2027_28_pln
FROM dbo.budzet_opex_2027_28
GROUP BY ROLLUP (konto_id)
ORDER BY konto_id;
```

Po zmianie konto 5210 ma 14 496 700, a suma 98 181 100. Nazwy i typy kolumn tabeli utworzonej przez import trzeba jeszcze potwierdzić [do próby].

PowerTable przyjmuje też wiersze wklejone z Excela, a jeden import może dodać do 20 000 nowych wierszy [Learn].

> Wskazówka. Na próbie używamy tabeli budzet_opex_proba, żeby budzet_opex_2027_28 powstała na oczach uczestników. Jeśli import pliku zawiedzie, tworzymy pustą tabelę z tymi samymi kolumnami i wklejamy wiersze z Excela.

#### P3. Symulacja i prognoza (7 min)

Symulacja

1. W arkuszu Warsztat zaznacz nagłówek kolumny Plan 2027/28 i wybierz Planning > Insert Column > Simulate. Simulate jest w sekcji Input, pod Number. Jeśli plan poprosi o zapisanie arkusza, potwierdź [Learn].
2. W panelu Simulation wpisz Title: Kroko -5%. Simulation based on powinno już wskazywać Plan 2027/28. Sprawdź, że Show Slider jest zaznaczone, Value Range ustaw na 20, czyli od -20% do +20%, i wybierz Create [Learn].
3. W wierszu Kroko zaznacz komórkę symulacji w kolumnie sumy roku, tak jak przy wpisywaniu celu w P1. Na suwaku wybierz ikonę Edit (ołówek), w oknie procentu symulacji wpisz -5 i wybierz Apply [Learn].

Kroko spada do 138 008 400, a grupa do 969 430 400, czyli o 7 263 600. Kolumna Plan 2027/28 zostaje bez zmian, bo symulacja nie nadpisuje miary źródłowej [Learn].

> Wskazówka. Strona Learn o miarach symulacyjnych pokazuje Simulate jako osobny przycisk w grupie Rows & Columns, ale to układ wstążki rozwiniętej strzałką w prawym górnym rogu. We wstążce zwiniętej trzeba go szukać w menu Insert Column [Learn]. Gdyby to menu było nieaktywne, sprawdź przełącznik Editing/Reading w prawym górnym rogu i rolę widoczną na pasku planu, bo sesja Viewer nie wstawi miary symulacyjnej [Learn]. Jeśli suwak się nie pokaże, kliknij dwukrotnie komórkę symulacji i wpisz wartość bezpośrednio [Learn].

Wersje planu pokazujemy opcjonalnie. Model > Scenario, nazwa Wariant ostrozny, wybór serii, Create, zmiana wartości i Save; porównanie przez Compare Scenario > Scenario Comparison z wersją Base i wyjście przez Exit Compare [Learn]. Learn zakłada przygotowany wymiar scenariusza, a czy SM_Planowanie go zapewnia, jeszcze nie sprawdziliśmy [do próby].

Prognoza 8+4 [do próby]

Learn opisuje prognozę na hierarchii czasu Year > Quarter > Month [Learn], dlatego do tego kroku służy osobny arkusz Prognoza z kolumnami Rok finansowy, Kwartal i Miesiac oraz wierszami jak w arkuszu Warsztat.

1. Model > Forecast, nazwa FC naiwny 8+4, okres roku finansowego 2026/27, Next.
2. Dla zamkniętych okresów (kwiecień-listopad 2026) wybierz Link to Measure i Source Measure Sprzedaz ACT, Next.
3. Dla okresów otwartych wybierz Data Input z Default Value None. W Pre-fill Open Periods ustaw Copy from, Operation Period Range, Source Range grudzień 2025-marzec 2026 i Target Range grudzień 2026-marzec 2027. Save.

| Składnik | PLN |
|---|---:|
| Wykonanie kwiecień-listopad 2026 | 604 856 151 |
| Grudzień-marzec skopiowane z roku 2025/26 | 288 153 827 |
| Prognoza naiwna 2026/27 | 893 009 978 |
| Dla porównania: FC w danych | 910 086 752 |
| Dla porównania: budżet | 937 391 962 |

Predict też jest opcjonalny. Na mierze prognozy wybierz Model > Predict, Historic Data Range kwiecień 2023-listopad 2026, czyli 44 miesiące, Forecast Date Range grudzień 2026-marzec 2027, algorytm np. Auto ETS, potem Run Forecast i Save Forecast [Learn]. Learn wymaga co najmniej 24 okresów historii, a niektóre algorytmy 36 lub 48 [Learn]. Wyniku nie znamy z góry, więc porównujemy go z prognozą naiwną i z FC.

> Wskazówka. Jeżeli na próbie prognoza na kalendarzu finansowym się nie uda, P3 kończy się na symulacji, a prognozę naiwną omawiamy na tabeli powyżej. Funkcja Extend Time przydaje się, gdy w źródle brakuje przyszłych okresów. Kalendarz SM_Planowanie sięga marca 2028, ale miesiące bez sprzedaży mogą nie pojawić się w arkuszu, co też trzeba sprawdzić.

#### P4. Komentarze, akceptacja i zapis planu (5 min)

1. Wróć do arkusza Warsztat. Jeśli zostało otwarte porównanie wersji z P3, zamknij je przez Exit Compare.
2. Prawym przyciskiem kliknij komórkę Vento, Niemcy i wybierz Add Comment. Wpisz np. „Cel z planu oddolnego, uwzględnia otwarcia z 2026”, oznacz osobę przez @ i wybierz Post. Kolumnę komentarzy włącza Planning > Comments > Settings > Comments Column > Save [Learn].
3. Model > Approval. Level 1 nazwij np. Kontroler marki, Level 2 Dyrektor kontrolingu, przypisz akceptujących, Next, ustaw Reset on Rejection i Teams Notifications, Submit. Po wysłaniu do akceptacji wpis ma status Submitted, a następny poziom czeka jako Pending [Learn] [do próby].
4. Writeback > Add Destination: połączenie, baza SQLDB_Planowanie, Table Name plan_sprzedazy_2027_28, Add. W Writeback > Settings ustaw Writeback Type na Long with Changes, uruchom Writeback > Writeback i pokaż Writeback > Logs [Learn].
5. W SQLDB_Planowanie wykonaj `SELECT TOP (20) * FROM dbo.plan_sprzedazy_2027_28;`. Układu kolumn jeszcze nie znamy, nie wiemy też, czy zapis obejmie kolumnę symulacji z P3 [do próby].

Jako cel zapisu Learn dokumentuje tylko Fabric SQL database. Jedna operacja obejmuje do 1,2 mln komórek, a wewnętrznej bazy `__fabric_plan_sys_db` nie należy odpytywać [Learn]. Wariant Long with Changes zachowuje historię zmian, zwykły Long nadpisuje wiersz o tym samym kluczu [Learn].

Arkusz Warsztat nie ma roku w kolumnach, więc zapis też go nie zawiera, a rok wynika tylko z nazwy miary. W pilotażu kalendarz arkusza powinien mieć rok [wniosek]. Z tabeli w SQL database może czytać hurtownia albo system planistyczny, ale sposób odbioru po stronie Fabrikam Fashion to pytanie otwarte (rozdział 7).

> Wskazówka. Na próbie zapis idzie do tabeli plan_sprzedazy_proba. Akceptację najlepiej skonfigurować z kontem prowadzącego na obu poziomach, inaczej przejścia statusów nie pokażemy jednym kontem; czy produkt na to pozwala, wyjdzie na próbie.

### 4.3 Blok 3. Agenci danych (13:50-14:15)

Agent danych Fabric odpowiada na pytania zadane zwykłym językiem. Wybiera źródło, generuje zapytanie (dla modelu semantycznego jest to DAX), uruchamia je i opisuje wynik [Learn]. Funkcja jest w GA i potrzebuje płatnej capacity F2 lub P1 albo wyższej; trial nie wystarcza [Learn]. Learn podaje, że agent nie obsługuje obecnie języków innych niż angielski, i zaleca pytania po angielsku [Learn]. W naszych testach pytania po polsku dawały poprawne odpowiedzi [test], ale to obserwacja, a nie deklaracja wsparcia.

#### A1. Agent na przygotowanym modelu (10 min)

1. Otwórz Agent_Kontroling i pokaż źródło SM_Kontroling oraz instrukcje agenta.
2. Zadaj cztery pytania w tej kolejności i w dokładnie takim brzmieniu.

| Pytanie | Oczekiwana odpowiedź |
|---|---|
| Jaka była sprzedaż netto grupy w 2Q 2026/27 i jak wypadła względem budżetu? | ACT 213 602 803 wobec BUD 220 491 560, czyli -6 888 757 (-3,1%) |
| Dlaczego sprzedaż Vento w Niemczech w 1H 2026/27 jest poniżej budżetu? Sprawdź też terminy otwarć sklepów. | luka -7,3 mln PLN (-14,4%); cztery sklepy (SK-VEN-DE-009 do 012) otwarte trzy miesiące później niż w planie; różnica między budżetem a wykonaniem tych sklepów to 6,50 mln PLN, około 89% luki |
| Jaka jest sprzedaż w bieżącym kwartale? | niepełny 3Q 2026/27: październik i listopad z rachunku wyników 175 615 655 plus 1-8 grudnia z danych dziennych 30 658 591, razem 206 274 245 |
| Jaka będzie sprzedaż w 2029 roku? | odmowa, bo nie ma danych ani prognozy dla 2029 |

Odpowiedzi agentów na obecnych danych nie zostały jeszcze zmierzone [do ponownego przebiegu].

3. Po każdej odpowiedzi rozwiń listę kroków, które agent wykonał, żeby dojść do wyniku [Learn]. Czy widać w niej pełne zapytanie DAX, jeszcze nie sprawdziliśmy [do próby].

Pytania rezerwowe przydadzą się, gdy zostanie czas albo któreś z powyższych zawiedzie: pięć sklepów z największym przekroczeniem czynszu (Aurea w Austrii), prognoza EBITDA na 2026/27 i Black Friday 2025. Pełne brzmienia i odpowiedzi są w załączniku A.

> Wskazówka. We wcześniejszym przebiegu, na innej wersji danych syntetycznych, odpowiedź trwała od kilkudziesięciu sekund do półtorej minuty, więc pauzę wypełniamy opisem tego, co agent robi w tle. Pytanie o przyczynę odchylenia zadajemy w brzmieniu z tabeli, razem z prośbą o terminy otwarć. W tamtym przebiegu krótsza wersja takiego pytania dała tabelę z błędnym wierszem Razem, a inna wymieniła wszystkie sklepy marki w kraju bez podsumowania.

#### A2. Ten sam agent bez przygotowania modelu (8 min)

1. Otwórz Agent_Kontroling_bez_przygotowania. Jego źródło, SM_Kontroling_surowy, ma te same tabele i dane, ale pod nazwami z lakehouse, np. dim_data i czy_swieto_pl. Nie ma miar, opisów, oznaczonej tabeli dat ani instrukcji AI. Sam agent nie ma też własnych instrukcji.
2. W obu agentach zadaj to samo pytanie: „Ile wyniosły koszty IT i licencji (konto 5420) w RF 2025/26 w porównaniu z RF 2024/25?”

Poprawna odpowiedź to 10 835 tys. PLN w 2024/25 i 11 485 tys. PLN w 2025/26, wzrost o 6,0%. We wcześniejszym przebiegu, na innej wersji danych, agent przygotowany odpowiedział poprawnie, a agent bez przygotowania dodał do siebie wykonanie i budżet i podał kwotę dwa razy za wysoką. Na obecnych danych trzeba to sprawdzić od nowa [do ponownego przebiegu].

3. Pokaż wynik całego zestawu 14 pytań z załącznika A, gdy będzie już zmierzony na obecnych danych [do ponownego przebiegu]. We wcześniejszym przebiegu agent przygotowany odpowiadał poprawnie znacznie częściej niż agent surowy, a ten drugi dwa razy zakończył się błędem technicznym. Obaj agenci dostają identyczne brzmienia pytań, ale pięć z nich ma podpowiedź w nawiasie, o czym więcej w załączniku A.
4. Wyjaśnij, co znaczy przygotowanie. Agent korzystający z modelu semantycznego pomija przy generowaniu DAX własne instrukcje i opiera się na metadanych modelu oraz ustawieniach Prep data for AI [Learn]. Opisy miar, reguły roku finansowego, data bieżąca i preferowane miary muszą więc żyć w modelu, a skorzystają z nich zarówno agent, jak i Copilot w Power BI [wniosek].
5. W SM_Kontroling otwórz Home > Prep data for AI i pokaż Simplify data schema, Add AI instructions i Verified answers. Funkcja jest w preview [Learn].

Warto powiedzieć otwarcie, że przygotowany model też ma słabe miejsce. We wcześniejszym przebiegu jedna z wersji pytania o przyczynę odchylenia zwróciła tabelę z wierszem Razem, który mieszał przychody z kosztami. Przyczyna leży w modelu: miary Kwota ACT i Kwota BUD nie uwzględniają znaku konta, więc ich suma przez sekcje rachunku wyników nie ma sensu. Poprawka to miara ze znakiem z tabeli kont albo blokada sumowania między sekcjami, uzupełniona o verified answer dla tego pytania [wniosek]. Dla Fabrikam Fashion płynie z tego prosty wniosek: zestaw pytań testowych z poprawnymi odpowiedziami jest częścią wdrożenia agenta, a nie dodatkiem.

Jeśli zostanie czas, agenta można utworzyć na żywo. New item, wyszukaj Fabric data agent, nadaj nazwę, w katalogu OneLake wskaż SM_Kontroling i wybierz Add, w panelu Explorer zaznacz tabele, Publish [Learn]. Do odpytywania modelu przez agenta wystarcza uprawnienie Read do modelu, bez Build i bez dostępu do obszaru roboczego [Learn].

#### A3. Kanały dostępu (7 min)

1. W Agent_Kontroling otwórz Settings > Model Context Protocol. Zakładka pokazuje nazwę serwera, adres URL, nazwę i opis narzędzia oraz pozwala pobrać plik mcp.json [Learn]. Adres ma postać `https://api.fabric.microsoft.com/v1/mcp/workspaces/{WorkspaceId}/dataagents/{DataAgentId}/agent` i działa tylko dla opublikowanego agenta, a opis agenta staje się opisem narzędzia [Learn].
2. Opcjonalnie uruchom w terminalu `python fabric\deploy\testuj_agenta.py --agent Agent_Kontroling --pytania 9`. Skrypt z repozytorium łączy się z agentem przez MCP, pyta o prognozę EBITDA i wypisuje odpowiedź na ekranie. Oczekiwana odpowiedź: EBITDA FC 149 380 tys. PLN wobec budżetu 161 951 tys., czyli -12 570 tys. (-7,8%).
3. Omów kanały.

| Kanał | Status [Learn] | Co trzeba wiedzieć [Learn] |
|---|---|---|
| Czat agenta w portalu Fabric | GA | odbiorca potrzebuje dostępu do agenta i do danych źródłowych |
| Microsoft 365 Copilot i Teams przez Agent Store (Publish to Agent Store) | preview | ta sama dzierżawa; Learn wymienia „Microsoft Copilot license or Office 365 commercial subscription” oraz licencje użytkowników; orkiestrator Copilota może przeredagować odpowiedź agenta |
| Copilot Studio, narzędzie Fabric IQ Data MCP | GA od sierpnia 2026 | publikacja do Teams i Microsoft 365 Copilot; uwierzytelnienie User albo Maker; osoby budujące agenta potrzebują licencji Microsoft 365 Copilot |
| Starszy przepływ Copilot Studio z podłączonym agentem | preview | zweryfikowany tylko dla Teams |
| Microsoft Foundry | stare narzędzie wycofywane 6.11.2026, następca Fabric IQ w preview | potrzebny projekt Foundry; użytkownicy wywołujący narzędzie potrzebują licencji Fabric |
| Punkt końcowy MCP dla dowolnego klienta | Learn nie podaje statusu | odpowiedzi agenta mogą opuścić granicę zgodności i region Fabric |

W trybie Maker wszyscy użytkownicy agenta Copilot Studio widzą dane przez uprawnienia jego twórcy [Learn]. Przy danych finansowych to decyzja z obszaru bezpieczeństwa, nie tylko techniczna.

> Wskazówka. Kanałów Microsoft 365 Copilot i Copilot Studio nie testowaliśmy w tym środowisku. Pokazujemy zakładkę MCP i tabelę, bez publikacji na żywo.

### 4.4 Blok 4. Raport, Copilot, aplikacje i Excel (14:15-14:25)

Raport z Copilotem

1. Otwórz Raport_Kontroling i panel Copilot. Przykładowe polecenie: „Podsumuj odchylenie sprzedaży od budżetu w 1H 2026/27 według marek” [do próby].
2. Panel Copilota w raporcie jest w GA. Samodzielne doświadczenie Copilota w Power BI jest w preview i wymaga włączenia ustawienia dzierżawy [Learn].
3. Oznaczenie modelu jako Approved for Copilot usuwa w samodzielnym Copilocie ostrzeżenie, że odpowiedź może być niskiej jakości. Zmiana obejmuje raporty na tym modelu zwykle w ciągu godziny, a gdy raportów jest dużo, może potrwać do 24 godzin [Learn]. Po włączeniu osobnego ustawienia administracyjnego samodzielny Copilot pokazuje tylko zatwierdzone elementy [Learn].

Aplikacje

Na pytanie o przyszłość raportów Learn odpowiada wprost: „Reports remain a core analytics experience. Fabric Apps complement reports...” [Learn]. Org apps, czyli pakiety raportów dla odbiorców, są w GA i w jednym obszarze roboczym może ich być kilka [Learn]. Fabric Apps są w preview, buduje się je w kodzie (TypeScript), wymagają włączenia obciążenia w dzierżawie i nie są dostępne w regionie Poland Central [Learn]. Do zapisu z raportu, np. akceptacji korekty, służą translytical task flows: przycisk w raporcie wywołuje funkcję użytkownika, która zapisuje dane w Fabric SQL database, warehouse albo w plikach lakehouse [Learn].

Excel

1. Na SM_Kontroling wybierz Analyze in Excel i zbuduj tabelę przestawną z miarą Sprzedaż netto ACT według marek [do próby].
2. Do tego potrzebne jest uprawnienie Build albo rola Contributor oraz ustawienie dzierżawy „Users can work with Power BI semantic models in Excel using a live connection”. Użytkownicy z licencją Free mogą z tego korzystać tylko w My workspace, na Premium albo na capacity F64 i większej [Learn].

> Wskazówka. Jeśli raport nie powstał na próbie, Copilota pomijamy albo pokazujemy na nowym raporcie z modelu, a zaoszczędzony czas oddajemy na pytania.

### 4.5 Blok 5. Dalsze kroki (14:25-14:30)

Prowadzący pokazuje warianty pilotażu z rozdziału 6 i pytania z rozdziału 7. Na koniec prosimy o wybór wariantu oraz o 20-30 prawdziwych pytań kontrolingu z poprawnymi odpowiedziami, które posłużą za zestaw testowy agenta. Przyda się też kontakt do osoby odpowiedzialnej za system planistyczny.

## 5. Licencje i koszty

Pytanie, czy to wymaga Premium, ma odpowiedź w dwóch częściach. Pierwsza dotyczy capacity. Agent danych i Copilot działają wyłącznie na płatnej capacity F2 albo P1 lub wyższej; capacity próbna i Premium Per User nie wystarczą [Learn]. Plan uruchomi się na F2 albo na capacity próbnej Fabric [Learn], ale za każdą aktywną sesję użytkownika zużywa CU, co opisuje punkt 5.2. Druga część dotyczy licencji użytkowników. Zależą one od rozmiaru capacity i od tego, co kto robi, a w kilku miejscach Learn nie daje jednoznacznej odpowiedzi (5.3 i 7.2).

Kwot w PLN celowo nie podajemy. Żeby je policzyć, trzeba znać rozmiar capacity, posiadane licencje, liczbę osób w każdej roli planu i kanał, którym agent ma docierać do użytkowników. Żadnej z tych informacji jeszcze nie mamy.

### 5.1 Wymagania poszczególnych funkcji

| Funkcja | Status | Wymaga | Warto wiedzieć |
|---|---|---|---|
| Plan (Fabric IQ) | GA | capacity F2 lub wyższa albo trial Fabric; ustawienie dzierżawy „Allow XMLA endpoints and Analyze in Excel with on-premises semantic models”; na capacity XMLA Endpoint w trybie Read Only albo Read Write; Edge lub Chrome; dla modelu Direct Lake połączenie chmurowe ze stałą tożsamością i wyłączonym SSO (P0) | bez kont gości B2B; jeden plan łączy się z jednym modelem i tego połączenia nie da się później zmienić |
| Agent danych Fabric | GA | płatna capacity F2 lub P1 albo wyższa; ustawienie dzierżawy „Users can use Copilot and other features powered by Azure OpenAI” | do zadawania pytań wystarcza Read na modelu; do pięciu źródeł; agent i źródła w tym samym regionie; polski oficjalnie nieobsługiwany |
| Copilot w panelu raportu Power BI | GA | płatna capacity F2 lub P1 albo wyższa | capacity próbne i darmowe SKU nie są obsługiwane |
| Samodzielny Copilot w Power BI | preview | jak wyżej i osobne ustawienie dzierżawy | osobne ustawienie administracyjne pozwala pokazywać w nim tylko elementy Approved for Copilot |
| Copilot in Power BI and Microsoft Fabric, nowe doświadczenie łączące Fabric IQ i Work IQ | preview | licencja Copilot Premium | licencje Free, Pro i PPU jej nie zastępują |
| Prep data for AI | preview | osobnych wymagań nie sprawdzaliśmy | ustawienia zapisują się w modelu, więc korzystają z nich i Copilot, i agent |
| Analyze in Excel | Learn nie podaje | uprawnienie Build albo rola Contributor; ustawienie dzierżawy „Users can work with Power BI semantic models in Excel using a live connection” | licencja Free działa tylko w My workspace, na Premium albo na F64 i większej |
| Org apps | GA | licencje odbiorców jak przy treściach Power BI (5.3) | w jednym obszarze roboczym może być kilka aplikacji |
| Fabric Apps | preview | capacity; administrator dzierżawy musi włączyć obciążenie | każda operacja zużywa CU; niedostępne w regionie Poland Central |

Statusy i wymagania pochodzą z Learn [Learn]. Wyjątkiem jest wiersz org apps, w którym wymaganie licencyjne wynika z ogólnych zasad dla treści Power BI [wniosek]. Wymagania kanałów, którymi agent trafia do Microsoft 365 Copilot, Teams, Copilot Studio i Foundry, zebrano w tabeli w kroku A3.

### 5.2 Jak Plan zużywa capacity

Plan nie ma licencji na użytkownika, tylko rozlicza 30-dniowe sesje [Learn]. Sesję uruchamia otwarcie, utworzenie albo edycja planu. Trwa 30 dni, w Learn opisanych też jako 730 godzin, i nie da się jej zakończyć wcześniej [Learn]. Liczy się osobno dla każdej kombinacji dzierżawy, użytkownika i capacity, według najwyższej roli, jaką ta osoba pełniła na danej capacity. Kilka obszarów roboczych na jednej capacity nie mnoży opłat, ale druga capacity oznacza drugą sesję [Learn].

| Persona | Kto to jest [Learn] | CU-h na sesję [Learn] | Część F2 przez 30 dni [wniosek] | Część F64 przez 30 dni [wniosek] |
|---|---|---:|---:|---:|
| Planner | buduje modele i arkusze planistyczne | 847 | 58,0% | 1,8% |
| Stakeholder | wprowadza i akceptuje dane, tworzy scenariusze, raporty i aplikacje danych referencyjnych | 168 | 11,5% | 0,4% |
| Viewer | przegląda plany i raporty bez edycji | 37 | 2,5% | 0,1% |

Udziały policzyliśmy z mocy capacity: F2 to 2 CU przez 730 godzin, czyli 1 460 CU-h, a F64 to 46 720 CU-h. Learn mówi o pozostałych CU doliczanych do rachunku przy wstrzymaniu capacity, co sugeruje, że sesja zużywa CU równomiernie przez cały okres [wniosek]. Zużycie planu w CU-h na 30 dni daje się więc oszacować wzorem 847 × liczba Plannerów + 168 × liczba Stakeholderów + 37 × liczba Viewerów. Liczba osób w poszczególnych rolach to jedno z pytań w rozdziale 7.

Z tej samej strony Learn wynika kilka rzeczy ważnych w praktyce [Learn]. Usunięcie planu nie kończy sesji, naliczają się do końca 30 dni. Gdy capacity zostanie wstrzymana albo usunięta, pozostałe CU aktywnych sesji trafiają na rachunek Azure. Udane zadanie automatyzacji w PowerTable lub Infobridge zużywa „2 CU” bez podanej jednostki czasu, nieudane nic nie kosztuje. Fabric SQL database, OneLake, operacje XMLA i pozostałe obciążenia zużywają capacity niezależnie od sesji planu.

Jedna niejasność dotyczy arkuszy PowerTable i intelligence sheets. Uwaga na stronie ról mówi, że ich tworzenie i edycja to aktywność Stakeholdera, która nie podnosi sesji do poziomu Plannera, a tabela niżej na tej samej stronie przypisuje tworzenie arkuszy Plannerowi [Learn]. Dopóki nie zostanie to wyjaśnione, bezpieczniej liczyć takie osoby jak Plannerów [wniosek].

Learn ostrzega, że małe capacity, takie jak F2 i F4, łatwo przeciążyć sesjami, zwłaszcza gdy korzystają z nich też inne obciążenia [Learn]. Arytmetyka to potwierdza, bo dwie sesje Plannera to 1 694 CU-h, a F2 daje przez 30 dni 1 460 CU-h [wniosek]. Administrator może ograniczyć przechodzenie na droższe sesje ustawieniami „Users can upgrade to a Planner session” i „Users can upgrade to a Stakeholder session”, a do tego włączyć Show Oversubscription Warning [Learn]. Na rachunku Azure zużycie planu widać w miernikach Fabric Planning - Planner Sessions, Stakeholder Sessions, Viewer Sessions i Automated Jobs [Learn].

### 5.3 Licencje użytkowników

Granicą jest rozmiar F64. Na mniejszej capacity każda osoba oglądająca treści Power BI potrzebuje licencji Pro, PPU albo indywidualnego triala, a od F64 wystarcza licencja Free z rolą Viewer [Learn]. Tworzenie i udostępnianie elementów Power BI, czyli na przykład raportów i modeli, poza My workspace wymaga Pro, PPU albo indywidualnego triala niezależnie od rozmiaru capacity [Learn]. Pozostałe elementy Fabric, takie jak lakehouse czy notatnik, użytkownik z licencją Free może tworzyć i udostępniać na capacity F albo próbnej [Learn]. PPU nie daje capacity, więc nie zastąpi F2 ani P1 [Learn]. Microsoft 365 E5 zawiera licencję Power BI Pro [Learn], co ma znaczenie, jeśli Fabrikam Fashion z niej korzysta.

Dwie kwestie Learn zostawia otwarte (7.2). Nie wiadomo, czy osoba, która tylko rozmawia z agentem opartym na modelu semantycznym, potrzebuje licencji Pro na capacity mniejszej od F64. Learn potwierdza jedynie, że jako uprawnienie wystarcza Read na modelu [Learn]. Brakuje też zestawienia, które łączyłoby trzy persony Planu z licencjami Free, Pro i PPU oraz z rozmiarem capacity. Obie kwestie trzeba potwierdzić dla konkretnej konfiguracji Fabrikam Fashion, zanim powstanie kalkulacja.

Kanały agenta mają własne wymagania. Integracja z Microsoft 365 Copilot przez Agent Store wymaga według Learn „Microsoft Copilot license or Office 365 commercial subscription” oraz licencji dla każdej osoby, która korzysta z agenta [Learn]. Osoby budujące agenta w Copilot Studio potrzebują licencji Microsoft 365 Copilot [Learn]. Agenci w Copilot Chat rozliczani według zużycia działają po skonfigurowaniu przez administratora subskrypcji Copilot Studio [Learn].

### 5.4 Region i zgodność

Agent i jego źródła muszą działać na capacity w tym samym regionie, inaczej agent nie wykona zapytania [Learn]. Ustawienia dzierżawy, które pozwalają przetwarzać i przechowywać dane wysłane do Azure OpenAI poza regionem capacity, są wymagane tylko wtedy, gdy capacity leży poza EU Data Boundary i poza USA [Learn]. Region West Europe znajduje się w Holandii, a EU Data Boundary obejmuje kraje UE i EFTA [Learn], więc dla capacity w tym regionie samo użycie agenta tych ustawień nie wymaga [wniosek]. To nie jest ocena zgodności dzierżawy Fabrikam Fashion.

Historia rozmów z agentem jest przechowywana do 28 dni, jeśli użytkownik nie usunie jej wcześniej, a zmiany ustawień dzierżawy mogą zacząć działać dopiero po godzinie [Learn]. Przy kanałach zewnętrznych, czyli Microsoft 365 Copilot, Copilot Studio, Foundry i innych klientach MCP, Learn ostrzega, że odpowiedzi agenta mogą opuścić granicę zgodności i region Fabric [Learn]. Ten temat trzeba omówić z działem bezpieczeństwa, zanim agent wyjdzie poza portal Fabric.

Planning jest dostępny we wszystkich regionach obsługujących Fabric [Learn]. Fabric Apps w preview nie są natomiast dostępne w regionie Poland Central [Learn], co trzeba wziąć pod uwagę, jeśli Fabrikam Fashion rozważa capacity w Polsce. Zużycie Copilota i agentów przez wybraną grupę użytkowników można też rozliczać na osobnej capacity oznaczonej jako Fabric Copilot capacity, co najmniej F2 albo P1, w regionie macierzystym dzierżawy [Learn]. Pozwala to oddzielić koszt AI od capacity, na której leżą dane.

## 6. Dalsze kroki: warianty pilotażu

Warianty różnią się zakresem i ilością pracy po stronie Fabrikam Fashion. Żadnego nie rekomendujemy z góry, bo wybór zależy od odpowiedzi na pytania z rozdziału 7.

### 6.1 Wariant A. Budżet kosztów w Planie

Pilotaż obejmuje jeden cykl budżetu kosztów dla kilku wybranych MPK centrali i przenosi do Planu ręczny obieg opisany w rozdziale 1. Kontroling przygotowuje strukturę w PowerTable zamiast w szablonie Excela. Właściciele MPK wpisują kwoty i komentarze bezpośrednio w planie, budżet przechodzi przez zdefiniowane poziomy akceptacji, a wersja uzgodniona trafia przez writeback do Fabric SQL database. Na warsztacie odpowiadają temu kroki P2 i P4.

To wariant najbliższy problemowi z rozdziału 1 i wymagający stosunkowo niewielu danych: struktury MPK i kont oraz wykonania i prognozy bieżącego roku. Pełny model rachunku wyników nie jest tu potrzebny. Słabą stroną jest koszt rosnący z liczbą osób, bo każdy właściciel MPK, który wprowadza dane, uruchamia sesję Stakeholdera za 168 CU-h na 30 dni. Otwarte zostają też licencje tych osób i odbiór budżetu przez system planistyczny. Wdrażanie planu przez Git i potoki wdrożeń jest wciąż w preview [Learn], więc przenoszenie gotowego planu między środowiskami trzeba będzie przećwiczyć.

Szybki start nie wymaga decyzji. Wystarczy pusty szablon budżetu z obecnego procesu i lista osób w poszczególnych rolach, żeby policzyć zużycie capacity wzorem z 5.2.

### 6.2 Wariant B. Agent danych na modelu Fabrikam Fashion

Punktem wyjścia jest zestaw 20-30 prawdziwych pytań kontrolingu z poprawnymi odpowiedziami. Agent powstaje na jednym istniejącym modelu semantycznym kontrolingu, a gdyby takiego nie było, na wąskim modelu zbudowanym na danych z hurtowni. Wynik mierzymy dwa razy, przed przygotowaniem modelu i po nim. W naszym teście oba modele mają te same tabele i dane, a model pod agentem przygotowanym różni się od surowego nazwami biznesowymi, opisami, miarami, oznaczoną tabelą dat i instrukcjami AI (załącznik A). We wcześniejszym przebiegu ta różnica wyraźnie poprawiła trafność odpowiedzi, a pomiar na obecnych danych jest [do ponownego przebiegu]. Agent przygotowany miał też własne instrukcje. Narzędzie generujące DAX je pomija [Learn], mogły więc wpłynąć najwyżej na formę odpowiedzi [wniosek]. Verified answers w teście nie było, dlatego ich wpływ trzeba zmierzyć osobno w pilotażu [wniosek].

Wariant daje szybki i mierzalny wynik na danych, które już są, i wprost odpowiada na pytanie o wiarygodność odpowiedzi AI. Przygotowany model przyda się też Copilotowi w raportach Power BI. Ma jednak swoje warunki. Agent potrzebuje płatnej capacity F2 lub P1 i nie działa na capacity próbnej, a polski nie jest językiem oficjalnie obsługiwanym [Learn]. Modele analityczne zbudowane poza Power BI trzeba najpierw przenieść albo odtworzyć jako model semantyczny [wniosek]. Przed szerszym udostępnieniem agenta trzeba też zdecydować o kanałach i o ograniczeniach dostępu na poziomie wierszy.

Zestaw pytań z odpowiedziami przyda się niezależnie od decyzji, dlatego można go zbierać od razu.

### 6.3 Wariant C. Wąski przepływ od danych do planu

Jedna marka w jednym kraju, ale cały przepływ: dane z hurtowni i systemu ERP w lakehouse, model Direct Lake, plan sprzedaży i kosztów na tym modelu, agent na tym samym modelu i zapis planu do bazy, z której czyta system planistyczny. Taki pilotaż najpełniej odpowiada na postulat z rozdziału 1, żeby historia i plan były w jednym miejscu.

Tylko ten wariant sprawdza integrację z systemami Fabrikam Fashion. Kosztem jest najwięcej pracy i najszersze grono osób: kontroling, IT, właściciele hurtowni i systemu planistycznego. Na wynik trzeba poczekać dłużej niż w A i B, a ryzyko leży głównie w dostępie do danych źródłowych i w odbiorze planu po stronie systemu planistycznego.

Pierwszym krokiem jest wskazanie tabel źródłowych dla wybranej marki i kraju oraz sposobu, w jaki można je odczytać.

### 6.4 Porównanie wariantów

| | A. Budżet kosztów w Planie | B. Agent na modelu Fabrikam Fashion | C. Wąski przepływ |
|---|---|---|---|
| Odpowiada na | ręczny obieg Exceli przy budżecie | wiarygodność odpowiedzi AI, pytania do danych zwykłym językiem | historię i plan w jednym miejscu |
| Dane od Fabrikam Fashion | struktura MPK i kont, wykonanie, prognoza | istniejący model albo dane z hurtowni, 20-30 pytań z odpowiedziami | dane źródłowe jednej marki w jednym kraju |
| Kto po stronie Fabrikam Fashion | kontroling, właściciele wybranych MPK | kontroling, właściciel modelu Power BI | kontroling, IT, właściciele hurtowni i systemu planistycznego |
| Główne ryzyko | licencje i koszt sesji przy wielu osobach | jakość odpowiedzi po polsku, wybór kanału i zgodność | integracja i czas |
| Pierwszy krok | pusty szablon budżetu i lista osób w rolach | zestaw pytań z odpowiedziami | lista tabel źródłowych i sposób dostępu |

A i B nie zależą od siebie i mogą iść równolegle, bo dotyczą innych procesów i innych danych. C ma sens jako drugi krok, gdy A albo B potwierdzą wartość [wniosek].

## 7. Luki i pytania

Scenariusz opiera się na danych syntetycznych, dokumentacji i testach w środowisku warsztatowym. Ten rozdział zbiera to, czego nie wiemy o Fabrikam Fashion, czego Learn nie rozstrzyga i czego nie sprawdziliśmy. Żadnej z tych luk nie wypełniliśmy szacunkiem.

### 7.1 Pytania do Fabrikam Fashion

| Nr | Pytanie | Do czego potrzebna odpowiedź |
|---:|---|---|
| 1 | Czy Fabrikam Fashion ma capacity Fabric albo Power BI Premium? Jakiego rozmiaru i w którym regionie? | wybór wariantu pilotażu, zużycie capacity przez Plan (5.2), region agenta i źródeł (5.4) |
| 2 | Jakie licencje mają osoby z kontrolingu i finansów oraz właściciele MPK: Free, Pro, PPU, Microsoft 365 E5, Microsoft 365 Copilot? | wymagania licencyjne poniżej i powyżej F64 (5.3), dostępne kanały agenta |
| 3 | Ile osób w procesie budżetu buduje plany, ile wprowadza lub akceptuje dane, a ile tylko je przegląda? | liczba sesji Planner, Stakeholder i Viewer we wzorze z 5.2 |
| 4 | Kiedy zaczyna się cykl budżetowy na 2027/28 i przez ile poziomów akceptacji przechodzi budżet? | termin wariantu A, konfiguracja akceptacji w Planie |
| 5 | Na jakim poziomie szczegółowości powstają plan sprzedaży i budżet kosztów: sklep czy kraj, miesiąc czy tydzień, konto czy grupa kont? | budowa modelu i arkuszy, limity Planu |
| 6 | Jak system planistyczny przyjmuje dziś dane, kto za niego odpowiada i czy może czytać z bazy SQL? | odbiór planu zapisanego przez writeback (P4, wariant C) |
| 7 | Na jakiej technologii działają hurtownia i istniejące modele analityczne? Które modele Power BI kontrolingu już istnieją? | wybór modelu dla agenta (wariant B), sposób zasilenia lakehouse'u |
| 8 | W jaki sposób można odczytać dane z systemu ERP, np. przez widoki w bazie, eksport plików albo API? | wariant C, zasilanie lakehouse'u |
| 9 | Czy dostęp do danych kontrolingu jest dziś ograniczany na poziomie wierszy, np. według marki, kraju albo MPK? | zabezpieczenia na poziomie wierszy w modelu; Plan pobiera wiersze według uprawnień zalogowanej osoby [Learn], a agent w Copilot Studio w trybie Maker pokazuje dane z uprawnieniami twórcy [Learn]; przy modelu Direct Lake ze stałą tożsamością reguły trzeba zapisać w modelu (P0) [Learn] |
| 10 | W jakim języku użytkownicy będą rozmawiać z agentem? | polski nie jest oficjalnie obsługiwany (4.3), zakres testów w wariancie B |
| 11 | Jakie zasady obowiązują w Fabrikam Fashion przy udostępnianiu danych finansowych w Microsoft 365 Copilot, Teams i narzędziach zewnętrznych? | wybór kanału agenta (A3, 5.4) |
| 12 | Kto zarządza ustawieniami dzierżawy Fabric i ustawieniami capacity? | ustawienia z 5.1, które trzeba włączyć przed pilotażem |
| 13 | Czy w pilotażu ma uczestniczyć partner wdrożeniowy, a jeśli tak, w jakim zakresie? | podział pracy i harmonogram |
| 14 | Czy kontroling przygotuje 20-30 prawdziwych pytań z poprawnymi odpowiedziami? | zestaw testowy agenta i pomiar przed przygotowaniem modelu i po nim (6.2) |

### 7.2 Czego nie rozstrzyga dokumentacja

| Luka | Co wiadomo [Learn] | Jak domknąć |
|---|---|---|
| Licencja osoby, która na capacity mniejszej od F64 tylko rozmawia z agentem | do zadawania pytań wystarcza uprawnienie Read na modelu; Learn nie mówi, czy taka rozmowa jest oglądaniem treści Power BI, które wymaga Pro | potwierdzenie w Microsoft dla konfiguracji Fabrikam Fashion, test z kontem Free |
| Licencje person Planu | znane są persony i ich CU-h; brakuje zestawienia person z licencjami Free, Pro i PPU oraz z progiem F64 | potwierdzenie w Microsoft przed kalkulacją |
| Rola potrzebna do zbudowania planu | tutorial wymaga Member albo Admin, strona ról przypisuje Plannerowi także Contributor | test z kontem w roli Contributor w pilotażu |
| Persona przy pracy w PowerTable | uwaga na stronie ról mówi o Stakeholderze, tabela na tej samej stronie o Plannerze | potwierdzenie w Microsoft; do tego czasu liczyć jak Plannera |
| Jednostka „2 CU” za zadanie automatyzacji | Learn podaje „2 CU” bez jednostki czasu | potwierdzenie w Microsoft, w pilotażu odczyt miernika Automated Jobs |
| Wersje i snapshoty zwykłego arkusza planistycznego | Learn wymienia „Version management and snapshots”, ale nie opisuje procedury ani przechowywania | test w pilotażu i potwierdzenie w Microsoft |
| Połączenie planu z modelem Direct Lake | strona o tworzeniu arkusza mówi, że plan łączy się z modelem tożsamością zalogowanej osoby, bez współdzielonego połączenia chmurowego; strona kodów błędów wymaga dla modelu Direct Lake połączenia ze stałą tożsamością. U nas plan podłączył się dopiero po ustawieniu takiego połączenia [test] | potwierdzenie w Microsoft; w pilotażu test na modelu Fabrikam Fashion w docelowym trybie przechowywania |
| Zapis planu do miejsca innego niż Fabric SQL database | writeback jest udokumentowany tylko do Fabric SQL database | odczyt z tej bazy przez system planistyczny albo hurtownię (pytanie 6) |
| Działanie instrukcji AI po wdrożeniu przez Git albo potok | model trzeba odświeżyć w usłudze, a dla Direct Lake Learn dodaje „but only once a day” | sprawdzenie w Prep data for AI po każdym wdrożeniu |
| Pełny format folderu Copilot w definicji modelu | Learn pokazuje folder w definicji REST, bez kompletnego opisu plików; nasz folder Fabric przyjął [test] | eksport definicji z modelu skonfigurowanego w portalu i porównanie |
| Definicje elementów Plan i Data agent w API | przykłady w specyfikacjach są niespójne, np. lakehouse-tables obok lakehouse_tables | eksport definicji z działającego elementu i użycie jej jako wzorca |

### 7.3 Czego nie sprawdziliśmy

Kroki oznaczone [do próby] w chwili przygotowania dokumentu nie były sprawdzone, bo część z nich wymaga elementów tworzonych ręcznie tuż przed warsztatem. Należą do nich prognoza na kalendarzu finansowym, blokada pojedynczego kraju przed ponownym rozkładem, przejścia statusów akceptacji, układ kolumn tabel tworzonych przez import do PowerTable i przez writeback, wymiar scenariusza w SM_Planowanie, edycja modelu w przeglądarce, widok kroków agenta, Copilot w raporcie i Analyze in Excel. Kanałów Microsoft 365 Copilot i Copilot Studio w ogóle nie testowaliśmy. Połączenie ze stałą tożsamością dla SM_Planowanie sprawdziliśmy tylko z uwierzytelnianiem OAuth 2.0, bez jednostki usługi i tożsamości obszaru roboczego.

Wynik agentów ma swoje granice. Test na obecnych danych jest jeszcze przed nami [do ponownego przebiegu], a we wcześniejszym przebiegu każde pytanie padło tylko raz, przy czym pięć z czternastu ma podpowiedź (załącznik A). Verified answers ani oznaczenia Approved for Copilot nie skonfigurowaliśmy. Fabric przyjął folder Copilot z instrukcjami AI w definicji modelu [test], ale po takim wdrożeniu Learn wymaga odświeżenia modelu [Learn], więc nie mamy pewności, czy agent w teście z tych instrukcji korzystał [wniosek]. Przyczyny dwóch przerwań agenta bez przygotowania we wcześniejszym przebiegu nie ustaliliśmy.

## Załącznik A. Test agentów danych

Skrypt `fabric/deploy/testuj_agenta.py` zadaje każde z 14 pytań obu opublikowanym agentom przez ich punkt końcowy MCP, po jednym razie. Odpowiedzi ocenia się ręcznie, porównując je z kluczem w `dane/oczekiwane_odpowiedzi.md`. Pełne odpowiedzi trafiają do pliku `dokumentacja/wyniki_testu_agentow.md`, a kontrole miar DAX obu modeli z wartościami oczekiwanymi do `dokumentacja/wyniki_weryfikacji_dax.md`. Oba pliki zawierają dziś tylko informację, że przebieg na obecnych danych trzeba wykonać od nowa [do ponownego przebiegu].

W kluczu pięć pytań (3, 8, 11, 13 i 14) kończy się nawiasem z podpowiedzią. Jest w nim opis oczekiwanej odpowiedzi, sposób liczenia albo uwaga, że agent nie powinien zgadywać. Obaj agenci dostają dokładnie te same brzmienia, więc porównanie między nimi jest uczciwe, ale wynik agenta przygotowanego wypada przez to lepiej, niż wypadłby w zwykłej rozmowie. Tabela A.1 podaje pytania bez nawiasów.

### A.1 Pytania i oczekiwane odpowiedzi

| Nr | Pytanie | Oczekiwana odpowiedź |
|---:|------------------------------------------|------------------------------|
| 1 | Jaka była sprzedaż netto grupy w 2Q 2026/27 i jak wypadła względem budżetu? | ACT 213 602 803 wobec BUD 220 491 560, odchylenie -6 888 757 (-3,1%) |
| 2 | Która marka ma największe procentowe odchylenie sprzedaży od budżetu narastająco w RF 2026/27 (kwiecień do listopada)? Podaj odchylenia wszystkich marek w PLN i %. | Kroko -7,7% (-8 352 tys. PLN); Vento -6,2%, Aurea -0,6%, Lumi +4,8% |
| 3 | Dlaczego Vento w Niemczech jest poniżej budżetu w 1H 2026/27? | -7 341 tys. PLN (-14,4%); cztery sklepy, SK-VEN-DE-009 do 012, otwarte później niż w planie |
| 4 | Które 5 sklepów ma największe przekroczenie kosztów czynszu względem budżetu w RF 2026/27 (kwiecień do listopada)? | pięć sklepów Aurea w Austrii, od SK-AUR-AT-002 (+97 tys. PLN) do SK-AUR-AT-005 (+56 tys. PLN), każdy +11,7% |
| 5 | Jak zmieniła się sprzedaż odzieży wierzchniej w listopadzie 2026 r/r, w podziale na marki? | z 14 926 tys. do 10 761 tys. PLN (-27,9%); Aurea -29,4%, Vento -26,9% |
| 6 | Jak zmieniał się udział e-commerce w sprzedaży grupy w kolejnych latach finansowych? | 18,0%, 19,0%, 20,6% i 23,1% w latach 2023/24-2026/27; ostatni rok obejmuje 8 miesięcy |
| 7 | Ile wyniosła sprzedaż grupy w Black Friday 2025 i ile to razy więcej niż średnia z pozostałych piątków listopada 2025? | 7 388 tys. PLN, 2,10 raza więcej niż średnia 3 510 tys. PLN |
| 8 | Jaki był koszt logistyki e-commerce na jedno zamówienie w Niemczech w październiku i listopadzie 2026 w porównaniu z budżetem? | październik ACT 30,95 i BUD 24,68 PLN, listopad ACT 30,95 i BUD 25,51 PLN |
| 9 | Jaka jest prognoza EBITDA grupy na RF 2026/27 (FC 8+4) i jak wypada względem budżetu? | FC 149 380 tys. wobec BUD 161 951 tys. PLN, -12 570 tys. (-7,8%) |
| 10 | Które 5 sklepów Kroko ma najniższą marżę brutto % w RF 2026/27 (kwiecień do listopada)? | od SK-KRO-PL-016 (52,0%) do SK-KRO-SE-001 (52,7%) |
| 11 | Jaka była dynamika sprzedaży LFL Kroko w 2Q 2026/27? | 38 sklepów LFL, z 30 471 tys. do 28 319 tys. PLN, -7,1% |
| 12 | Ile wyniosły koszty IT i licencji (konto 5420) w RF 2025/26 w porównaniu z RF 2024/25? | z 10 835 tys. do 11 485 tys. PLN (+6,0%) |
| 13 | Jaka będzie sprzedaż w 2029 roku? | odmowa, bo dla 2029 nie ma danych |
| 14 | Jaka jest sprzedaż w bieżącym kwartale? | niepełny 3Q 2026/27: 175 615 655 z października i listopada oraz 30 658 591 z 1-8 grudnia, razem 206 274 245 |

### A.2 Ocena odpowiedzi

Ocena odpowiedzi i czasy z wcześniejszego przebiegu dotyczyły innej wersji danych syntetycznych, dlatego je usunęliśmy. Po wdrożeniu obecnych danych trzeba uruchomić `python fabric\deploy\testuj_agenta.py`, ocenić odpowiedzi według tabeli A.1 i uzupełnić ten punkt [do ponownego przebiegu].

Z tamtego przebiegu zostają obserwacje jakościowe, które warto sprawdzić ponownie. Agent przygotowany odpowiadał poprawnie na większość pytań, a jego błędy dotyczyły głównie okresu (sprzedaż za kilka miesięcy opisana jako półrocze) i pojedynczego miesiąca w pytaniu o koszt zamówienia. Agent bez przygotowania mylił scenariusze, sumując wykonanie z budżetem, wybierał MPK e-commerce zamiast sklepów, zwracał puste tabele i dwa razy przerwał pracę z błędem technicznym. Pytanie o przyczynę odchylenia zadane bez podpowiedzi dało u agenta przygotowanego tabelę z wierszem Razem mieszającym przychody z kosztami, co opisuje krok A2.

## Załącznik B. Repozytorium i odtworzenie środowiska

Repozytorium mieści generator danych, gotowe dane, definicje modeli, skrypty wdrożenia i testów oraz ten dokument.

```text
README.md
dane/
  csv/                        14 tabel w CSV
  parquet/                    te same tabele w Parquet, z nich powstaje lakehouse
  excel/                      5 plików z punktu 3.4
  SLOWNIK_DANYCH.md           opis tabel i kolumn
  oczekiwane_odpowiedzi.csv   klucz 14 pytań testowych, obok wersja .md
generator/                    generator danych syntetycznych, walidacja, opis w SPEC.md
fabric/
  semantic_model/             TMDL trzech modeli, build_tmdl.py, instrukcje AI w prep_for_ai/
  data_agent/                 instrukcje agenta danych
  plan/                       klucz alokacji celu 2027/28, skrypt pliku awaryjnego
  deploy/                     wdrożenie, kontrole DAX, test agentów przez MCP
dokumentacja/                 scenariusz, wyniki testów, eksport do docx
```

Polecenia uruchamia się z katalogu głównego repozytorium, w kolejności z tabeli.

| Cel | Polecenie |
|---|---|
| tabele w dane/csv i dane/parquet, cztery pliki Excel, słownik danych i klucz odpowiedzi | `python generator\generate_data.py` |
| walidacja danych i porównanie dwóch przebiegów generatora | `python generator\validate.py --determinism` |
| definicje TMDL trzech modeli, dla SM_Kontroling razem z folderem Copilot | `python fabric\semantic_model\build_tmdl.py` |
| klucz alokacji celu 2027/28, z którego korzysta weryfikacja modelu | `python fabric\plan\klucz_alokacji_2027_28.py` |
| plik awaryjny Planu | `python fabric\plan\excel_awaryjny_planu.py` |
| wdrożenie do Fabric | `python fabric\deploy\deploy.py` |
| kontrole DAX wdrożonych modeli, wynik w dokumentacja\wyniki_weryfikacji_dax.md | `python fabric\deploy\weryfikuj_model.py` |
| test agentów przez MCP | `python fabric\deploy\testuj_agenta.py` |
| eksport scenariusza do docx | `python dokumentacja\eksport_docx.py` |

Skrypty sprawdziliśmy na Pythonie 3.13 w Windows [test]. Generator potrzebuje pakietów z pliku generator\requirements.txt (pandas, numpy, pyarrow, openpyxl). Wdrożenie wymaga dodatkowo pakietu requests, test agentów pakietu mcp, a eksport scenariusza do docx programu pandoc. Skrypty z katalogu fabric\deploy pobierają token przez Azure CLI, więc najpierw trzeba się zalogować poleceniem az login na koncie, które może tworzyć obszary robocze w docelowej dzierżawie.

Nazwę obszaru roboczego ustawia zmienna FABRIC_WORKSPACE, domyślnie Fabrikam Kontroling Warsztat. Zmienna FABRIC_CAPACITY_ID wskazuje capacity i jest potrzebna, gdy obszar trzeba dopiero utworzyć. Jeśli obszar już istnieje na innej capacity, skrypt przepnie go na wskazaną. Identyfikatory utworzonych elementów trafiają do pliku fabric\deploy\.stan_wdrozenia.json, który nie jest wersjonowany, a korzystają z niego weryfikuj_model.py i testuj_agenta.py.

Skrypt deploy.py ma dziewięć kroków: obszar, lakehouse, pliki, tabele, sql, modele, odswiez, sqldb i agenci. Przełącznik --kroki uruchamia tylko wybrane, na przykład `--kroki modele,odswiez` po zmianie TMDL. Przełącznik --tryb-direct-lake ustawia modele na Direct Lake przez punkt końcowy SQL (wartość sql, domyślna) albo na Direct Lake on OneLake (wartość onelake). Środowisko warsztatowe działa w pierwszym z tych trybów.

Pełny przebieg testuj_agenta.py, czyli wszystkie pytania zadane obu agentom, nadpisuje dokumentacja\wyniki_testu_agentow.md razem z ręczną oceną odpowiedzi, którą trzeba wtedy przygotować od nowa. Gdy przebieg zawęża --pytania (np. `--pytania 1,3,13`) albo --agent, odpowiedzi trafiają tylko na ekran. Tak samo działa --pytanie, które pozwala zadać agentowi własne pytanie. Skrypt validate.py z przełącznikiem --determinism uruchamia generator dwa razy i porównuje sumy SHA256 plików Parquet. W naszym przebiegu pliki były identyczne.

Po skrypcie zostaje kilka kroków ręcznych.

1. Ustawienia dzierżawy i capacity z punktu 5.1. Zmiany w ustawieniach dzierżawy mogą zacząć działać dopiero po godzinie [Learn].
2. Połączenie chmurowe ze stałą tożsamością dla SM_Planowanie i Plan_Kontroling według kroku P0. Krok modele w deploy.py sprawdza po każdym przebiegu, czy SM_Planowanie nadal korzysta z takiego połączenia, i ostrzega, gdy go brakuje.
3. Raport_Kontroling, jeśli w bloku 4 ma się pojawić Copilot w raporcie.
4. Kontrola instrukcji AI w Prep data for AI na SM_Kontroling. Skrypt ostrzega, gdy Fabric nie zachowa folderu Copilot w definicji modelu, ale instrukcje warto obejrzeć także bez ostrzeżenia. Jeśli ich brakuje, wkleja się treść pliku fabric\semantic_model\prep_for_ai\SM_Kontroling_instructions.md.
5. Verified answers i oznaczenie Approved for Copilot, o ile mają być częścią pokazu. W środowisku warsztatowym ich nie ma (7.3).

Po wdrożeniu zmian przez Git albo potok wdrożeń Learn wymaga odświeżenia modelu w usłudze, żeby zsynchronizować ustawienia AI, a dla modeli DirectQuery i Direct Lake dodaje zastrzeżenie „but only once a day” [Learn]. Wdrożenie przez API definicji traktujemy tak samo [wniosek]. Krok odswiez wykonuje takie odświeżenie po każdym wdrożeniu, ale instrukcje zmieniane kilka razy w ciągu dnia mogą nie od razu dotrzeć do Copilota i agenta [wniosek].

Dlaczego Plan nie powstaje ze skryptu, wyjaśnia punkt 3.5.

Skrypt eksport_docx.py tworzy z tego pliku dokumentacja\docx\Scenariusz_warsztatu.docx. Przełącznik --sprawdz-w-wordzie otwiera gotowy plik w Wordzie tylko do odczytu, podaje liczbę stron, tabel i łączy i niczego nie zapisuje.

## Załącznik C. Źródła w Microsoft Learn

Strony przejrzeliśmy w dniach poprzedzających warsztat. Statusy GA i preview zmieniają się dość często, dlatego przed decyzją o pilotażu warto je sprawdzić ponownie.

Plan w Fabric IQ

- <https://learn.microsoft.com/fabric/iq/plan/overview>
- <https://learn.microsoft.com/fabric/iq/plan/planning-overview>
- <https://learn.microsoft.com/fabric/iq/plan/overview-limitations>
- <https://learn.microsoft.com/fabric/iq/plan/overview-prerequisites>
- <https://learn.microsoft.com/fabric/iq/plan/overview-roles>
- <https://learn.microsoft.com/fabric/iq/plan/planning-how-to-get-started>
- <https://learn.microsoft.com/fabric/iq/plan/planning-how-to-input-data>
- <https://learn.microsoft.com/fabric/iq/plan/planning-how-to-set-up-scenarios>
- <https://learn.microsoft.com/fabric/iq/plan/planning-how-to-use-simulation-measures>
- <https://learn.microsoft.com/fabric/iq/plan/planning-how-to-insert-columns/how-to-insert-data-input-columns>
- <https://learn.microsoft.com/fabric/iq/plan/planning-how-to-write-back-data>
- <https://learn.microsoft.com/fabric/iq/plan/planning-concept-writeback>
- <https://learn.microsoft.com/fabric/iq/plan/planning-concept-allocation-rules-controls>
- <https://learn.microsoft.com/fabric/iq/plan/planning-concept-predict>
- <https://learn.microsoft.com/fabric/iq/plan/planning-forecasting/planning-how-to-build-forecasts>
- <https://learn.microsoft.com/fabric/iq/plan/planning-forecasting/planning-how-to-extend-time>
- <https://learn.microsoft.com/fabric/iq/plan/planning-forecasting/planning-how-to-generate-statistical-forecasts-using-predict-feature>
- <https://learn.microsoft.com/fabric/iq/plan/planning-tutorial/planning/tutorial-0-introduction>
- <https://learn.microsoft.com/fabric/iq/plan/planning-tutorial/planning/tutorial-1-allocation-collaboration>
- <https://learn.microsoft.com/fabric/iq/plan/planning-tutorial/intelligence/tutorial-11-planning-sheet-powertable-canvas>
- <https://learn.microsoft.com/fabric/iq/plan/powertable-how-to-create-table-app>
- <https://learn.microsoft.com/fabric/iq/plan/powertable-how-to-insert-rows-import-data>
- <https://learn.microsoft.com/fabric/iq/plan/infobridge-how-to-create-bridge>
- <https://learn.microsoft.com/fabric/iq/plan/infobridge-how-to-write-back-data>
- <https://learn.microsoft.com/fabric/iq/plan/intelligence-how-to-get-started>
- <https://learn.microsoft.com/fabric/iq/plan/resources/billing-fabric-plan>
- <https://learn.microsoft.com/fabric/iq/plan/resources/error-codes-and-resolutions>

Agent danych Fabric

- <https://learn.microsoft.com/fabric/data-science/concept-data-agent>
- <https://learn.microsoft.com/fabric/data-science/how-to-create-data-agent>
- <https://learn.microsoft.com/fabric/data-science/data-agent-add-datasources>
- <https://learn.microsoft.com/fabric/data-science/data-agent-configurations>
- <https://learn.microsoft.com/fabric/data-science/data-agent-configuration-best-practices>
- <https://learn.microsoft.com/fabric/data-science/data-agent-example-queries>
- <https://learn.microsoft.com/fabric/data-science/data-agent-schema-object-descriptions>
- <https://learn.microsoft.com/fabric/data-science/data-agent-sharing>
- <https://learn.microsoft.com/fabric/data-science/data-agent-tenant-settings>
- <https://learn.microsoft.com/fabric/data-science/data-agent-mcp-server>
- <https://learn.microsoft.com/fabric/data-science/data-agent-microsoft-365-copilot>
- <https://learn.microsoft.com/fabric/data-science/data-agent-microsoft-copilot-studio>
- <https://learn.microsoft.com/fabric/data-science/data-agent-microsoft-copilot-studio-tool>
- <https://learn.microsoft.com/fabric/data-science/fabric-data-agent-sdk>
- <https://learn.microsoft.com/fabric/data-science/semantic-model-best-practices>
- <https://learn.microsoft.com/azure/foundry/agents/how-to/tools/fabric>
- <https://learn.microsoft.com/azure/foundry/agents/how-to/tools/fabric-iq>

Copilot i przygotowanie modelu dla AI

- <https://learn.microsoft.com/power-bi/create-reports/copilot-introduction>
- <https://learn.microsoft.com/power-bi/create-reports/copilot-prepare-data-ai>
- <https://learn.microsoft.com/power-bi/explore-reports/copilot-chat-with-data-standalone>
- <https://learn.microsoft.com/fabric/iq/connectors/copilot-power-bi-fabric>
- <https://learn.microsoft.com/fabric/enterprise/fabric-copilot-capacity>

Raporty i aplikacje

- <https://learn.microsoft.com/power-bi/create-reports/fabric-apps-analytics>
- <https://learn.microsoft.com/power-bi/create-reports/translytical-task-flow-overview>
- <https://learn.microsoft.com/power-bi/explore-reports/end-user-apps>
- <https://learn.microsoft.com/power-bi/explore-reports/org-app-items>
- <https://learn.microsoft.com/fabric/apps/overview>
- <https://learn.microsoft.com/fabric/apps/pricing>
- <https://learn.microsoft.com/fabric/fundamentals/track-visualize-data>
- <https://learn.microsoft.com/fabric/data-engineering/user-data-functions/user-data-functions-overview>

Dane, Excel i OneLake

- <https://learn.microsoft.com/power-bi/collaborate-share/service-analyze-in-excel>
- <https://learn.microsoft.com/power-query/connectors/excel>
- <https://learn.microsoft.com/fabric/data-factory/create-first-dataflow-gen2>
- <https://learn.microsoft.com/fabric/data-engineering/load-to-tables>
- <https://learn.microsoft.com/fabric/onelake/onelake-file-explorer>
- <https://learn.microsoft.com/fabric/onelake/onelake-file-explorer-release-notes>
- <https://learn.microsoft.com/fabric/onelake/quickstart-get-data>
- <https://learn.microsoft.com/fabric/fundamentals/direct-lake-overview>
- <https://learn.microsoft.com/fabric/fundamentals/direct-lake-security-integration>
- <https://learn.microsoft.com/power-bi/connect-data/service-connect-cloud-data-sources>

Licencje, rozliczenia i regiony

- <https://learn.microsoft.com/fabric/enterprise/licenses>
- <https://learn.microsoft.com/fabric/enterprise/azure-billing>
- <https://learn.microsoft.com/fabric/enterprise/powerbi/service-admin-power-bi-licensing>
- <https://learn.microsoft.com/fabric/admin/region-availability>
- <https://learn.microsoft.com/azure/reliability/regions-list>
- <https://learn.microsoft.com/privacy/eudb/eu-data-boundary-learn>
- <https://learn.microsoft.com/microsoft-365/copilot/agent-essentials/m365-agents-admin-guide>
- <https://learn.microsoft.com/fabric/fundamentals/whats-new>

Definicje elementów, API i CI/CD

- <https://learn.microsoft.com/rest/api/fabric/articles/item-management/definitions/item-definition-overview>
- <https://learn.microsoft.com/rest/api/fabric/articles/item-management/definitions/plan-definition>
- <https://learn.microsoft.com/rest/api/fabric/articles/item-management/definitions/data-agent-definition>
- <https://learn.microsoft.com/rest/api/fabric/articles/item-management/definitions/semantic-model-definition>
- <https://learn.microsoft.com/rest/api/fabric/core/items/create-item>
- <https://learn.microsoft.com/rest/api/fabric/core/items/get-item-definition>
- <https://learn.microsoft.com/rest/api/fabric/core/items/update-item-definition>
- <https://learn.microsoft.com/rest/api/fabric/semanticmodel/items/update-semantic-model-definition>
- <https://learn.microsoft.com/rest/api/fabric/core/connections/create-connection>
- <https://learn.microsoft.com/fabric/cicd/git-integration/intro-to-git-integration>
- <https://learn.microsoft.com/fabric/cicd/deployment-pipelines/intro-to-deployment-pipelines>
- <https://learn.microsoft.com/power-bi/developer/projects/projects-dataset>
