"""Test agentów danych przez endpoint MCP opublikowanego agenta.

Zadaje pytania z dane/oczekiwane_odpowiedzi.csv agentom z .stan_wdrozenia.json.
Pełny przebieg (wszystkie pytania, wszyscy agenci) nadpisuje dokumentacja/wyniki_testu_agentow.md,
razem z ręczną oceną dopisaną w tym pliku. Przebieg zawężony przez --pytania albo --agent
wypisuje odpowiedzi tylko na ekran i pliku nie zmienia.
Kolumna "trafienie" to tylko heurystyka. Szuka wartości kluczowej w tekście odpowiedzi
w kilku zapisach i sprawdza znak oraz skalę zapisaną tuż za liczbą (tys., mln, mld).
Gdy znaku albo skali nie da się ustalić, zwraca "ręcznie". Ostateczną ocenę trzeba zrobić ręcznie.

Endpoint opublikowanego agenta:
  https://api.fabric.microsoft.com/v1/mcp/workspaces/{ws}/dataagents/{id}/agent
  (https://learn.microsoft.com/fabric/data-science/data-agent-mcp-server)

Wymaga: pip install mcp, az login do tenanta z obszarem roboczym, agent opublikowany.

Przykłady:
  python fabric/deploy/testuj_agenta.py --pytania 1,3,13
  python fabric/deploy/testuj_agenta.py --agent Agent_Kontroling --pytanie "What was group net sales in 2Q 2026/27?"
"""
from __future__ import annotations

import argparse
import asyncio
import contextlib
import csv
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import fabric_api as fa

KATALOG = Path(__file__).resolve().parent
REPO = KATALOG.parents[1]
STAN = KATALOG / ".stan_wdrozenia.json"
KLUCZ = REPO / "dane" / "oczekiwane_odpowiedzi.csv"
WYNIK = REPO / "dokumentacja" / "wyniki_testu_agentow.md"
MCP_URL = "https://api.fabric.microsoft.com/v1/mcp/workspaces/{ws}/dataagents/{agent}/agent"


@contextlib.asynccontextmanager
async def polacz(url: str, naglowki: dict[str, str]):
    """Strumień MCP dla obu linii pakietu mcp (1.x jak w Learn i 2.x)."""
    import mcp.client.streamable_http as sh

    if hasattr(sh, "streamablehttp_client"):
        async with sh.streamablehttp_client(url, headers=naglowki, timeout=30, sse_read_timeout=600) as (r, w, _):
            yield r, w
    else:
        import httpx2
        limit = httpx2.Timeout(30, read=600)
        async with sh.create_mcp_http_client(headers=naglowki, timeout=limit) as http:
            async with sh.streamable_http_client(url, http_client=http) as (r, w):
                yield r, w


async def zapytaj(ws: str, agent_id: str, pytanie: str) -> tuple[str, str]:
    from mcp import ClientSession

    naglowki = {"Authorization": " ".join(("Bearer", fa.get_token(fa.FABRIC_RESOURCE)))}
    async with polacz(MCP_URL.format(ws=ws, agent=agent_id), naglowki) as (r, w):
        async with ClientSession(r, w) as sesja:
            await sesja.initialize()
            narzedzie = (await sesja.list_tools()).tools[0]
            schemat = getattr(narzedzie, "input_schema", None) or getattr(narzedzie, "inputSchema")
            arg = next(iter(schemat["properties"]))
            wynik = await sesja.call_tool(narzedzie.name, {arg: pytanie}, read_timeout_seconds=600)
            tresc = getattr(wynik, "content", None)
            if tresc is None:
                return narzedzie.name, f"(odpowiedź bez treści: {wynik!r})"[:2000]
            tekst = "\n".join(b.text for b in tresc if getattr(b, "type", "") == "text")
            if getattr(wynik, "is_error", False) or getattr(wynik, "isError", False):
                tekst = "BŁĄD NARZĘDZIA: " + tekst
            return narzedzie.name, tekst


LICZBA = re.compile(r"\d{1,3}(?:[ \u00a0\u202f]\d{3})+(?:[.,]\d+)?|\d[\d.,]*\d|\d")
MINUSY = "-\u2011\u2013\u2212"
PRZED_SKALA = re.compile(r"[ \u00a0\u202f*]{0,4}")
SKALE = (
    (1e3, re.compile(r"[Tt]ys|[Tt]housand|[kK](?![^\W\d_])")),
    (1e6, re.compile(r"[Mm]ln|[Mm]ilion|[Mm]illion|mn(?![^\W\d_])|M(?![^\W\d_])")),
    (1e9, re.compile(r"[Mm]ld|[Mm]iliard|[Bb]illion|bn(?![^\W\d_])")),
)
RANGA = {"nie": 0, "ręcznie": 1, "tak": 2}


