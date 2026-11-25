# Oczekiwane odpowiedzi agenta

Dane są w pełni syntetyczne i wymyślone. Nie przedstawiają wyników żadnej firmy; skala jest umowna. Poniższe liczby są wynikiem obliczeń pandas na wygenerowanych tabelach, a nie cytatem ze źródeł biznesowych ani podsumowaniem AI.

Data stanu: 2026-12-09. Zamknięte miesiące ACT kończą się w listopadzie 2026. Kwoty zbiorcze zaokrąglono do tysięcy PLN, procenty do 0,1 pp. Koszt jednego zamówienia podano do groszy, aby zachować sens porównania. Zaokrąglone składniki mogą nie sumować się do zaokrąglonego wyniku.

## 1. Jaka była sprzedaż netto grupy w 2Q 2026/27 i jak wypadła względem budżetu?

2Q: ACT 213 603 000 PLN, BUD 220 492 000 PLN, odchylenie -6 889 000 PLN (-3,1%).

Sposób liczenia: fakt_pnl, konto 4010, scenariusze ACT i BUD, miesiące lipiec, sierpień i wrzesień 2026. Odchylenie = ACT minus BUD; procent = ACT / BUD minus 1.

Dobra odpowiedź agenta wskazuje finansowy, a nie kalendarzowy kwartał, obie kwoty i oba odchylenia.

## 2. Która marka ma największe procentowe odchylenie sprzedaży od budżetu narastająco w RF 2026/27 (kwiecień do listopada)? Podaj odchylenia wszystkich marek w PLN i %.

Największe odchylenie bezwzględne %: Kroko, -8 352 000 PLN, -7,7%. Największy spadek względem BUD: Kroko.

| Marka | ACT | BUD | ACT minus BUD | Odchylenie |
| --- | --- | --- | --- | --- |
| Aurea | 173 451 000 PLN | 174 483 000 PLN | -1 031 000 PLN | -0,6% |
| Kroko | 99 909 000 PLN | 108 261 000 PLN | -8 352 000 PLN | -7,7% |
| Lumi | 82 829 000 PLN | 79 017 000 PLN | +3 812 000 PLN | +4,8% |
| Vento | 248 667 000 PLN | 264 969 000 PLN | -16 301 000 PLN | -6,2% |

Sposób liczenia: fakt_pnl po połączeniu z dim_mpk, konto 4010, ACT i BUD, kwiecień do listopada 2026, grupowanie według marki. Ranking według bezwzględnej wartości procentu.

Dobra odpowiedź agenta pokazuje wszystkie cztery marki, znak odchylenia oraz rozróżnia największą zmianę bezwzględną od największego spadku.

## 3. Dlaczego Vento w Niemczech jest poniżej budżetu w 1H 2026/27? (Oczekiwane: odchylenie sprzedaży i lista 4 sklepów z datą planowaną i rzeczywistą otwarcia.)

Vento DE 1H: ACT 43 720 000 PLN, BUD 51 061 000 PLN, różnica -7 341 000 PLN (-14,4%); 4 opóźnione otwarcia.

Budżet zawierał sprzedaż od terminów planowanych, podczas gdy wykonanie pojawia się dopiero po rzeczywistym otwarciu. Nowe sklepy dochodzą od 70% do 100% docelowego poziomu przez sześć miesięcy. Nie należy przypisywać całego odchylenia wyłącznie opóźnieniom, ponieważ założenia wzrostu ACT i BUD także się różnią.

| MPK | Nazwa | Planowane otwarcie | Rzeczywiste otwarcie |
| --- | --- | --- | --- |
| SK-VEN-DE-009 | Vento Hamburg 9 | 2026-05-01 | 2026-08-01 |
| SK-VEN-DE-010 | Vento Kolonia 10 | 2026-05-15 | 2026-08-15 |
| SK-VEN-DE-011 | Vento Frankfurt nad Menem 11 | 2026-06-01 | 2026-09-01 |
| SK-VEN-DE-012 | Vento Lipsk 12 | 2026-06-15 | 2026-09-15 |

