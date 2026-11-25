# Warsztat Microsoft Fabric dla kontrolingu i finansów

[English version](README.md)

Materiały do warsztatu dla zespołu kontrolingu i finansów fikcyjnej sieci odzieżowej Fabrikam Fashion. Warsztat pokazuje Plan w Fabric IQ (Planning), agentów danych Fabric i model semantyczny Direct Lake na lakehouse. W repozytorium są scenariusz, generator danych syntetycznych razem z gotowymi danymi, definicje trzech modeli semantycznych oraz skrypty, które wdrażają środowisko do obszaru roboczego Fabric i sprawdzają, czy liczy poprawnie.

Wszystkie dane są syntetyczne. Fabrikam Fashion i jej cztery marki (Aurea, Vento, Lumi, Kroko) działające w sześciu krajach są fikcyjne, prawdziwe są tylko nazwy krajów i miast. Sklepy, MPK, kwoty i zdarzenia wymyślił generator, więc liczby nie opisują wyników żadnej firmy, a podobieństwo do istniejących marek jest przypadkowe.

## Scenariusz

Główny dokument to [dokumentacja/Scenariusz_warsztatu.md](dokumentacja/Scenariusz_warsztatu.md). Rozdział 4 służy do przeklikania warsztatu z klientem, bo przy każdym kroku podaje ścieżkę kliknięć i liczbę kontrolną. Pozostałe rozdziały omawiają licencje i koszty, warianty pilotażu oraz luki i pytania do zespołu klienta, a w załącznikach są wyniki testów, opis odtworzenia środowiska i źródła w Microsoft Learn.

Polecenie `python dokumentacja\eksport_docx.py` tworzy z niego plik dokumentacja/docx/Scenariusz_warsztatu.docx, który też jest w repozytorium.

## Zawartość

```text
dane/                   14 tabel w CSV i Parquet, 5 plików Excel, słownik danych, klucz 14 pytań testowych
generator/              generator danych i walidacja, opis w generator/README.md i generator/SPEC.md
fabric/semantic_model/  TMDL modeli SM_Kontroling, SM_Kontroling_surowy i SM_Planowanie, instrukcje AI
fabric/data_agent/      instrukcje agenta danych
fabric/plan/            klucz alokacji celu sprzedaży 2027/28, skrypt pliku awaryjnego Planu
fabric/deploy/          wdrożenie do Fabric, kontrole DAX, test agentów przez MCP
dokumentacja/           scenariusz, wyniki testów, eksport do docx
```

## Uruchomienie

Skrypty działały na Pythonie 3.13 w Windows. Generator korzysta z pakietów wymienionych w generator/requirements.txt, wdrożenie potrzebuje jeszcze pakietu requests, test agentów pakietu mcp, a eksport do docx programu pandoc. Skrypty z fabric/deploy pobierają token przez Azure CLI. Przed ich uruchomieniem trzeba wykonać `az login` na koncie, które może tworzyć obszary robocze w docelowej dzierżawie.

Dane, definicje TMDL i klucz alokacji są już w repozytorium, dlatego do samego wdrożenia wystarczą polecenia z drugiego bloku. Pierwszy blok odtwarza te pliki od zera.

```powershell
python generator\generate_data.py
python generator\validate.py --determinism
python fabric\semantic_model\build_tmdl.py
python fabric\plan\klucz_alokacji_2027_28.py
python fabric\plan\excel_awaryjny_planu.py
```

```powershell
$env:FABRIC_WORKSPACE = "Fabrikam Kontroling Warsztat"
$env:FABRIC_CAPACITY_ID = "<identyfikator capacity>"
python fabric\deploy\deploy.py
python fabric\deploy\weryfikuj_model.py
python fabric\deploy\testuj_agenta.py
```

FABRIC_CAPACITY_ID to identyfikator capacity z API Fabric, a nie identyfikator zasobu Azure. Skrypt potrzebuje go tylko wtedy, gdy obszar roboczy trzeba utworzyć albo przepiąć na inną capacity. Wdrożenie ma dziewięć kroków (obszar, lakehouse, pliki, tabele, sql, modele, odswiez, sqldb, agenci), a przełącznik `--kroki` pozwala uruchomić wybrane. Identyfikatory utworzonych elementów skrypt zapisuje w fabric/deploy/.stan_wdrozenia.json. Plik nie trafia do repozytorium, a korzystają z niego weryfikuj_model.py i testuj_agenta.py.

Pełny przebieg testuj_agenta.py nadpisuje dokumentacja/wyniki_testu_agentow.md razem z ręczną oceną odpowiedzi. Pojedyncze pytania lepiej sprawdzać z przełącznikami `--pytania`, `--agent` albo `--pytanie`, bo wtedy wynik trafia tylko na ekran.

## Co zostaje do zrobienia ręcznie

Skrypty nie tworzą planu w Fabric IQ ani raportu Power BI. Plan_Kontroling powstaje według kroku P0 scenariusza, a powody opisuje punkt 3.5. Wcześniej trzeba w ustawieniach SM_Planowanie przypisać model do połączenia chmurowego ze stałą tożsamością (OAuth 2.0, jednostka usługi albo tożsamość obszaru roboczego, bez SSO), bo z domyślnym SSO plan nie łączy się z modelem Direct Lake. Krok modele w deploy.py ostrzega, gdy takiego połączenia brakuje. Ręcznie ustawia się także ustawienia dzierżawy i capacity z punktu 5.1, a verified answers i oznaczenie Approved for Copilot dodaje się tylko wtedy, gdy mają być częścią pokazu. Pełną listę podaje załącznik B scenariusza.

## Wyniki kontroli

Dane wygenerowano ponownie na potrzeby publicznej wersji, więc wyniki z pierwotnego przebiegu w dzierżawie przestały do nich pasować. Pliki dokumentacja/wyniki_weryfikacji_dax.md i dokumentacja/wyniki_testu_agentow.md czekają na ponowny przebieg: po wdrożeniu wypełnią je weryfikuj_model.py i testuj_agenta.py. Wartości oczekiwane są w dane/oczekiwane_odpowiedzi.md.

## Capacity i koszty

Środowisko warsztatowe potrzebuje capacity Fabric (F SKU lub trial). Gdy capacity jest wstrzymana, modele, agenci i plan nie odpowiadają, więc przed pracą trzeba ją wznowić. Każda osoba, która otworzy, utworzy albo zmieni plan, uruchamia 30-dniową sesję liczoną w CU, której nie da się zakończyć wcześniej. Szczegóły i przeliczenie na udział w capacity są w punkcie 5.2 scenariusza.

## Dane wrażliwe

W repozytorium nie ma haseł, kluczy ani identyfikatorów dzierżawy, subskrypcji i capacity. Plik stanu wdrożenia z identyfikatorami utworzonych elementów jest wyłączony w .gitignore. GUID-y w plikach TMDL i w folderze Copilot (lineageTag i pokrewne) nie pochodzą z żadnej dzierżawy. build_tmdl.py wylicza je deterministycznie jako UUID w wersji 5 z nazw obiektów modelu.

## Licencja

MIT, treść w pliku [LICENSE](LICENSE).
