# Klucz alokacji celu 2027/28 (scenariusz P1)

Plik generuje `fabric/plan/klucz_alokacji_2027_28.py`. Dane są syntetyczne.

Prowadzący wstawia w Planie kolumnę liczbową `Plan 2027/28` z opcją kopiowania wartości z miary `Sprzedaz ACT 2025/26`, a następnie wpisuje cel marki w wierszu sumy marki. Rozkład proporcjonalny do wartości istniejących w kolumnie opisuje samouczek Planning w Microsoft Learn. Dokładne zachowanie zaokrągleń w Planie trzeba potwierdzić przed warsztatem, dlatego kwoty poniżej traktujemy jako punkt odniesienia z dokładnością do pojedynczych złotych.

## Cele do wpisania w wierszach marek

| Marka | ACT 2025/26 (PLN) | Cel 2027/28 do wpisania (PLN) | Zmiana wobec ACT 2025/26 |
|---|---:|---:|---:|
| Aurea | 247 413 778 | 274 514 000 | +11,0% |
| Vento | 344 103 948 | 422 704 000 | +22,8% |
| Lumi | 110 434 702 | 134 204 000 | +21,5% |
| Kroko | 164 197 984 | 145 272 000 | -11,5% |
| Grupa | 866 150 412 | 976 694 000 | +12,8% |

Cele marek to sumy wierszy arkusza `Cele` w pliku `cele_sprzedazy_2027_28.xlsx` (marka x kraj x kanał). Plik powstał jako prognoza FC 2026/27 powiększona o docelowy wzrost, zaokrąglona do tysięcy PLN.

## Oczekiwany rozkład po miesiącach (mln PLN)

| Marka | Kwi | Maj | Cze | Lip | Sie | Wrz | Paz | Lis | Gru | Sty | Lut | Mar | Razem |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Aurea | 20,87 | 23,26 | 21,38 | 20,82 | 21,61 | 21,96 | 23,81 | 29,83 | 38,01 | 17,76 | 15,23 | 19,98 | 274,51 |
| Vento | 31,57 | 34,66 | 32,58 | 32,00 | 33,14 | 33,95 | 36,90 | 45,74 | 59,35 | 27,69 | 23,87 | 31,26 | 422,70 |
| Lumi | 10,43 | 11,19 | 10,62 | 10,27 | 10,68 | 10,67 | 11,50 | 14,39 | 18,66 | 8,60 | 7,37 | 9,83 | 134,20 |
| Kroko | 11,70 | 12,40 | 11,34 | 11,13 | 11,55 | 11,68 | 12,66 | 15,18 | 20,30 | 9,33 | 7,78 | 10,22 | 145,27 |
| Grupa | 74,57 | 81,52 | 75,91 | 74,21 | 76,98 | 78,25 | 84,87 | 105,14 | 136,31 | 63,38 | 54,25 | 71,30 | 976,69 |

## Punkt do dyskusji: cel z góry czy z dołu

Vento w Niemczech miało w 2025/26 udział 24,2% w sprzedaży marki. Po wpisaniu celu marki Plan przydzieli Niemcom około 102,15 mln PLN, a cel z pliku Excel, budowany oddolnie po krajach, wynosi 114 756 000 PLN. Różnica pokazuje, że alokacja według historycznej struktury nie uwzględnia nowych sklepów ani opóźnionych otwarć. Do tego służy wpisanie celu na poziomie kraju albo zablokowanie wybranych komórek przed rozkładem.

Tabela `ref_plan_2027_28_rozklad` w lakehouse zawiera rozkład miesięczny w wariancie, w którym cele wpisuje się na poziomie marka x kraj x kanał (kolumna `plan_ly_pln`), oraz wariant z udziałami średnimi z dwóch lat (`plan_sr2_pln`). Suma `plan_ly_pln` dla każdego wiersza celu zgadza się z plikiem Excel, co skrypt sprawdza przy każdym uruchomieniu.
