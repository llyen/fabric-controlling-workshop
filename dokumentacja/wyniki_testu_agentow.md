# Wyniki testu agentów danych

Plik generuje `fabric/deploy/testuj_agenta.py`, który zadaje 14 pytań z `dane/oczekiwane_odpowiedzi.csv` opublikowanym agentom przez endpoint MCP.

Do ponownego przebiegu. Dane syntetyczne w tej wersji repozytorium wygenerowano od nowa, więc odpowiedzi agentów z wcześniejszego testu nie odpowiadają już kluczowi i zostały usunięte. Po wdrożeniu uruchom `python fabric\deploy\testuj_agenta.py`, a potem dopisz ręczną ocenę odpowiedzi. Kolumna trafienie w wyniku skryptu jest tylko heurystyką i nie zastępuje oceny człowieka.