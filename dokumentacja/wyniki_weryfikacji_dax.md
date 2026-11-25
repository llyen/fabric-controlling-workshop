# Wyniki weryfikacji DAX

Plik generuje `fabric/deploy/weryfikuj_model.py` na wdrożonych modelach. Oczekiwane wartości pochodzą z klucza odpowiedzi generatora (`dane/oczekiwane_odpowiedzi.csv`) i klucza alokacji planu (`fabric/plan/klucz_alokacji_2027_28.json`).

Do ponownego przebiegu. Dane syntetyczne w tej wersji repozytorium wygenerowano od nowa, więc wyniki z wcześniejszego wdrożenia nie pasują już do klucza i zostały usunięte. Po wdrożeniu (`python fabric\deploy\deploy.py`) uruchom `python fabric\deploy\weryfikuj_model.py`, a skrypt nadpisze ten plik tabelą porównania.