Sposób liczenia: fakt_pnl, konto 4010, ACT i BUD, VEN, DE, oba kanały, kwiecień do września 2026. Lista otwarć pochodzi z dim_mpk; daty planowane i rzeczywiste nie są zamienne.

Dobra odpowiedź agenta podaje kwotę i procent odchylenia, wszystkie cztery MPK i obie daty oraz wskazuje wpływ rozruchu.

## 4. Które 5 sklepów ma największe przekroczenie kosztów czynszu względem budżetu w RF 2026/27 (kwiecień do listopada)?

| MPK | Nazwa | ACT | BUD | Przekroczenie | Odchylenie |
| --- | --- | --- | --- | --- | --- |
| SK-AUR-AT-002 | Aurea Graz 2 | 928 000 PLN | 832 000 PLN | +97 000 PLN | +11,7% |
| SK-AUR-AT-003 | Aurea Linz 3 | 631 000 PLN | 565 000 PLN | +66 000 PLN | +11,7% |
| SK-AUR-AT-004 | Aurea Salzburg 4 | 594 000 PLN | 532 000 PLN | +62 000 PLN | +11,7% |
| SK-AUR-AT-001 | Aurea Wiedeń 1 | 576 000 PLN | 516 000 PLN | +60 000 PLN | +11,7% |
| SK-AUR-AT-005 | Aurea Wiedeń 5 | 538 000 PLN | 482 000 PLN | +56 000 PLN | +11,7% |

Ranking jest według przekroczenia w PLN, nie według samego procentu. Sklepy Aurea w Austrii mają od kwietnia podwyżkę stawki o 15%, podczas gdy BUD zakładał 3%.

Sposób liczenia: fakt_pnl i dim_mpk, konto 5120, Sklep, kwiecień do listopada 2026. Suma ACT minus suma BUD dla każdego MPK; sortowanie malejąco według dodatniej różnicy.

Dobra odpowiedź agenta podaje pięć identyfikatorów, kwoty ACT i BUD, różnicę w PLN i wyjaśnia zmianę stawki.

## 5. Jak zmieniła się sprzedaż odzieży wierzchniej w listopadzie 2026 r/r, w podziale na marki?

| Marka | Listopad 2025 | Listopad 2026 | Zmiana PLN | Zmiana r/r |
| --- | --- | --- | --- | --- |
| Aurea | 5 915 000 PLN | 4 178 000 PLN | -1 738 000 PLN | -29,4% |
| Vento | 9 011 000 PLN | 6 584 000 PLN | -2 427 000 PLN | -26,9% |
| Razem | 14 926 000 PLN | 10 761 000 PLN | -4 165 000 PLN | -27,9% |

To zaszyty efekt ciepłego listopada: niższa sprzedaż i mniejszy udział kategorii OW.

Sposób liczenia: fakt_sprzedaz_kategorie_mies, kategoria OW, listopad 2025 i listopad 2026, oba kanały i wszystkie kraje. Procent to suma 2026 / suma 2025 minus 1, nie średnia procentów krajów.

Dobra odpowiedź agenta podaje wszystkie marki, wynik łączny i rozróżnia zmianę sprzedaży kategorii od zmiany całej marki.

## 6. Jak zmieniał się udział e-commerce w sprzedaży grupy w kolejnych latach finansowych?

| RF | Zakres ACT | E-commerce | Grupa | Udział |
| --- | --- | --- | --- | --- |
| 2023/24 | pełne 12 miesięcy | 131 421 000 PLN | 730 118 000 PLN | 18,0% |
| 2024/25 | pełne 12 miesięcy | 152 890 000 PLN | 805 594 000 PLN | 19,0% |
| 2025/26 | pełne 12 miesięcy | 178 670 000 PLN | 866 150 000 PLN | 20,6% |
| 2026/27 | kwiecień do listopada 2026, 8 miesięcy | 139 646 000 PLN | 604 856 000 PLN | 23,1% |

Sposób liczenia: agg_sprzedaz_mies, wyłącznie ACT, suma sprzedaży kanału E-commerce / sprzedaż grupy w danym RF. Ostatni RF kończy się na listopadzie, bez dziennego grudnia.

Dobra odpowiedź agenta wskazuje niepełny RF 2026/27 i nie miesza ACT z FC lub BUD.

