"""Klucz odpowiedzi liczony wyłącznie z wygenerowanych tabel."""

import numpy as np
import pandas as pd

import config as cfg
from kalendarz import fiscal_year

QUESTIONS = [
    "Jaka była sprzedaż netto grupy w 2Q 2026/27 i jak wypadła względem budżetu?",
    "Która marka ma największe procentowe odchylenie sprzedaży od budżetu narastająco w RF 2026/27 (kwiecień do listopada)? Podaj odchylenia wszystkich marek w PLN i %.",
    "Dlaczego Vento w Niemczech jest poniżej budżetu w 1H 2026/27? (Oczekiwane: odchylenie sprzedaży i lista 4 sklepów z datą planowaną i rzeczywistą otwarcia.)",
    "Które 5 sklepów ma największe przekroczenie kosztów czynszu względem budżetu w RF 2026/27 (kwiecień do listopada)?",
    "Jak zmieniła się sprzedaż odzieży wierzchniej w listopadzie 2026 r/r, w podziale na marki?",
    "Jak zmieniał się udział e-commerce w sprzedaży grupy w kolejnych latach finansowych?",
    "Ile wyniosła sprzedaż grupy w Black Friday 2025 i ile to razy więcej niż średnia z pozostałych piątków listopada 2025?",
    "Jaki był koszt logistyki e-commerce na jedno zamówienie w Niemczech w październiku i listopadzie 2026 w porównaniu z budżetem? (Koszt na zamówienie ACT = konto 5220 ACT / liczba zamówień z faktu dziennego; budżetowy = konto 5220 BUD / liczba zamówień ACT.)",
    "Jaka jest prognoza EBITDA grupy na RF 2026/27 (FC 8+4) i jak wypada względem budżetu?",
    "Które 5 sklepów Kroko ma najniższą marżę brutto % w RF 2026/27 (kwiecień do listopada)?",
    "Jaka była dynamika sprzedaży LFL Kroko w 2Q 2026/27? (Sklepy LFL to sklepy z `lfl_od` <= 2026-07-01 i bez zamknięcia przed 2026-10-01; porównanie lipca do września 2026 z lipcem do września 2025.)",
    "Ile wyniosły koszty IT i licencji (konto 5420) w RF 2025/26 w porównaniu z RF 2024/25?",
    "Jaka będzie sprzedaż w 2029 roku? (Oczekiwane: brak danych, agent nie powinien zgadywać.)",
    "Jaka jest sprzedaż w bieżącym kwartale? (Oczekiwane: 3Q 2026/27, czyli październik do grudnia 2026; P&L ACT tylko za październik i listopad, grudzień tylko z danych dziennych do 08.12.2026; podać oba składniki osobno.)",
]


def number(value, decimals=0, plus=False):
    text = f"{abs(value):,.{decimals}f}".replace(",", " ").replace(".", ",")
    sign = "-" if value < 0 else "+" if plus and value > 0 else ""
    return sign + text


def pln(value, plus=False):
    return number(round(float(value) / 1000.) * 1000., plus=plus) + " PLN"


def pct(value, plus=False):
    return number(float(value) * 100., 1, plus=plus) + "%"


def md_table(headers, rows):
    return "\n".join(
        ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
        + ["| " + " | ".join(str(value) for value in row) + " |" for row in rows]
    )


