# Generator danych warsztatowych

Dane są w pełni syntetyczne i wymyślone. Nie przedstawiają wyników żadnej firmy, a skala jest umowna. Kontrakt tabel znajduje się w `SPEC.md`.

## Uruchomienie

Z katalogu głównego projektu:

```powershell
python generator\generate_data.py
python generator\validate.py
```

Pełna weryfikacja z dwoma uruchomieniami z innego katalogu:

```powershell
python generator\validate.py --determinism
```

Skrypty odnajdują katalog projektu względem własnego pliku, więc działają również po podaniu pełnej ścieżki z innego katalogu. Wymagane pakiety są wymienione w `requirements.txt`. Generator niczego nie pobiera ani nie instaluje.

Wyniki trafiają do `dane\parquet`, `dane\csv` oraz `dane\excel`. Fakt dzienny ma CSV skompresowany gzip; pozostałe CSV mają BOM UTF-8. Każdy Parquet używa kompresji snappy i dat date32. W `dane` powstają także słownik i obliczony klucz 14 odpowiedzi w Markdown oraz CSV.

## Parametry i kod

`config.py` zawiera ziarno 731905, parametry ekonomiczne, otwarcia, zamknięcia i parametry historii. Po zmianie należy uruchomić generator i walidator; samo wyjście generatora nie oznacza przejścia testów.

`kalendarz.py` wyznacza RF oraz święta z algorytmem Wielkanocy. `wymiary.py` buduje sieć. `model.py` liczy wektorowo siatkę dzienną i fakty miesięczne. `schemat.py` jest jawnym kontraktem typów i kolumn. `eksport.py` zapisuje pliki, a `odpowiedzi.py` oblicza odpowiedzi z gotowych tabel.

Rok finansowy zaczyna się 1 kwietnia (`FY_START_MONTH`). Wymiar marki zawiera cztery marki handlowe oraz techniczny GRP dla centrali bez marki. GRP nie występuje w agregatach sprzedaży ani celach. Kolumna `kwartal_finansowy_sort` umożliwia sortowanie kwartałów między latami.

`plan_kalendarz` jest osobnym kalendarzem miesięcznym dla `SM_Planowanie`. Zawiera 60 miesięcy od kwietnia 2023 do marca 2028, daty date32 oraz wyłącznie tekst ASCII. Atrybuty finansowe i zamknięcie miesiąca pochodzą z `dim_data`; skróty miesięcy mają postać `Kwi`, `Maj`, `Paz` itd.

## Jawne decyzje modelowe

Budżet roku N używa rocznej sprzedaży ACT roku poprzedniego, po uwzględnieniu czasu działalności i rozruchu. Rozkład miesięczny pochodzi z gładkiego profilu sezonowości, dni tygodnia, promocji i kalendarza handlowego, bez nowego szumu. Dla nowych sklepów bazą jest średnia sprzedaż na m2 porównywalnych sklepów tej samej marki i kraju. Daty planowane sterują BUD, rzeczywiste ACT i rozruchem FC. Znane zamknięcia obowiązują we wszystkich scenariuszach.

Wzrost BUD sklepów wynosi dla AUR, VEN, LUM i KRO odpowiednio 3%, 6%, 4% i 2%; e-commerce 13%. Wzrost czynszów i kosztu zamówienia to 3%. Płace rosną o 7%, media i pozostałe stałe koszty o 3%, IT i marketing centrali o 6%. Czynsze i koszty stałe są proporcjonalne do kalendarzowych dni działalności w miesiącu. Konto 6010 nie wchodzi do EBITDA.

Sieć aktywna odpowiada liczebnościom SPEC.md. Dodatkowe pięć MPK zachowuje historię zamknięć. Cztery opóźnione sklepy Vento DE mają powierzchnie od 650 do 900 m2. Siedem sklepów na RF 2027/28 pozostaje wyłącznie w wymiarze i wejściu planistycznym.

LFL zaczyna się po 12 pełnych miesiącach: dla otwarcia 1 maja jest to 1 maja rok później; dla otwarcia 15 maja jest to 1 czerwca rok później. Data zamknięcia oznacza ostatni dzień działalności, włącznie.

Reguły niedziel handlowych odczytano literalnie z uproszczenia SPEC.md. Dlatego 24.12.2023 jest dniem handlowym z połową wagi sprzedaży. Nie jest to odwzorowanie szczególnych przepisów konkretnego roku. Poza Polską wolne są tylko Nowy Rok, Boże Narodzenie i Wielkanoc.

Kategorie mają wspólną marżę w obrębie miesiąca, marki, kraju i kanału. Podział sprzedaży, kosztu i sztuk jest uzgodniony co do grosza i sztuki. Kursy walut są informacyjne i zachowują sześć miejsc dziesiętnych; nie zaokrągla się kursów SEK i DKK do dwóch miejsc.

Arkusze używają kodów marek i krajów. Procenty zapisano jako ułamki. Plik celów ma zaokrąglone wartości, natomiast szablon kosztów ma puste miesiące i rzeczywiste formuły `SUM`, przeliczane przez Excel po otwarciu. Pośrednie XML openpyxl są tworzone wyłącznie w katalogu projektu i usuwane po zapisie.

Oddzielny `budzet_opex_centrala_2027_28_import.xlsx` zawiera arkusze `Import` i `Opis`. Ma 45 wierszy kosztów oraz 19 nagłówków ASCII, bez formuł i kolumny sumy. Projekt miesięczny to FC / 12 × (1 + indeksacja), zaokrąglony do 100 PLN: 6% dla konta 5410, 3% dla pozostałych. Wyłącznie wiersz `HQ-TEC` × `5420` dostaje w październiku dodatkowe 180 000 PLN z komentarzem o odnowieniu licencji. To jedyna dopłata i jedyny niepusty komentarz w pliku. Pozostałe MPK konta 5420 mają w październiku zwykłą bazę miesięczną. To roboczy projekt importowy, nie zmiana faktów ani dotychczasowego szablonu.

Przy ponownym uruchomieniu generator nie przepisuje istniejącego Excela, jeśli treść jest identyczna poza technicznym czasem zapisania. Chroni to oryginalne pliki przed zmianami wynikającymi wyłącznie z metadanych ZIP i openpyxl.

## Kontrola

Walidator jest zwykłym skryptem Python, nie wymaga pytest. Sprawdza kontrakt Parquet, klucze, kalendarz, uzgodnienia, scenariusze, wszystkie historie, wejścia Excel, klucz odpowiedzi i rozmiar. Kod wyjścia 0 oznacza wyłącznie wyniki PASS. Kwoty grupowe w kluczu zaokrąglane są do tysięcy, koszty jednostkowe do groszy.

Tabela testów jest zapisywana w `generator\wyniki_walidacji.csv`. Opcja `--determinism` zapisuje dodatkowo czasy i skróty SHA256 obu uruchomień w `generator\weryfikacja_deterministycznosci.json`. Zestaw zawiera 14 tabel, a klucz odpowiedzi 14 pytań.

Deterministyczność można potwierdzić przez porównanie SHA256 plików Parquet przed i po ponownym uruchomieniu. Ziarno, kolejność generowania i sortowania są stałe; dwa uruchomienia na tej samej wersji bibliotek dają identyczne pliki. Przy niezmienionej treści arkuszy generator zachowuje istniejące pliki Excel bez przepisywania.

Brak danych klienta, rzeczywistych stawek licencyjnych, VAT, zwrotów, zapasów i cash flow. Model nie służy do prognozowania wyników rzeczywistej firmy.