def odczytaj(token: str) -> list[tuple[float, int]]:
    """Możliwe odczyty liczby z tekstu jako (wartość, liczba miejsc po przecinku).

    Zapis "1,052" jest niejednoznaczny (tysiące albo ułamek), więc zwraca oba odczyty.
    """
    t = re.sub(r"[\s\u00a0\u202f]", "", token)
    wyniki: list[tuple[float, int]] = []

    def dodaj(s: str) -> None:
        with contextlib.suppress(ValueError):
            wyniki.append((float(s), len(s.split(".")[1]) if "." in s else 0))

    if "," in t and "." in t:
        dziesietny = "," if t.rfind(",") > t.rfind(".") else "."
        tysiace = "." if dziesietny == "," else ","
        dodaj(t.replace(tysiace, "").replace(dziesietny, "."))
    elif "," in t or "." in t:
        sep = "," if "," in t else "."
        czesci = t.split(sep)
        if len(czesci) > 2:
            dodaj(t.replace(sep, ""))
        else:
            dodaj(t.replace(sep, "."))
            if len(czesci[1]) == 3:
                dodaj(t.replace(sep, ""))
    else:
        dodaj(t)
    return wyniki


def znak_przed(tekst: str, poczatek: int) -> int:
    """Znak liczby: 1 dla plusa, -1 dla minusa, 0 gdy nie da się go ustalić.

    Minus tuż po cyfrze to łącznik przedziału albo daty (31-33%, 2026-09).
    Spacji nie pomija, bo myślnik listy w markdown ("- 25,4%") nie jest minusem.
    """
    i = poczatek - 1
    while i >= 0 and tekst[i] == "*":
        i -= 1
    if i < 0:
        return 0
    if tekst[i] == "+":
        return 1
    if tekst[i] not in MINUSY:
        return 0
    i -= 1
    while i >= 0 and tekst[i] == "*":
        i -= 1
    return 0 if i >= 0 and tekst[i].isdigit() else -1


def skala_po(tekst: str, koniec: int) -> float:
    poz = PRZED_SKALA.match(tekst, koniec).end()
    for skala, wzor in SKALE:
        if wzor.match(tekst, poz):
            return skala
    return 1.0


def liczby(tekst: str):
    """Liczby z tekstu jako (możliwe odczyty, znak, skala zapisana za liczbą)."""
    for m in LICZBA.finditer(tekst):
        yield odczytaj(m.group()), znak_przed(tekst, m.start()), skala_po(tekst, m.end())


def zgodnosc_znaku(znak: int, cel: float) -> str:
    if cel < 0:
        return {-1: "tak", 0: "ręcznie", 1: "nie"}[znak]
    return "nie" if znak == -1 else "tak"


def najlepsza(oceny) -> str:
    wynik = "nie"
    for o in oceny:
        if RANGA[o] > RANGA[wynik]:
            wynik = o
            if wynik == "tak":
                break
    return wynik


def ocena_kwoty(odpowiedz: str, cel: float) -> str:
    """Kwota w PLN w dowolnym zapisie (pełna, tys., mln, mld) z tolerancją zaokrąglenia.

    Klucz jest zaokrąglony do 1 000 PLN, stąd dodatkowe 1 000 PLN tolerancji.
    Odczyt zbyt mało precyzyjny (tolerancja ponad 0,5% celu) się nie liczy.
    Liczba bez jednostki, która pasuje dopiero w innej skali (np. w tabeli
    z jednostką w nagłówku), daje najwyżej "ręcznie".
    """
    def oceny():
        for odczyty, znak, skala in liczby(odpowiedz):
            skale = (1.0, 1e3, 1e6, 1e9) if skala == 1 else (skala,)
            for v, d in odczyty:
                for s in skale:
                    tol = 0.5 * 10 ** (-d) * s
                    if tol <= 0.005 * abs(cel) and abs(v * s - abs(cel)) <= tol + 1000:
                        z = zgodnosc_znaku(znak, cel)
                        yield z if s == skala or z == "nie" else "ręcznie"
    return najlepsza(oceny())


def ocena_procentu(odpowiedz: str, cel: float) -> str:
    def oceny():
        for odczyty, znak, skala in liczby(odpowiedz):
            if skala != 1:
                continue
            for v, d in odczyty:
                if d >= 1 and abs(v - abs(cel)) <= 0.5 * 10 ** (-d) + 0.05:
                    yield zgodnosc_znaku(znak, cel)
    return najlepsza(oceny())