def make_answers(tables):
    mpk = tables["dim_mpk"]
    pnl = tables["fakt_pnl"].merge(mpk, on="mpk_id", validate="many_to_one")
    daily = tables["fakt_sprzedaz_dzienna"]
    category = tables["fakt_sprzedaz_kategorie_mies"]
    aggregate = tables["agg_sprzedaz_mies"]
    brand_names = tables["dim_marka"].set_index("marka_kod")["marka_nazwa"]
    sections, csv_rows, summary, metrics = [], [], {}, {}

    def add(nr, result, calculation, agent, key, unit, short):
        sections.append(f"## {nr}. {QUESTIONS[nr - 1]}\n\n{result}\n\n"
                        f"Sposób liczenia: {calculation}\n\n"
                        f"Dobra odpowiedź agenta {agent}\n")
        csv_rows.append({
            "nr": nr, "pytanie": QUESTIONS[nr - 1], "wartosc_kluczowa": str(key),
            "jednostka": unit, "opis": short + " Sposób liczenia: " + calculation
            + " Dobra odpowiedź agenta " + agent,
        })
        summary[nr] = short

    def sales(start, end, **filters):
        selected = pnl.loc[pnl["miesiac"].between(start, end) & pnl["konto_id"].eq("4010")]
        for column, value in filters.items():
            selected = selected.loc[selected[column].eq(value)]
        return selected.groupby("scenariusz_kod")["kwota_pln"].sum()

    q1 = sales("2026-07-01", "2026-09-01")
    delta, ratio = q1["ACT"] - q1["BUD"], q1["ACT"] / q1["BUD"] - 1.
    short = f"2Q: ACT {pln(q1.ACT)}, BUD {pln(q1.BUD)}, odchylenie {pln(delta, True)} ({pct(ratio, True)})."
    add(1, short, "fakt_pnl, konto 4010, scenariusze ACT i BUD, miesiące lipiec, sierpień i wrzesień 2026. "
        "Odchylenie = ACT minus BUD; procent = ACT / BUD minus 1.",
        "wskazuje finansowy, a nie kalendarzowy kwartał, obie kwoty i oba odchylenia.",
        int(round(q1.ACT, -3)), "PLN", short)
    metrics["q1"] = {"act": q1.ACT, "bud": q1.BUD, "delta": delta, "pct": ratio}

    ytd = pnl.loc[pnl["miesiac"].between("2026-04-01", "2026-11-01") & pnl["konto_id"].eq("4010")
                  & pnl["scenariusz_kod"].isin(["ACT", "BUD"])]
    by_brand = ytd.pivot_table(index="marka_kod", columns="scenariusz_kod", values="kwota_pln", aggfunc="sum")
    by_brand["delta"] = by_brand.ACT - by_brand.BUD
    by_brand["pct"] = by_brand.ACT / by_brand.BUD - 1.
    worst = by_brand["pct"].abs().idxmax()
    most_negative = by_brand["pct"].idxmin()
    rows = [[brand_names[brand], pln(row.ACT), pln(row.BUD), pln(row.delta, True), pct(row.pct, True)]
            for brand, row in by_brand.iterrows()]
    short = f"Największe odchylenie bezwzględne %: {brand_names[worst]}, {pln(by_brand.loc[worst, 'delta'], True)}, {pct(by_brand.loc[worst, 'pct'], True)}."
    detail = short + f" Największy spadek względem BUD: {brand_names[most_negative]}.\n\n" + \
        md_table(["Marka", "ACT", "BUD", "ACT minus BUD", "Odchylenie"], rows)
    add(2, detail, "fakt_pnl po połączeniu z dim_mpk, konto 4010, ACT i BUD, kwiecień do listopada 2026, "
        "grupowanie według marki. Ranking według bezwzględnej wartości procentu.",
        "pokazuje wszystkie cztery marki, znak odchylenia oraz rozróżnia największą zmianę bezwzględną od największego spadku.",
        pct(by_brand.loc[worst, "pct"]), "%", short + " " + "; ".join(
            f"{brand_names[b]} {pln(r.delta, True)} ({pct(r.pct, True)})" for b, r in by_brand.iterrows()))
    metrics["q2"] = by_brand

    q3 = sales("2026-04-01", "2026-09-01", marka_kod=cfg.DELAYED_BRAND, kraj_kod=cfg.DELAYED_COUNTRY)
    ratio3 = q3.ACT / q3.BUD - 1.
    delayed = mpk.loc[mpk["mpk_id"].isin(cfg.DELAYED_OPENINGS)].sort_values("mpk_id")
    dates_table = md_table(["MPK", "Nazwa", "Planowane otwarcie", "Rzeczywiste otwarcie"],
                          [[r.mpk_id, r.mpk_nazwa, r.data_otwarcia_plan.strftime("%Y-%m-%d"),
                            r.data_otwarcia.strftime("%Y-%m-%d")] for r in delayed.itertuples()])
    short = f"Vento DE 1H: ACT {pln(q3.ACT)}, BUD {pln(q3.BUD)}, różnica {pln(q3.ACT - q3.BUD, True)} ({pct(ratio3, True)}); 4 opóźnione otwarcia."
    add(3, short + "\n\nBudżet zawierał sprzedaż od terminów planowanych, podczas gdy wykonanie "
        "pojawia się dopiero po rzeczywistym otwarciu. Nowe sklepy dochodzą od 70% do 100% "
        "docelowego poziomu przez sześć miesięcy. Nie należy przypisywać całego odchylenia wyłącznie "
        "opóźnieniom, ponieważ założenia wzrostu ACT i BUD także się różnią.\n\n" + dates_table,
        "fakt_pnl, konto 4010, ACT i BUD, VEN, DE, oba kanały, kwiecień do września 2026. "
        "Lista otwarć pochodzi z dim_mpk; daty planowane i rzeczywiste nie są zamienne.",
        "podaje kwotę i procent odchylenia, wszystkie cztery MPK i obie daty oraz wskazuje wpływ rozruchu.",
        pct(ratio3), "%", short)
    metrics["q3"] = {"act": q3.ACT, "bud": q3.BUD, "pct": ratio3}

    rents = pnl.loc[pnl["miesiac"].between("2026-04-01", "2026-11-01") & pnl["konto_id"].eq("5120")
                    & pnl["typ_mpk"].eq("Sklep") & pnl["scenariusz_kod"].isin(["ACT", "BUD"])]
    rents = rents.pivot_table(index="mpk_id", columns="scenariusz_kod", values="kwota_pln", aggfunc="sum")
    rents["delta"], rents["pct"] = rents.ACT - rents.BUD, rents.ACT / rents.BUD - 1.
    top_rents = rents.sort_values(["delta", "mpk_id"], ascending=[False, True]).head(5)
    names = mpk.set_index("mpk_id")["mpk_nazwa"]
    rent_table = md_table(["MPK", "Nazwa", "ACT", "BUD", "Przekroczenie", "Odchylenie"],
                          [[key, names[key], pln(row.ACT), pln(row.BUD), pln(row.delta, True), pct(row.pct, True)]
                           for key, row in top_rents.iterrows()])
    short = "Czynsze, pięć największych przekroczeń: " + "; ".join(
        f"{key} {pln(row.delta, True)} ({pct(row.pct, True)})" for key, row in top_rents.iterrows()) + "."
    add(4, rent_table + "\n\nRanking jest według przekroczenia w PLN, nie według samego procentu. "
        "Sklepy Aurea w Austrii mają od kwietnia podwyżkę stawki o 15%, podczas gdy BUD zakładał 3%.",
        "fakt_pnl i dim_mpk, konto 5120, Sklep, kwiecień do listopada 2026. Suma ACT minus suma BUD "
        "dla każdego MPK; sortowanie malejąco według dodatniej różnicy.",
        "podaje pięć identyfikatorów, kwoty ACT i BUD, różnicę w PLN i wyjaśnia zmianę stawki.",
        int(round(top_rents.iloc[0].delta, -3)), "PLN", short)
    metrics["q4"] = top_rents

    outer = category.loc[category["kategoria_kod"].eq("OW") &
                         category["miesiac"].isin(pd.to_datetime(["2025-11-01", "2026-11-01"]))].copy()
    outer["year"] = outer["miesiac"].dt.year
    ow = outer.pivot_table(index="marka_kod", columns="year", values="sprzedaz_netto_pln", aggfunc="sum")
    ow["delta"], ow["pct"] = ow[2026] - ow[2025], ow[2026] / ow[2025] - 1.
    overall_ow = ow[2026].sum() / ow[2025].sum() - 1.
    ow_rows = [[brand_names[key], pln(row[2025]), pln(row[2026]), pln(row["delta"], True), pct(row["pct"], True)]
               for key, row in ow.iterrows()]
    ow_rows.append(["Razem", pln(ow[2025].sum()), pln(ow[2026].sum()),
                    pln(ow["delta"].sum(), True), pct(overall_ow, True)])
    short = f"Odzież wierzchnia: {pln(ow[2025].sum())} do {pln(ow[2026].sum())}, {pct(overall_ow, True)}; " + \
        "; ".join(f"{brand_names[b]} {pct(row['pct'], True)}" for b, row in ow.iterrows()) + "."
    add(5, md_table(["Marka", "Listopad 2025", "Listopad 2026", "Zmiana PLN", "Zmiana r/r"], ow_rows)
        + "\n\nTo zaszyty efekt ciepłego listopada: niższa sprzedaż i mniejszy udział kategorii OW.",
        "fakt_sprzedaz_kategorie_mies, kategoria OW, listopad 2025 i listopad 2026, oba kanały i wszystkie kraje. "
        "Procent to suma 2026 / suma 2025 minus 1, nie średnia procentów krajów.",
        "podaje wszystkie marki, wynik łączny i rozróżnia zmianę sprzedaży kategorii od zmiany całej marki.",
        pct(overall_ow), "%", short)
    metrics["q5"] = {"brands": ow, "pct": overall_ow}

    actual_agg = aggregate.loc[aggregate["scenariusz_kod"].eq("ACT")].copy()
    actual_agg["fy"] = fiscal_year(actual_agg["miesiac"])
    channel_years = actual_agg.groupby(["fy", "kanal"])["sprzedaz_netto_pln"].sum().unstack()
    channel_years["share"] = channel_years["E-commerce"] / channel_years[["E-commerce", "Sklep"]].sum(axis=1)
    rows = []
    for year, row in channel_years.iterrows():
        period = "kwiecień do listopada 2026, 8 miesięcy" if year == 2026 else "pełne 12 miesięcy"
        rows.append([f"{year}/{(year + 1) % 100:02d}", period,
                     pln(row["E-commerce"]), pln(row["E-commerce"] + row["Sklep"]), pct(row["share"])])
    short = "Udział e-commerce: " + "; ".join(
        f"{year}/{(year + 1) % 100:02d} {pct(row['share'])}" + (" (8 miesięcy)" if year == 2026 else "")
        for year, row in channel_years.iterrows()) + "."
    add(6, md_table(["RF", "Zakres ACT", "E-commerce", "Grupa", "Udział"], rows),
        "agg_sprzedaz_mies, wyłącznie ACT, suma sprzedaży kanału E-commerce / sprzedaż grupy w danym RF. "
        "Ostatni RF kończy się na listopadzie, bez dziennego grudnia.",
        "wskazuje niepełny RF 2026/27 i nie miesza ACT z FC lub BUD.",
        pct(channel_years.loc[2026, "share"]), "%", short)
    metrics["q6"] = channel_years

    group_day = daily.groupby("data")["sprzedaz_netto_pln"].sum()
    fridays = group_day.loc[(group_day.index.year == 2025) & (group_day.index.month == 11)
                            & (group_day.index.dayofweek == 4)]
    bf, friday_mean = group_day.loc["2025-11-28"], fridays.drop(pd.Timestamp("2025-11-28")).mean()
    multiple = bf / friday_mean
    short = f"Black Friday: {pln(bf)}, średnia pozostałych piątków {pln(friday_mean)}, {number(multiple, 2)} razy."
    add(7, short + "\n\nPiątki porównawcze to 7, 14 i 21 listopada 2025.",
        "fakt_sprzedaz_dzienna, suma grupy na 28.11.2025; mianownik to średnia trzech innych "
        "piątków listopada po wcześniejszym zsumowaniu całej grupy dla każdego dnia.",
        "podaje dzień, sprzedaż, mianownik i mnożnik, bez porównywania do średniej pojedynczego MPK.",
        int(round(bf, -3)), "PLN", short)
    metrics["q7"] = {"sales": bf, "mean": friday_mean, "multiple": multiple}

    logistics_rows, logistics_metrics = [], []
    for month in ("2026-10-01", "2026-11-01"):
        dt = pd.Timestamp(month)
        orders = daily.loc[daily["mpk_id"].str.match(r"^EC-.+-DE$")
                           & (daily["data"].dt.to_period("M") == dt.to_period("M")), "liczba_paragonow"].sum()
        costs = pnl.loc[pnl["miesiac"].eq(dt) & pnl["konto_id"].eq("5220")
                        & pnl["mpk_id"].str.match(r"^EC-.+-DE$")].groupby("scenariusz_kod")["kwota_pln"].sum()
        act_rate, bud_rate = costs.ACT / orders, costs.BUD / orders
        logistics_rows.append([dt.strftime("%Y-%m"), number(orders), pln(costs.ACT), pln(costs.BUD),
                               number(act_rate, 2) + " PLN", number(bud_rate, 2) + " PLN",
                               pct(costs.ACT / costs.BUD - 1., True)])
        logistics_metrics.append({"miesiac": month, "orders": int(orders), "act": costs.ACT,
                                  "bud": costs.BUD, "act_rate": act_rate, "bud_rate": bud_rate})
    short = "Koszt na zamówienie DE: " + "; ".join(
        f"{row['miesiac'][:7]} ACT {number(row['act_rate'], 2)} PLN, BUD {number(row['bud_rate'], 2)} PLN"
        for row in logistics_metrics) + "."
    add(8, md_table(["Miesiąc", "Zamówienia ACT", "Koszt ACT", "Koszt BUD",
                     "ACT na zamówienie", "BUD na zamówienie ACT", "Odchylenie kosztu"], logistics_rows)
        + "\n\nOd października działa podwyżka stawek przewoźnika w Niemczech o 18%. Budżetowa kwota na zamówienie "
        "w tym pytaniu jest ilorazem budżetu i liczby zamówień ACT, nie umowną stawką z budżetu.",
        "fakt_pnl, konto 5220, EC-*-DE, osobno październik i listopad 2026, ACT i BUD. "
        "Oba scenariusze dzielone przez tę samą liczbę zamówień ACT z fakt_sprzedaz_dzienna.",
        "stosuje wymagany wspólny mianownik i oddziela wpływ stawki przewoźnika od liczby zamówień.",
        "; ".join(f"{r['miesiac'][:7]}: {r['act_rate']:.2f}/{r['bud_rate']:.2f}" for r in logistics_metrics),
        "PLN/zamówienie, ACT/BUD", short)
    metrics["q8"] = logistics_metrics

    full = pnl.loc[(fiscal_year(pnl["miesiac"]) == 2026) &
                   pnl["scenariusz_kod"].isin(["FC", "BUD"]) & ~pnl["konto_id"].eq("6010")].copy()
    signs = tables["dim_konto"].set_index("konto_id")["znak"]
    full["signed"] = full["kwota_pln"] * full["konto_id"].map(signs)
    eb = full.groupby("scenariusz_kod")["signed"].sum()
    net = full.loc[full["konto_id"].eq("4010")].groupby("scenariusz_kod")["kwota_pln"].sum()
    short = f"EBITDA RF 2026/27: FC {pln(eb.FC)} ({pct(eb.FC / net.FC)} sprzedaży), BUD {pln(eb.BUD)}, różnica {pln(eb.FC - eb.BUD, True)} ({pct(eb.FC / eb.BUD - 1., True)})."
    add(9, short + "\n\nFC zawiera osiem miesięcy ACT i cztery miesiące prognozy. Amortyzacja nie pomniejsza EBITDA.",
        "fakt_pnl, wszystkie MPK, RF 2026/27, osobno FC i BUD. "
        "EBITDA = 4010 minus 4510 minus wszystkie konta kosztów operacyjnych, bez konta 6010; znaki z dim_konto.",
        "nie odejmuje amortyzacji, nie sumuje FC z ACT i podaje obie wartości oraz odchylenie.",
        int(round(eb.FC, -3)), "PLN", short)
    metrics["q9"] = {"fc": eb.FC, "bud": eb.BUD, "delta": eb.FC - eb.BUD, "margin": eb.FC / net.FC}

    lum = pnl.loc[pnl["marka_kod"].eq(cfg.DECLINING_BRAND) & pnl["typ_mpk"].eq("Sklep")
                  & pnl["miesiac"].between("2026-04-01", "2026-11-01")
                  & pnl["scenariusz_kod"].eq("ACT") & pnl["konto_id"].isin(["4010", "4510"])]
    gross = lum.pivot_table(index="mpk_id", columns="konto_id", values="kwota_pln", aggfunc="sum")
    gross["margin"] = (gross["4010"] - gross["4510"]) / gross["4010"]
    worst_gross = gross.sort_values(["margin", "mpk_id"]).head(5)
    short = "Najniższa marża Kroko: " + "; ".join(
        f"{key} {pct(row['margin'])}" for key, row in worst_gross.iterrows()) + "."
    add(10, md_table(["MPK", "Nazwa", "Sprzedaż ACT", "Marża brutto PLN", "Marża brutto %"],
                     [[key, names[key], pln(row["4010"]), pln(row["4010"] - row["4510"]), pct(row["margin"])]
                      for key, row in worst_gross.iterrows()]),
        "fakt_pnl i dim_mpk, KRO, Sklep, ACT, kwiecień do listopada 2026. "
        "Dla każdego MPK: (suma 4010 minus suma 4510) / suma 4010. Sklepy zamknięte w okresie "
        "pozostają w rankingu za miesiące, w których prowadziły sprzedaż.",
        "nie zastępuje marży narzutem i nie uśrednia dziennych procentów bez ważenia sprzedażą.",
        pct(worst_gross.iloc[0]["margin"]), "%", short)
    metrics["q10"] = worst_gross

    eligible = mpk.loc[mpk["marka_kod"].eq(cfg.DECLINING_BRAND) & mpk["typ_mpk"].eq("Sklep")
                       & (mpk["lfl_od"] <= pd.Timestamp("2026-07-01"))
                       & (mpk["data_zamkniecia"].isna()
                          | (mpk["data_zamkniecia"] >= pd.Timestamp("2026-10-01"))), "mpk_id"]
    lfl = pnl.loc[pnl["mpk_id"].isin(eligible) & pnl["konto_id"].eq("4010")
                  & pnl["scenariusz_kod"].eq("ACT") & pnl["miesiac"].dt.month.between(7, 9)]
    lfl_values = lfl.groupby(lfl["miesiac"].dt.year)["kwota_pln"].sum()
    lfl_growth = lfl_values[2026] / lfl_values[2025] - 1.
    short = f"LFL Kroko 2Q: {len(eligible)} sklepów, {pln(lfl_values[2025])} do {pln(lfl_values[2026])}, {pct(lfl_growth, True)}."
    add(11, short, "dim_mpk: marka KRO, typ Sklep, lfl_od nie później niż 01.07.2026, "
        "brak zamknięcia przed 01.10.2026. Ten sam zbiór MPK w obu latach; "
        "konto 4010 ACT z fakt_pnl, lipiec do września 2025 i lipiec do września 2026.",
        "podaje liczebność wspólnej kohorty, obie podstawy i procent, bez e-commerce oraz zamkniętych sklepów.",
        pct(lfl_growth), "%", short)
    metrics["q11"] = {"count": len(eligible), "ly": lfl_values[2025], "act": lfl_values[2026], "pct": lfl_growth}

    it = pnl.loc[pnl["konto_id"].eq("5420") & pnl["scenariusz_kod"].eq("ACT")].copy()
    it["fy"] = fiscal_year(it["miesiac"])
    it_totals = it.groupby("fy")["kwota_pln"].sum()
    short = f"IT i licencje: RF 2024/25 {pln(it_totals[2024])}, RF 2025/26 {pln(it_totals[2025])}, różnica {pln(it_totals[2025] - it_totals[2024], True)} ({pct(it_totals[2025] / it_totals[2024] - 1., True)})."
    add(12, short + "\n\nOdnowienia licencji przypadają na kwiecień i październik. Wartości nie opisują cen konkretnych produktów.",
        "fakt_pnl, konto 5420, ACT, wszystkie MPK. RF 2024/25 to kwiecień 2024 do marca 2025; "
        "RF 2025/26 to kwiecień 2025 do marca 2026.",
        "porównuje pełne lata finansowe i nie interpretuje syntetycznego kosztu jako cennika licencji.",
        int(round(it_totals[2025], -3)), "PLN", short)
    metrics["q12"] = {"ly": it_totals[2024], "act": it_totals[2025],
                       "delta": it_totals[2025] - it_totals[2024]}

    add(13, "Brak danych o sprzedaży w 2029 roku. Nie da się podać wiarygodnej kwoty z tego zestawu. "
        "FC kończy się w marcu 2027, a cel i rozkład planu obejmują RF 2027/28. "
        "Nie ma zatwierdzonego celu, prognozy ani wykonania dla 2029.",
        "Sprawdzenie zakresów fakt_pnl, ref_plan_2027_28_rozklad i dim_data, bez ekstrapolacji.",
        "odmawia zgadywania liczby, wskazuje brak danych oraz prosi o cel lub założenia do osobnej symulacji.",
        "brak danych", "nie dotyczy", "Brak danych dla 2029; bez ekstrapolacji i wymyślonej prognozy.")

    closed_quarter = sales("2026-10-01", "2026-11-01").ACT
    december = daily.loc[daily["data"].between(cfg.FORECAST_START, cfg.DAILY_END), "sprzedaz_netto_pln"].sum()
    short = f"3Q 2026/27 na {cfg.AS_OF}: P&L ACT październik i listopad {pln(closed_quarter)}, dzienny grudzień do 08.12 {pln(december)}, razem niepełny kwartał {pln(closed_quarter + december)}."
    add(14, short + "\n\nNie ma zamkniętego grudnia w P&L ACT. "
        "Nie należy podawać powyższej sumy jako wyniku pełnego kwartału ani uzupełniać reszty miesiąca prognozą bez oznaczenia.",
        "Bieżący kwartał ustalony według daty stanu 09.12.2026, nie zegara komputera. "
        "Konto 4010 ACT z fakt_pnl za październik i listopad oraz fakt_sprzedaz_dzienna "
        "za 01.12.2026 do 08.12.2026, bez ponownego doliczania dni października i listopada.",
        "podaje 3Q 2026/27, osobno oba składniki, graniczną datę danych i zastrzeżenie niepełności.",
        f"{int(round(closed_quarter, -3))}; {int(round(december, -3))}", "PLN, zamknięte; częściowy grudzień", short)
    metrics["q14"] = {"closed": closed_quarter, "december": december}

    heading = (
        "# Oczekiwane odpowiedzi agenta\n\n"
        "Dane są w pełni syntetyczne i wymyślone. Nie przedstawiają wyników żadnej firmy; "
        "skala jest umowna. Poniższe liczby są wynikiem obliczeń pandas na wygenerowanych "
        "tabelach, a nie cytatem ze źródeł biznesowych ani podsumowaniem AI.\n\n"
        f"Data stanu: {cfg.AS_OF}. Zamknięte miesiące ACT kończą się w listopadzie 2026. "
        "Kwoty zbiorcze zaokrąglono do tysięcy PLN, procenty do 0,1 pp. "
        "Koszt jednego zamówienia podano do groszy, aby zachować sens porównania. "
        "Zaokrąglone składniki mogą nie sumować się do zaokrąglonego wyniku.\n\n"
    )
    ending = (
        "\n## Luki i granice odpowiedzi\n\n"
        "Brak danych klienta i rzeczywistych przyczyn biznesowych. Wyjaśnienia dotyczą "
        "wyłącznie scenariuszy zaszytych w generatorze. Nie ma danych o VAT, zwrotach, "
        "zapasach, cash flow ani sprzedaży po dacie granicznej. Każda nowa prognoza "
        "wymaga odrębnych założeń, zamiast dopisywania faktów.\n"
    )
    return heading + "\n".join(sections) + ending, pd.DataFrame(csv_rows), summary, metrics


def write_answers(tables):
    markdown, csv, summary, metrics = make_answers(tables)
    (cfg.DATA_DIR / "oczekiwane_odpowiedzi.md").write_text(markdown, encoding="utf-8")
    csv.to_csv(cfg.DATA_DIR / "oczekiwane_odpowiedzi.csv", index=False, encoding="utf-8-sig",
               lineterminator="\n")
    return summary, metrics