## 7. Ile wyniosła sprzedaż grupy w Black Friday 2025 i ile to razy więcej niż średnia z pozostałych piątków listopada 2025?

Black Friday: 7 388 000 PLN, średnia pozostałych piątków 3 510 000 PLN, 2,10 razy.

Piątki porównawcze to 7, 14 i 21 listopada 2025.

Sposób liczenia: fakt_sprzedaz_dzienna, suma grupy na 28.11.2025; mianownik to średnia trzech innych piątków listopada po wcześniejszym zsumowaniu całej grupy dla każdego dnia.

Dobra odpowiedź agenta podaje dzień, sprzedaż, mianownik i mnożnik, bez porównywania do średniej pojedynczego MPK.

## 8. Jaki był koszt logistyki e-commerce na jedno zamówienie w Niemczech w październiku i listopadzie 2026 w porównaniu z budżetem? (Koszt na zamówienie ACT = konto 5220 ACT / liczba zamówień z faktu dziennego; budżetowy = konto 5220 BUD / liczba zamówień ACT.)

| Miesiąc | Zamówienia ACT | Koszt ACT | Koszt BUD | ACT na zamówienie | BUD na zamówienie ACT | Odchylenie kosztu |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-10 | 20 683 | 640 000 PLN | 510 000 PLN | 30,95 PLN | 24,68 PLN | +25,4% |
| 2026-11 | 26 500 | 820 000 PLN | 676 000 PLN | 30,95 PLN | 25,51 PLN | +21,3% |

Od października działa podwyżka stawek przewoźnika w Niemczech o 18%. Budżetowa kwota na zamówienie w tym pytaniu jest ilorazem budżetu i liczby zamówień ACT, nie umowną stawką z budżetu.

Sposób liczenia: fakt_pnl, konto 5220, EC-*-DE, osobno październik i listopad 2026, ACT i BUD. Oba scenariusze dzielone przez tę samą liczbę zamówień ACT z fakt_sprzedaz_dzienna.

Dobra odpowiedź agenta stosuje wymagany wspólny mianownik i oddziela wpływ stawki przewoźnika od liczby zamówień.

## 9. Jaka jest prognoza EBITDA grupy na RF 2026/27 (FC 8+4) i jak wypada względem budżetu?

EBITDA RF 2026/27: FC 149 380 000 PLN (16,4% sprzedaży), BUD 161 951 000 PLN, różnica -12 570 000 PLN (-7,8%).

FC zawiera osiem miesięcy ACT i cztery miesiące prognozy. Amortyzacja nie pomniejsza EBITDA.

Sposób liczenia: fakt_pnl, wszystkie MPK, RF 2026/27, osobno FC i BUD. EBITDA = 4010 minus 4510 minus wszystkie konta kosztów operacyjnych, bez konta 6010; znaki z dim_konto.

Dobra odpowiedź agenta nie odejmuje amortyzacji, nie sumuje FC z ACT i podaje obie wartości oraz odchylenie.

## 10. Które 5 sklepów Kroko ma najniższą marżę brutto % w RF 2026/27 (kwiecień do listopada)?

| MPK | Nazwa | Sprzedaż ACT | Marża brutto PLN | Marża brutto % |
| --- | --- | --- | --- | --- |
| SK-KRO-PL-016 | Kroko Kielce 16 | 1 174 000 PLN | 611 000 PLN | 52,0% |
| SK-KRO-DE-003 | Kroko Hamburg 3 | 2 887 000 PLN | 1 511 000 PLN | 52,3% |
| SK-KRO-PL-010 | Kroko Kraków 10 | 2 018 000 PLN | 1 059 000 PLN | 52,5% |
| SK-KRO-PL-002 | Kroko Kraków 2 | 1 201 000 PLN | 630 000 PLN | 52,5% |
| SK-KRO-SE-001 | Kroko Sztokholm 1 | 1 931 000 PLN | 1 018 000 PLN | 52,7% |

Sposób liczenia: fakt_pnl i dim_mpk, KRO, Sklep, ACT, kwiecień do listopada 2026. Dla każdego MPK: (suma 4010 minus suma 4510) / suma 4010. Sklepy zamknięte w okresie pozostają w rankingu za miesiące, w których prowadziły sprzedaż.

