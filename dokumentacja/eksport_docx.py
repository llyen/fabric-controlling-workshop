"""Eksport scenariusza warsztatu do docx.

Plik źródłowy to dokumentacja/Scenariusz_warsztatu.md, wynik to
dokumentacja/docx/Scenariusz_warsztatu.docx. Komentarze HTML są pomijane.

Spis treści powstaje jako lista odnośników do nagłówków, bez numerów stron.
Pole spisu treści z pandoca wymagałoby aktualizacji w Wordzie przy każdym
otwarciu, a zapis przez Worda mógłby dopisać do pliku etykietę i autora.

Użycie (z katalogu głównego repozytorium):
    python dokumentacja\\eksport_docx.py
    python dokumentacja\\eksport_docx.py --sprawdz-w-wordzie

Wymaga pandoca w PATH, w %LOCALAPPDATA%\\Pandoc, w %ProgramFiles%\\Pandoc albo w zmiennej PANDOC.
Opcja --sprawdz-w-wordzie otwiera gotowe pliki w Wordzie tylko do odczytu
(Windows, pakiet pywin32) i podaje liczbę stron i tabel.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

KATALOG = Path(__file__).resolve().parent
ZRODLO = KATALOG / "Scenariusz_warsztatu.md"
WYJSCIE = KATALOG / "docx"

PLIK_DOCX = "Scenariusz_warsztatu.docx"

# Tabele, w których najdłuższe słowa kolumn nie mieszczą się razem w wierszu strony
# (nagłówek -> potrzebna liczba znaków); wypisywane jako ostrzeżenie po eksporcie.
ZA_SZEROKIE_TABELE: dict[str, int] = {}

# Stała data w metadanych, żeby ponowny eksport tej samej treści dawał te same pliki.
DATA_EKSPORTU = datetime(2026, 1, 1, tzinfo=timezone.utc)

SEPARATOR_TABELI = re.compile(r"^\|(\s*:?-{3,}:?\s*\|)+\s*$")
NAGLOWEK = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
LINK_WZGLEDNY = re.compile(r"\[([^\]]+)\]\((?!https?://|mailto:|#)[^)]*\)")
SPACJA_W_LICZBIE = re.compile(r"(?<=\d) (?=\d{3}(?!\d))")
KOD_INLINE = re.compile(r"(`[^`\n]*`)")

# A4 z marginesami 2,5 cm u góry i u dołu oraz 2 cm po bokach, tekst 11 pt.
STRONA_A4 = (
    '<w:pgSz w:w="11906" w:h="16838" />'
    '<w:pgMar w:top="1418" w:right="1134" w:bottom="1418" w:left="1134" w:header="709" w:footer="709" w:gutter="0" />'
)
# Przybliżona liczba znaków w wierszu tekstu 11 pt przy tej szerokości strony.
ZNAKOW_W_WIERSZU = 84


def znajdz_pandoc() -> str:
    kandydaci = [
        os.environ.get("PANDOC"),
        shutil.which("pandoc"),
        os.path.expandvars(r"%LOCALAPPDATA%\Pandoc\pandoc.exe"),
        os.path.expandvars(r"%ProgramFiles%\Pandoc\pandoc.exe"),
    ]
    for k in kandydaci:
        if k and Path(k).is_file():
            return k
    sys.exit("Nie znaleziono pandoca. Ustaw zmienną PANDOC albo dodaj pandoc do PATH.")


def podziel_na_bloki(tekst: str) -> list[list[str]]:
    """Dzieli Markdown na bloki rozdzielone pustą linią, nie rozcinając bloków kodu."""
    bloki: list[list[str]] = []
    biezacy: list[str] = []
    w_kodzie = False
    for linia in tekst.splitlines():
        if linia.lstrip().startswith(("```", "~~~")):
            w_kodzie = not w_kodzie
        if not w_kodzie and not linia.strip():
            if biezacy:
                bloki.append(biezacy)
                biezacy = []
            continue
        biezacy.append(linia)
    if biezacy:
        bloki.append(biezacy)
    return bloki


def wybierz_bloki(bloki: list[list[str]]) -> list[list[str]]:
    return [b for b in bloki if not all(re.fullmatch(r"\s*<!--.*?-->\s*", linia) for linia in b)]


def popraw_tekst(linia: str) -> str:
    """Usuwa linki względne i wstawia twarde spacje w liczbach, z pominięciem kodu inline."""
    czesci = KOD_INLINE.split(linia)
    for i in range(0, len(czesci), 2):
        czesci[i] = LINK_WZGLEDNY.sub(r"\1", czesci[i])
        czesci[i] = SPACJA_W_LICZBIE.sub("\u00a0", czesci[i])
    return "".join(czesci)


def podziel_wiersz(linia: str) -> list[str]:
    s = linia.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [k.strip() for k in re.split(r"(?<!\\)\|", s)]


def szerokosci_kolumn(wiersze: list[list[str]], liczba: int) -> list[int]:
    """Każda kolumna mieści najdłuższe słowo, a nadwyżkę szerokości dostają kolumny z większą ilością tekstu."""
    minimum, naturalna, slowa = [], [], []
    for k in range(liczba):
        teksty = [re.sub(r"[`<>\[\]]", "", w[k]) for w in wiersze if len(w) == liczba]
        slowo = max((len(s) for t in teksty for s in t.split()), default=3)
        srednia = sum(len(t) for t in teksty) / max(1, len(teksty))
        slowa.append(min(slowo, ZNAKOW_W_WIERSZU * 0.4))
        minimum.append(min(slowo + 3, ZNAKOW_W_WIERSZU * 0.4))
        naturalna.append(max(srednia + 3, minimum[-1]))
    # Zapas 3 znaków w minimum jest ostrożny, więc ostrzeżenie pojawia się dopiero wtedy,
    # gdy same najdłuższe słowa z jednym znakiem odstępu nie mieszczą się w wierszu.
    if sum(slowa) + liczba > ZNAKOW_W_WIERSZU and wiersze:
        ZA_SZEROKIE_TABELE.setdefault(" | ".join(wiersze[0][:3]), round(sum(slowa) + liczba))
    if sum(naturalna) <= ZNAKOW_W_WIERSZU or sum(minimum) >= ZNAKOW_W_WIERSZU:
        szer = naturalna if sum(naturalna) <= ZNAKOW_W_WIERSZU else minimum
    else:
        zapas = ZNAKOW_W_WIERSZU - sum(minimum)
        nadwyzka = [n - m for n, m in zip(naturalna, minimum)]
        szer = [m + zapas * x / sum(nadwyzka) for m, x in zip(minimum, nadwyzka)]
    suma = sum(szer)
    return [max(3, round(100 * s / suma)) for s in szer]


def przelicz_tabele(blok: list[str]) -> list[str]:
    if len(blok) < 2 or not blok[0].startswith("|") or not SEPARATOR_TABELI.match(blok[1]):
        return blok
    separator = podziel_wiersz(blok[1])
    wiersze = [podziel_wiersz(l) for i, l in enumerate(blok) if i != 1]
    szer = szerokosci_kolumn(wiersze, len(separator))
    nowe = []
    for kom, n in zip(separator, szer):
        lewy = ":" if kom.startswith(":") else ""
        prawy = ":" if kom.endswith(":") else ""
        nowe.append(lewy + "-" * max(3, n - len(lewy) - len(prawy)) + prawy)
    return [blok[0], "|" + "|".join(nowe) + "|"] + blok[2:]


def zbuduj_markdown(tekst: str) -> tuple[str, str]:
    bloki = wybierz_bloki(podziel_na_bloki(tekst))
    tytul = ""
    if bloki and bloki[0][0].startswith("# "):
        tytul = bloki[0][0][2:].strip()
        bloki = bloki[1:]

    spis: list[tuple[int, str, str]] = []
    gotowe: list[str] = []
    licznik = 0
    for blok in bloki:
        m = NAGLOWEK.match(blok[0])
        if m:
            licznik += 1
            poziom, napis = len(m.group(1)), m.group(2)
            ident = f"sekcja-{licznik}"
            if 2 <= poziom <= 4:
                spis.append((poziom - 1, napis, ident))
            gotowe.append(f"{m.group(1)} {popraw_tekst(napis)} {{#{ident}}}")
            blok = blok[1:]
            if not blok:
                continue
        blok = przelicz_tabele(blok)
        linie, w_kodzie = [], False
        for linia in blok:
            if linia.lstrip().startswith(("```", "~~~")):
                w_kodzie = not w_kodzie
                linie.append(linia)
            else:
                linie.append(linia if w_kodzie else popraw_tekst(linia))
        gotowe.append("\n".join(linie))

    wpisy = ['::: {custom-style="TOC Heading"}\nSpis treści\n:::']
    for poziom, napis, ident in spis:
        etykieta = napis.replace("[", "\\[").replace("]", "\\]")
        wpisy.append(f'::: {{custom-style="Spis treści {poziom}"}}\n[{etykieta}](#{ident})\n:::')
    wpisy.append('```{=openxml}\n<w:p><w:r><w:br w:type="page"/></w:r></w:p>\n```')
    return tytul, "\n\n".join(wpisy + gotowe) + "\n"


STYL_TABELI = """<w:style w:type="table" w:default="1" w:styleId="Table">
    <w:name w:val="Table" />
    <w:basedOn w:val="TableNormal" />
    <w:semiHidden />
    <w:unhideWhenUsed />
    <w:qFormat />
    <w:tblPr>
      <w:tblInd w:w="0" w:type="dxa" />
      <w:tblBorders>
        <w:top w:val="single" w:sz="4" w:space="0" w:color="A6A6A6" />
        <w:left w:val="single" w:sz="4" w:space="0" w:color="A6A6A6" />
        <w:bottom w:val="single" w:sz="4" w:space="0" w:color="A6A6A6" />
        <w:right w:val="single" w:sz="4" w:space="0" w:color="A6A6A6" />
        <w:insideH w:val="single" w:sz="4" w:space="0" w:color="A6A6A6" />
        <w:insideV w:val="single" w:sz="4" w:space="0" w:color="A6A6A6" />
      </w:tblBorders>
      <w:tblCellMar>
        <w:top w:w="40" w:type="dxa" />
        <w:left w:w="108" w:type="dxa" />
        <w:bottom w:w="40" w:type="dxa" />
        <w:right w:w="108" w:type="dxa" />
      </w:tblCellMar>
    </w:tblPr>
    <w:tblStylePr w:type="firstRow">
      <w:tcPr>
        <w:shd w:val="clear" w:color="auto" w:fill="E7E6E6" />
        <w:vAlign w:val="bottom" />
      </w:tcPr>
    </w:tblStylePr>
  </w:style>"""

STYLE_SPISU = "".join(
    f"""<w:style w:type="paragraph" w:customStyle="1" w:styleId="Spistreci{p}">
    <w:name w:val="Spis treści {p}" />
    <w:basedOn w:val="Normal" />
    <w:qFormat />
    <w:pPr>
      <w:spacing w:before="{120 if p == 1 else 0}" w:after="40" />
      <w:ind w:left="{(p - 1) * 360}" />
    </w:pPr>
  </w:style>"""
    for p in (1, 2, 3)
)


def przygotuj_szablon(pandoc: str, katalog: Path) -> Path:
    """Domyślny szablon pandoca z obramowaniem tabel i stylami spisu treści."""
    domyslny = katalog / "domyslny.docx"
    subprocess.run(
        [pandoc, "-o", str(domyslny), "--print-default-data-file", "reference.docx"],
        check=True, env=srodowisko_pandoca(),
    )
    szablon = katalog / "szablon.docx"
    with zipfile.ZipFile(domyslny) as zr, zipfile.ZipFile(szablon, "w", zipfile.ZIP_DEFLATED) as zw:
        for wpis in zr.infolist():
            dane = zr.read(wpis.filename)
            if wpis.filename == "word/styles.xml":
                xml = dane.decode("utf-8")
                xml, n = re.subn(r'<w:style w:type="table"[^>]*w:styleId="Table".*?</w:style>', STYL_TABELI, xml, count=1, flags=re.S)
                if n != 1:
                    sys.exit("Szablon pandoca nie ma stylu tabeli Table. Sprawdź wersję pandoca.")
                xml = xml.replace("</w:styles>", STYLE_SPISU + "</w:styles>")
                xml, n = re.subn(
                    r"(<w:rPrDefault>.*?)<w:sz w:val=\"24\"\s*/>(\s*)<w:szCs w:val=\"24\"\s*/>",
                    r'\1<w:sz w:val="22" />\2<w:szCs w:val="22" />', xml, count=1, flags=re.S,
                )
                if n != 1:
                    sys.exit("Szablon pandoca ma inny rozmiar domyślnej czcionki niż 12 pt. Sprawdź wersję pandoca.")
                dane = xml.encode("utf-8")
            elif wpis.filename == "word/document.xml":
                xml = dane.decode("utf-8")
                # Kolejność w sectPr wymagana przez schemat: footnotePr przed pgSz i pgMar.
                if "</w:footnotePr>" in xml:
                    xml, n = re.subn(r"</w:footnotePr>", "</w:footnotePr>" + STRONA_A4, xml, count=1)
                else:
                    xml, n = re.subn(r"<w:sectPr>", "<w:sectPr>" + STRONA_A4, xml, count=1)
                if n != 1 or "<w:pgSz" in xml.replace(STRONA_A4, "", 1):
                    sys.exit("Nieoczekiwana sekcja strony w szablonie pandoca. Sprawdź wersję pandoca.")
                dane = xml.encode("utf-8")
            # Pandoc przepisuje część wpisów z szablonu razem z ich datą.
            wpis.date_time = DATA_EKSPORTU.timetuple()[:6]
            zw.writestr(wpis, dane)
    return szablon


def srodowisko_pandoca() -> dict[str, str]:
    return dict(os.environ, SOURCE_DATE_EPOCH=str(int(DATA_EKSPORTU.timestamp())))


def eksportuj(pandoc: str, szablon: Path, tytul: str, markdown: str, cel: Path) -> None:
    polecenie = [
        pandoc, "-f", "markdown-smart", "-t", "docx",
        "--reference-doc", str(szablon),
        "--shift-heading-level-by=-1",
        "-M", f"title={tytul}",
        "-M", "lang=pl-PL",
        "-o", str(cel),
    ]
    subprocess.run(polecenie, input=markdown.encode("utf-8"), check=True, env=srodowisko_pandoca())


def tekst_docx(sciezka: Path) -> tuple[str, str]:
    with zipfile.ZipFile(sciezka) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    tekst = "".join(re.findall(r"<w:t(?: [^>]*)?>([^<]*)</w:t>", xml))
    return xml, tekst


def sprawdz(sciezka: Path, markdown: str) -> list[str]:
    bledy = []
    if sciezka.read_bytes()[:2] != b"PK":
        bledy.append("plik nie jest kontenerem ZIP")
    xml, tekst = tekst_docx(sciezka)
    tabele_md = sum(1 for b in podziel_na_bloki(markdown) if len(b) > 1 and SEPARATOR_TABELI.match(b[1]))
    tabele_docx = xml.count("<w:tbl>")
    if tabele_md != tabele_docx:
        bledy.append(f"tabel w Markdown {tabele_md}, w docx {tabele_docx}")
    kotwice = set(re.findall(r'w:anchor="([^"]+)"', xml))
    zakladki = set(re.findall(r'w:bookmarkStart [^>]*w:name="([^"]+)"', xml))
    if kotwice - zakladki:
        bledy.append(f"odnośniki bez celu: {sorted(kotwice - zakladki)[:5]}")
    if 'w:pStyle w:val="Spistreci1"' not in xml:
        bledy.append("spis treści nie dostał stylu Spis treści 1")
    if not re.search(r'<w:pgSz (?=[^>]*w:w="11906")(?=[^>]*w:h="16838")', xml):
        bledy.append("strona nie ma formatu A4")
    for znak in "\u2013\u2014\u2212":
        if znak in tekst:
            bledy.append(f"w tekście jest znak U+{ord(znak):04X}")
    return bledy


def sprawdz_w_wordzie(pliki: list[Path]) -> None:
    import win32com.client  # pywin32, tylko Windows

    word = win32com.client.DispatchEx("Word.Application")
    word.Visible = False
    word.DisplayAlerts = 0
    try:
        for plik in pliki:
            dok = word.Documents.Open(str(plik), ConfirmConversions=False, ReadOnly=True, AddToRecentFiles=False)
            try:
                strony = dok.ComputeStatistics(2)
                print(f"  Word: {plik.name}: {strony} stron, {dok.Tables.Count} tabel, {dok.Hyperlinks.Count} odnośników")
            finally:
                dok.Close(SaveChanges=0)
    finally:
        word.Quit()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sprawdz-w-wordzie", action="store_true", help="otwórz gotowe pliki w Wordzie tylko do odczytu")
    args = parser.parse_args()

    pandoc = znajdz_pandoc()
    tekst = ZRODLO.read_text(encoding="utf-8")
    WYJSCIE.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        szablon = przygotuj_szablon(pandoc, Path(tmp))
        tytul, markdown = zbuduj_markdown(tekst)
        cel = WYJSCIE / PLIK_DOCX
        eksportuj(pandoc, szablon, tytul, markdown, cel)
        bledy = sprawdz(cel, markdown)
    print(f"{cel.relative_to(KATALOG.parent)}: {'OK' if not bledy else 'BŁĘDY'}")
    for b in bledy:
        print(f"  - {b}")
    for naglowek, potrzeba in ZA_SZEROKIE_TABELE.items():
        print(f"  ostrzeżenie: w tabeli „{naglowek} …” najdłuższe słowa kolumn zajmują około {potrzeba} znaków, "
              f"a wiersz strony mieści około {ZNAKOW_W_WIERSZU}; Word podzieli część słów w komórkach")
    if args.sprawdz_w_wordzie:
        sprawdz_w_wordzie([cel])
    if bledy:
        sys.exit(1)


if __name__ == "__main__":
    main()