def trafienie(odpowiedz: str, wartosc: str, jednostka: str) -> str:
    if odpowiedz.startswith(("WYJĄTEK", "BŁĄD")):
        return "nie"
    if "brak" in wartosc:
        wzorce = r"brak danych|nie mam danych|nie ma danych|nie zawiera|no data|not available|does not contain|nie obejmuje"
        return "tak" if re.search(wzorce, odpowiedz, re.I) else "nie"
    if ":" in wartosc or "/" in wartosc or not (jednostka.startswith("PLN") or jednostka == "%"):
        return "ręcznie"
    oceny = []
    for kawalek in wartosc.split(";"):
        k = kawalek.strip().rstrip("%").replace(",", ".")
        for minus in MINUSY:
            k = k.replace(minus, "-")
        try:
            cel = float(k)
        except ValueError:
            return "ręcznie"
        oceny.append(ocena_procentu(odpowiedz, cel) if jednostka == "%" else ocena_kwoty(odpowiedz, cel))
    if "nie" in oceny:
        return "nie"
    return "ręcznie" if "ręcznie" in oceny else "tak"


def opis_wyjatku(e: BaseException) -> str:
    """Opis wyjątku; grupy wyjątków (np. z TaskGroup klienta MCP) rozwija do składowych."""
    skladowe = getattr(e, "exceptions", None)
    if isinstance(skladowe, (list, tuple)) and skladowe:
        return "; ".join(opis_wyjatku(s) for s in skladowe)
    return f"{type(e).__name__}: {e}"


def komorka(tekst: str) -> str:
    return tekst.replace("|", "\\|").replace("\r", "").replace("\n", "<br>")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--agent", action="append", help="nazwa agenta (domyślnie wszyscy z pliku stanu)")
    p.add_argument("--pytania", default="wszystkie", help="numery z klucza, np. 1,3,13")
    p.add_argument("--pytanie", help="własne pytanie zamiast klucza (wynik tylko na ekran)")
    a = p.parse_args()
    if a.pytanie is not None and not a.pytanie.strip():
        p.error("--pytanie nie może być puste")

    stan = json.loads(STAN.read_text(encoding="utf-8"))
    ws, agenci = stan["workspaceId"], stan["agenci"]
    nazwy = a.agent or list(agenci)

    if a.pytanie is not None:
        for n in nazwy:
            t0 = time.time()
            _, odp = asyncio.run(zapytaj(ws, agenci[n], a.pytanie))
            print(f"== {n} ({time.time() - t0:.0f} s)\n{odp}\n")
        return 0

    klucz = list(csv.DictReader(KLUCZ.open(encoding="utf-8-sig")))
    pelny = a.pytania == "wszystkie" and not a.agent
    if a.pytania != "wszystkie":
        wybrane = {s.strip() for s in a.pytania.split(",")}
        klucz = [k for k in klucz if k["nr"] in wybrane]

    wiersze = []
    for k in klucz:
        for n in nazwy:
            t0 = time.time()
            try:
                narzedzie, odp = asyncio.run(zapytaj(ws, agenci[n], k["pytanie"]))
            except Exception as e:
                narzedzie, odp = "", f"WYJĄTEK: {opis_wyjatku(e)}"[:1500]
            czas = time.time() - t0
            traf = trafienie(odp, k["wartosc_kluczowa"], k["jednostka"])
            print(f"[{k['nr']}] {n}: {traf}, {czas:.0f} s", flush=True)
            if not pelny:
                print(f"{odp}\n", flush=True)
            wiersze.append((k, n, odp, traf, czas))

    if not pelny:
        print(f"Przebieg zawężony: wyniki tylko na ekranie, {WYNIK.relative_to(REPO)} bez zmian.")
        return 0

    teraz = datetime.now().strftime("%Y-%m-%d %H:%M")
    linie = [
        "# Wyniki testu agentów danych",
        "",
        f"Uruchomienie {teraz}, skrypt `fabric/deploy/testuj_agenta.py`, endpoint MCP opublikowanego agenta.",
        "Kolumna trafienie to heurystyka szukająca wartości kluczowej w tekście odpowiedzi, ze sprawdzeniem znaku i skali; "
        "ręcznie oznacza, że któregoś z nich nie dało się ustalić. "
        "Nie zastępuje oceny człowieka: agent może podać poprawną liczbę w innym zapisie albo trafić liczbę przy złym uzasadnieniu.",
        "",
        "| nr | agent | trafienie | czas [s] | wartość kluczowa | odpowiedź agenta |",
        "|---|---|---|---:|---|---|",
    ]
    for k, n, odp, traf, czas in wiersze:
        wartosc, jedn = k["wartosc_kluczowa"], k["jednostka"]
        if not wartosc.endswith(jedn):
            wartosc = f"{wartosc} {jedn}"
        linie.append(f"| {k['nr']} | {n} | {traf} | {czas:.0f} | {komorka(wartosc)} | {komorka(odp)} |")
    podsum = {}
    for _, n, _, traf, _ in wiersze:
        podsum.setdefault(n, []).append(traf)
    linie += ["", "## Podsumowanie heurystyki", ""]
    for n, t in podsum.items():
        linie.append(f"{n}: {t.count('tak')} z {len(t)} (ręcznie do oceny {t.count('ręcznie')}).")
    WYNIK.write_text("\n".join(linie) + "\n", encoding="utf-8")
    print(f"Zapisano {WYNIK.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