Dobra odpowiedź agenta nie zastępuje marży narzutem i nie uśrednia dziennych procentów bez ważenia sprzedażą.

## 11. Jaka była dynamika sprzedaży LFL Kroko w 2Q 2026/27? (Sklepy LFL to sklepy z `lfl_od` <= 2026-07-01 i bez zamknięcia przed 2026-10-01; porównanie lipca do września 2026 z lipcem do września 2025.)

LFL Kroko 2Q: 38 sklepów, 30 471 000 PLN do 28 319 000 PLN, -7,1%.

Sposób liczenia: dim_mpk: marka KRO, typ Sklep, lfl_od nie później niż 01.07.2026, brak zamknięcia przed 01.10.2026. Ten sam zbiór MPK w obu latach; konto 4010 ACT z fakt_pnl, lipiec do września 2025 i lipiec do września 2026.

Dobra odpowiedź agenta podaje liczebność wspólnej kohorty, obie podstawy i procent, bez e-commerce oraz zamkniętych sklepów.

## 12. Ile wyniosły koszty IT i licencji (konto 5420) w RF 2025/26 w porównaniu z RF 2024/25?

IT i licencje: RF 2024/25 10 835 000 PLN, RF 2025/26 11 485 000 PLN, różnica +650 000 PLN (+6,0%).

Odnowienia licencji przypadają na kwiecień i październik. Wartości nie opisują cen konkretnych produktów.

Sposób liczenia: fakt_pnl, konto 5420, ACT, wszystkie MPK. RF 2024/25 to kwiecień 2024 do marca 2025; RF 2025/26 to kwiecień 2025 do marca 2026.

Dobra odpowiedź agenta porównuje pełne lata finansowe i nie interpretuje syntetycznego kosztu jako cennika licencji.

## 13. Jaka będzie sprzedaż w 2029 roku? (Oczekiwane: brak danych, agent nie powinien zgadywać.)

Brak danych o sprzedaży w 2029 roku. Nie da się podać wiarygodnej kwoty z tego zestawu. FC kończy się w marcu 2027, a cel i rozkład planu obejmują RF 2027/28. Nie ma zatwierdzonego celu, prognozy ani wykonania dla 2029.

Sposób liczenia: Sprawdzenie zakresów fakt_pnl, ref_plan_2027_28_rozklad i dim_data, bez ekstrapolacji.

Dobra odpowiedź agenta odmawia zgadywania liczby, wskazuje brak danych oraz prosi o cel lub założenia do osobnej symulacji.

## 14. Jaka jest sprzedaż w bieżącym kwartale? (Oczekiwane: 3Q 2026/27, czyli październik do grudnia 2026; P&L ACT tylko za październik i listopad, grudzień tylko z danych dziennych do 08.12.2026; podać oba składniki osobno.)

3Q 2026/27 na 2026-12-09: P&L ACT październik i listopad 175 616 000 PLN, dzienny grudzień do 08.12 30 659 000 PLN, razem niepełny kwartał 206 274 000 PLN.

Nie ma zamkniętego grudnia w P&L ACT. Nie należy podawać powyższej sumy jako wyniku pełnego kwartału ani uzupełniać reszty miesiąca prognozą bez oznaczenia.

Sposób liczenia: Bieżący kwartał ustalony według daty stanu 09.12.2026, nie zegara komputera. Konto 4010 ACT z fakt_pnl za październik i listopad oraz fakt_sprzedaz_dzienna za 01.12.2026 do 08.12.2026, bez ponownego doliczania dni października i listopada.

Dobra odpowiedź agenta podaje 3Q 2026/27, osobno oba składniki, graniczną datę danych i zastrzeżenie niepełności.

## Luki i granice odpowiedzi

Brak danych klienta i rzeczywistych przyczyn biznesowych. Wyjaśnienia dotyczą wyłącznie scenariuszy zaszytych w generatorze. Nie ma danych o VAT, zwrotach, zapasach, cash flow ani sprzedaży po dacie granicznej. Każda nowa prognoza wymaga odrębnych założeń, zamiast dopisywania faktów.
