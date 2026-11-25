"""Kalendarz finansowy i jawnie uproszczone reguły handlu."""

from datetime import date, timedelta
import calendar

import numpy as np
import pandas as pd

import config as cfg

MONTH_NAMES = ["styczeń", "luty", "marzec", "kwiecień", "maj", "czerwiec",
               "lipiec", "sierpień", "wrzesień", "październik", "listopad", "grudzień"]
MONTH_SHORT = ["sty", "lut", "mar", "kwi", "maj", "cze", "lip", "sie", "wrz", "paź", "lis", "gru"]
MONTH_SHORT_ASCII = ["Sty", "Lut", "Mar", "Kwi", "Maj", "Cze", "Lip", "Sie", "Wrz", "Paz", "Lis", "Gru"]
DAY_NAMES = ["poniedziałek", "wtorek", "środa", "czwartek", "piątek", "sobota", "niedziela"]


def easter(year):
    """Algorytm Meeusa dla kalendarza gregoriańskiego."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month, day = divmod(h + l - 7 * m + 114, 31)
    return date(year, month, day + 1)


def polish_holidays(year):
    holidays = {
        date(year, 1, 1): "Nowy Rok",
        date(year, 1, 6): "Święto Trzech Króli",
        date(year, 5, 1): "Święto Pracy",
        date(year, 5, 3): "Święto Konstytucji 3 Maja",
        date(year, 8, 15): "Wniebowzięcie Najświętszej Maryi Panny",
        date(year, 11, 1): "Wszystkich Świętych",
        date(year, 11, 11): "Narodowe Święto Niepodległości",
        date(year, 12, 25): "Boże Narodzenie, pierwszy dzień",
        date(year, 12, 26): "Boże Narodzenie, drugi dzień",
    }
    if year >= 2025:
        holidays[date(year, 12, 24)] = "Wigilia Bożego Narodzenia"
    sunday = easter(year)
    holidays.update({
        sunday: "Wielkanoc",
        sunday + timedelta(days=1): "Poniedziałek Wielkanocny",
        sunday + timedelta(days=49): "Zielone Świątki",
        sunday + timedelta(days=60): "Boże Ciało",
    })
    return holidays


def last_weekday(year, month, weekday):
    end = date(year, month, calendar.monthrange(year, month)[1])
    return end - timedelta(days=(end.weekday() - weekday) % 7)


def trading_sundays(year):
    sundays = {last_weekday(year, month, 6) for month in (1, 4, 6, 8)}
    sundays.add(easter(year) - timedelta(days=7))
    before = date(year, 12, 25 if year < 2025 else 24)
    christmas = [date(year, 12, day) for day in range(1, before.day)
                 if date(year, 12, day).weekday() == 6]
    sundays.update(christmas[-(2 if year < 2025 else 3):])
    return sundays.difference(polish_holidays(year))


def fiscal_year(dates):
    dates = pd.DatetimeIndex(dates)
    return np.asarray(dates.year - (dates.month < cfg.FY_START_MONTH).astype(int), dtype=np.int64)


def month_start(dates):
    return pd.DatetimeIndex(dates).to_period("M").to_timestamp()


def lfl_start(opening_dates):
    values = pd.DatetimeIndex(opening_dates)
    first = values.to_period("M").to_timestamp() + pd.DateOffset(years=1)
    return pd.DatetimeIndex(
        np.where(values.day == 1, first.values, (first + pd.offsets.MonthBegin(1)).values)
    )


def build_calendar():
    dates = pd.date_range(cfg.DAILY_START, cfg.CALENDAR_END, freq="D")
    holidays, sundays, black_fridays = {}, set(), set()
    for year in range(dates.year.min(), dates.year.max() + 1):
        holidays.update(polish_holidays(year))
        sundays.update(trading_sundays(year))
        black_fridays.add(last_weekday(year, 11, 4))
    fy = fiscal_year(dates)
    fiscal_month = (dates.month.to_numpy() - cfg.FY_START_MONTH) % 12 + 1
    labels = np.array([f"{year}/{(year + 1) % 100:02d}" for year in fy])
    quarter = np.array([f"{value}Q" for value in ((fiscal_month - 1) // 3 + 1)])
    day_values = dates.date
    holiday_names = [holidays.get(day) for day in day_values]
    is_holiday = np.array([day in holidays for day in day_values])
    is_trading_sunday = np.array([day in sundays for day in day_values])
    return pd.DataFrame({
        "data": dates,
        "rok": dates.year.to_numpy(dtype=np.int64),
        "miesiac": dates.month.to_numpy(dtype=np.int64),
        "miesiac_nazwa": np.take(MONTH_NAMES, dates.month - 1),
        "miesiac_skrot": np.take(MONTH_SHORT, dates.month - 1),
        "miesiac_poczatek": month_start(dates),
        "okres_rrrrmm": np.asarray(dates.year * 100 + dates.month, dtype=np.int64),
        "dzien_tygodnia_nr": np.asarray(dates.weekday + 1, dtype=np.int64),
        "dzien_tygodnia_nazwa": np.take(DAY_NAMES, dates.weekday),
        "tydzien_iso": dates.isocalendar().week.to_numpy(dtype=np.int64),
        "rok_finansowy": labels,
        "rok_finansowy_nr": fy,
        "kwartal_finansowy": quarter,
        "kwartal_finansowy_pelny": np.char.add(np.char.add(quarter, " "), labels),
        "kwartal_finansowy_sort": fy * 10 + (fiscal_month - 1) // 3 + 1,
        "polrocze_finansowe": np.where(fiscal_month <= 6, "1H", "2H"),
        "miesiac_finansowy_nr": fiscal_month.astype(np.int64),
        "czy_swieto_pl": is_holiday,
        "nazwa_swieta": holiday_names,
        "czy_niedziela_handlowa_pl": is_trading_sunday,
        "czy_dzien_handlowy_pl": ((dates.weekday < 6) | is_trading_sunday) & ~is_holiday,
        "czy_black_friday": np.array([day in black_fridays for day in day_values]),
        "czy_miesiac_zamkniety": dates <= pd.Timestamp(cfg.CLOSED_END),
    })


def build_plan_calendar(calendar_frame):
    columns = {
        "data": "miesiac",
        "rok_finansowy": "rok_finansowy",
        "rok_finansowy_nr": "rok_finansowy_nr",
        "kwartal_finansowy": "kwartal",
        "kwartal_finansowy_pelny": "kwartal_pelny",
        "kwartal_finansowy_sort": "kwartal_sort",
        "miesiac_finansowy_nr": "miesiac_fin_nr",
        "rok": "rok",
        "miesiac": "miesiac_nr",
        "czy_miesiac_zamkniety": "czy_miesiac_zamkniety",
    }
    months = calendar_frame.loc[calendar_frame["data"].dt.is_month_start, list(columns)].rename(columns=columns).copy()
    months["miesiac_nazwa"] = np.take(MONTH_SHORT_ASCII, months["miesiac_nr"] - 1)
    months["okres"] = months["miesiac"].dt.strftime("%Y-%m")
    return months


def foreign_closed(dates):
    dates = pd.DatetimeIndex(dates)
    easters = pd.DatetimeIndex([easter(year) for year in np.unique(dates.year)])
    return ((dates.month == 12) & (dates.day == 25)) | \
        ((dates.month == 1) & (dates.day == 1)) | dates.isin(easters)
