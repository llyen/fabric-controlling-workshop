"""Parametry modelu syntetycznego i jawne parametry historii."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "dane"
SEED = 731905
# Rok finansowy zaczyna się 1 kwietnia; RF 2026/27 to 01.04.2026 do 31.03.2027.
FY_START_MONTH = 4
AS_OF = "2026-12-09"
DAILY_START = "2023-04-01"
DAILY_END = "2026-12-08"
CLOSED_END = "2026-11-30"
CALENDAR_END = "2028-03-31"
FORECAST_START = "2026-12-01"
FORECAST_END = "2027-03-31"
PLAN_START = "2027-04-01"
PLAN_END = "2028-03-01"

BRANDS = [
    ("AUR", "Aurea", "Odzież biznesowa premium", 1),
    ("VEN", "Vento", "Sport i outdoor", 2),
    ("LUM", "Lumi", "Bielizna i odzież domowa", 3),
    ("KRO", "Kroko", "Obuwie i dodatki", 4),
]
GROUP_BRAND = ("GRP", "Centrala (bez marki)", "nie dotyczy", 5)

COUNTRIES = [
    ("PL", "Polska", "PLN", "Polska"),
    ("DE", "Niemcy", "EUR", "Europa Zachodnia"),
    ("AT", "Austria", "EUR", "Europa Zachodnia"),
    ("NL", "Holandia", "EUR", "Europa Zachodnia"),
    ("SE", "Szwecja", "SEK", "Skandynawia"),
    ("DK", "Dania", "DKK", "Skandynawia"),
]
CATEGORIES = [
    ("OW", "Odzież wierzchnia", "Odzież"),
    ("SW", "Swetry i bluzy", "Odzież"),
    ("SP", "Spodnie", "Odzież"),
    ("SU", "Sukienki i spódnice", "Odzież"),
    ("TS", "T-shirty i koszule", "Odzież"),
    ("OB", "Obuwie", "Obuwie"),
    ("AK", "Akcesoria", "Akcesoria"),
    ("BI", "Bielizna i odzież domowa", "Odzież"),
    ("SR", "Odzież sportowa", "Odzież"),
]
SCENARIOS = [
    ("ACT", "Wykonanie", "Dane rzeczywiste z zamkniętych miesięcy", 1),
    ("BUD", "Budżet", "Budżet zatwierdzony przed rozpoczęciem roku finansowego", 2),
    (
        "FC",
        "Prognoza 8+4",
        "Dla RF 2026/27: wykonanie kwiecień do listopada 2026 oraz prognoza "
        "grudzień 2026 do marca 2027",
        3,
    ),
]
ACCOUNTS = [
    ("4010", "Przychody ze sprzedaży netto", "Przychody", "Przychody", 1, 10),
    ("4510", "Koszt własny sprzedaży", "Koszt własny", "Koszt własny", -1, 20),
    ("5110", "Wynagrodzenia personelu sklepów", "Koszty operacyjne", "Koszty sklepów", -1, 40),
    ("5120", "Czynsze", "Koszty operacyjne", "Koszty sklepów", -1, 41),
    ("5130", "Media i utrzymanie", "Koszty operacyjne", "Koszty sklepów", -1, 42),
    ("5210", "Marketing", "Koszty operacyjne", "Marketing", -1, 50),
    ("5220", "Logistyka e-commerce", "Koszty operacyjne", "Koszty e-commerce", -1, 55),
    ("5230", "Prowizje płatnicze", "Koszty operacyjne", "Koszty e-commerce", -1, 56),
    ("5310", "Logistyka magazynowa", "Koszty operacyjne", "Logistyka", -1, 58),
    ("5410", "Wynagrodzenia centrali", "Koszty operacyjne", "Koszty centrali", -1, 60),
    ("5420", "IT i licencje", "Koszty operacyjne", "Koszty centrali", -1, 61),
    ("5910", "Pozostałe koszty operacyjne", "Koszty operacyjne", "Pozostałe", -1, 70),
    ("6010", "Amortyzacja", "Amortyzacja", "Amortyzacja", -1, 90),
]
STORE_COUNTS = {
    "AUR": [12, 6, 5, 3, 2, 1],
    "VEN": [20, 12, 4, 3, 3, 2],
    "LUM": [16, 4, 2, 2, 0, 0],
    "KRO": [24, 6, 3, 2, 2, 1],
}
AREAS = {"AUR": (250, 500), "VEN": (600, 1200), "LUM": (80, 200), "KRO": (150, 350)}
CITIES = {
    "PL": ["Warszawa", "Kraków", "Wrocław", "Poznań", "Łódź", "Lublin", "Katowice", "Kielce"],
    "DE": ["Berlin", "Monachium", "Hamburg", "Kolonia", "Frankfurt nad Menem", "Lipsk"],
    "AT": ["Wiedeń", "Graz", "Linz", "Salzburg"],
    "NL": ["Amsterdam", "Rotterdam", "Utrecht"],
    "SE": ["Sztokholm", "Göteborg", "Malmö"],
    "DK": ["Kopenhaga", "Aarhus"],
}
DEPARTMENTS = [
    ("FIN", "Finanse"),
    ("TEC", "Technologia"),
    ("SCM", "Łańcuch dostaw"),
    ("KAD", "Kadry"),
    ("PRD", "Produkt i projektowanie"),
    ("ADM", "Administracja i prawo"),
]
HQ_IT_MPK = "HQ-TEC"
HQ_LOGISTICS_MPK = "HQ-SCM"
HQ_LOGISTICS_DEPARTMENT = "Łańcuch dostaw"


def store_id(brand, country, number):
    return f"SK-{brand}-{country}-{number:03d}"


def ecom_id(brand, country):
    return f"EC-{brand}-{country}"


HISTORICAL_OPENINGS = {
    "SK-VEN-PL-016": "2023-06-01", "SK-VEN-PL-017": "2023-09-15",
    "SK-VEN-DE-005": "2023-11-01", "SK-VEN-AT-003": "2024-03-15",
    "SK-VEN-PL-018": "2024-05-01", "SK-VEN-NL-003": "2024-09-01",
    "SK-VEN-SE-003": "2025-04-15", "SK-VEN-PL-019": "2025-08-01",
    "SK-LUM-PL-015": "2023-10-01", "SK-LUM-DE-004": "2024-06-15",
    "SK-LUM-NL-002": "2025-05-01",
    "SK-AUR-AT-005": "2024-02-01", "SK-AUR-PL-012": "2025-03-01",
}
DELAYED_OPENINGS = {
    "SK-VEN-DE-009": ("2026-05-01", "2026-08-01"),
    "SK-VEN-DE-010": ("2026-05-15", "2026-08-15"),
    "SK-VEN-DE-011": ("2026-06-01", "2026-09-01"),
    "SK-VEN-DE-012": ("2026-06-15", "2026-09-15"),
}
DELAYED_BRAND, DELAYED_COUNTRY = "VEN", "DE"
DELAYED_STORE_AREA = (650, 900)
CLOSURES = {
    "SK-KRO-PL-025": "2025-05-31", "SK-KRO-PL-026": "2025-10-31",
    "SK-KRO-DE-007": "2026-01-31", "SK-KRO-PL-027": "2026-06-30",
    "SK-LUM-NL-003": "2025-08-31",
}
PLANNED_OPENINGS = {
    "SK-VEN-PL-021": "2027-05-01", "SK-VEN-DE-013": "2027-06-01",
    "SK-VEN-AT-005": "2027-09-01", "SK-VEN-DK-003": "2027-11-01",
    "SK-LUM-PL-017": "2027-04-01", "SK-LUM-AT-003": "2027-10-01",
    "SK-AUR-DE-007": "2027-08-01",
}

SALES_SCALE = 1.0
STORE_PRODUCTIVITY_RANGE = (.88, 1.12)
STORE_MARGIN_OFFSET_SIGMA = .007
STORE_MARGIN_OFFSET_LIMIT = .014
ECOM_MARGIN_OFFSET_SIGMA = .004
ECOM_MARGIN_OFFSET_LIMIT = .008
STORE_FORMATS = ["Centrum handlowe", "Park handlowy", "Ulica handlowa"]
STORE_FORMAT_WEIGHTS = [.46, .24, .30]
DENSITY = {"AUR": 15000, "VEN": 7000, "LUM": 19000, "KRO": 12500}
COUNTRY_FACTOR = {"PL": 1.00, "DE": 1.25, "AT": 1.20, "NL": 1.20, "SE": 1.30, "DK": 1.30}
MONTH_SEASONALITY = [.78, .74, .88, .96, 1.02, .98, .92, .94, 1.00, 1.04, 1.22, 1.48]
WEEKDAY_FACTOR = [.86, .86, .90, .96, 1.12, 1.32, 1.00]
PL_TRADING_SUNDAY_FACTOR = 1.30
ECOM_SUNDAY_FACTOR = 1.15
CHRISTMAS_FORTNIGHT_FACTOR = 1.30
CHRISTMAS_EVE_STORE_FACTOR = .50
BLACK_FRIDAY_STORE_FACTOR = 2.
BLACK_FRIDAY_ECOM_FACTOR = 3.
BLACK_FRIDAY_PRE_WEEK_FACTOR = 1.20
BLACK_FRIDAY_POST_WEEKEND_FACTOR = 1.40
CYBER_MONDAY_ECOM_FACTOR = 2.
STORE_LFL_GROWTH = .03
# Marka w trendzie spadkowym sklepów; FC obniża jej sprzedaż od grudnia 2026.
DECLINING_BRAND = "KRO"
DECLINING_STORE_GROWTH = {2024: .02, 2025: -.02, 2026: -.07}
FC_DECLINING_FACTOR = .91
ECOM_GROWTH = .14
FAST_ECOM_BRAND = "LUM"
FAST_ECOM_GROWTH = .28
ECOM_SHARE_2023 = .18
ECOM_BRAND_WEIGHTS = {"AUR": .30, "VEN": .35, "LUM": .20, "KRO": .15}
ECOM_COUNTRY_WEIGHTS = {"PL": .45, "DE": .25, "AT": .08, "NL": .10, "SE": .07, "DK": .05}
DAILY_SIGMA_STORE = .08
DAILY_SIGMA_ECOM = .12
BASKET = {"AUR": 320., "VEN": 210., "LUM": 95., "KRO": 240.}
ITEMS_PER_BASKET = 1.7
MULTI_ITEM_BRAND = "LUM"
MULTI_ITEM_PER_BASKET = 2.8
ECOM_BASKET_FACTOR = 1.25
GROSS_MARGIN = {"AUR": .60, "VEN": .50, "LUM": .62, "KRO": .54}
MARGIN_MONTH_ADJUSTMENT = [-.05, -.02, .01, .02, .01, -.01, -.05, -.02, .01, .02, -.01, 0]
ECOM_MARGIN_ADJUSTMENT = -.01
BLACK_FRIDAY_MARGIN_ADJUSTMENT = -.08
RAMP_START = .70
RAMP_MONTHS = 6
# Ciepły listopad 2026: niższa sprzedaż marek z odzieżą wierzchnią i obuwiem zimowym.
WEATHER_MONTH = "2026-11-01"
WARM_MONTH_FACTOR = {"AUR": .95, "VEN": .92, "LUM": .99, "KRO": .95}
WARM_MONTH_MARGIN_PP = -.01
OUTERWEAR_WEATHER_FACTOR = .70
CATEGORY_BASE_WEIGHTS = {
    "AUR": [.16, .14, .20, .12, .22, .06, .08, .02, 0],
    "VEN": [.18, .12, .10, 0, .10, .16, .06, 0, .28],
    "LUM": [0, .08, .04, .06, .08, 0, .06, .68, 0],
    "KRO": [0, 0, 0, 0, 0, .84, .16, 0, 0],
}
OUTERWEAR_WINTER_SHARE = .22
OUTERWEAR_SUMMER_SHARE = .04
OUTERWEAR_SEPTEMBER_SHARE = .14
OUTERWEAR_OTHER_SHARE = .12
OUTERWEAR_BRAND_FACTOR = {"AUR": 1.0, "VEN": 1.10, "LUM": 0., "KRO": 0.}
SWEATERS_WINTER_FACTOR = 1.60
SUMMER_DRESSES_TSHIRTS_FACTOR = 1.50
DECEMBER_ACCESSORIES_UNDERWEAR_FACTOR = 1.50
# Renegocjacja czynszów jednej marki w jednym kraju od początku RF 2026/27.
RENT_SHOCK_BRAND, RENT_SHOCK_COUNTRY = "AUR", "AT"
RENT_SHOCK_INCREASE = .15
RENT_SHOCK_START = "2026-04-01"
# Podwyżka stawki przewoźnika e-commerce w jednym kraju.
ORDER_SHOCK_COUNTRY = "DE"
ORDER_SHOCK_INCREASE = .18
ORDER_SHOCK_START = "2026-10-01"
RENT_INDEX_ACT = {2023: 1., 2024: 1.04, 2025: 1.035, 2026: 1.03}
STORE_PAYROLL_FIXED_SHARE = .080
STORE_PAYROLL_VARIABLE_SHARE = .025
STORE_RENT_SHARE = .125
STORE_UTILITIES_SHARE = .026
STORE_OTHER_SHARE = .015
STORE_OTHER_FIXED_PER_M2 = .60
STORE_DEPRECIATION_PER_M2 = 9.0
WAGE_COUNTRY_INDEX = {"PL": 1., "DE": 1.15, "AT": 1.10, "NL": 1.12, "SE": 1.20, "DK": 1.25}
WAGE_GROWTH = .07
UTILITY_GROWTH = .03
UTILITY_WINTER_FACTOR = 1.20
UTILITY_SUMMER_FACTOR = 1.10
ORDER_COST_PL_2023 = 16.
ORDER_COST_OTHER_2023 = 24.
ORDER_COST_GROWTH = .03
ECOM_PAYMENT_SHARE = .014
ECOM_MARKETING_SHARE = .045
HQ_LOGISTICS_STORE_SHARE = .028
HQ_PAYROLL_SHARE = .042
HQ_IT_SHARE = .014
HQ_MARKETING_SHARE = .016
HQ_OTHER_SHARE = .008
HQ_DEPRECIATION_SHARE = .005
HQ_COST_SCALE = 1.0
HQ_PAYROLL_WEIGHTS = {"HQ-FIN": .14, "HQ-TEC": .18, "HQ-SCM": .10, "HQ-KAD": .08,
                      "HQ-PRD": .26, "HQ-ADM": .10}
HQ_MARKETING_PAYROLL_WEIGHT = .035
HQ_ANNUAL_BONUS = .30
HQ_BONUS_MONTH = 6
HQ_IT_RENEWALS = {4: .70, 10: .55}
HQ_IT_GROWTH = .06
HQ_IT_DEPARTMENT_SHARE = .90
HQ_MARKETING_GROWTH = .06
HQ_OTHER_GROWTH = .03
HQ_MARKETING_SEASONALITY = [.70, .80, 1.30, 1.10, .90, .80, .75, .90, 1.30, 1., 1.60, 1.85]
BUD_STORE_GROWTH = {"AUR": .03, "VEN": .06, "LUM": .04, "KRO": .02}
BUD_ECOM_GROWTH = .13
BUD_RENT_GROWTH = .03
TARGET_GROWTH_2027 = {"AUR": .05, "VEN": .10, "LUM": .08, "KRO": -.03}
TARGET_ECOM_EXTRA_PP = .05
IMPORT_WAGE_INDEX = .06
IMPORT_OTHER_INDEX = .03
IMPORT_IT_RENEWAL_MPK = HQ_IT_MPK
IMPORT_IT_RENEWAL_PLN = 180_000.
IMPORT_IT_RENEWAL_MONTH = "m07_2027_10"
IMPORT_IT_RENEWAL_COMMENT = "Jednorazowe odnowienie licencji w październiku 2027."
FX_BASE = {"EUR": 4.30, "SEK": .392, "DKK": .577}
FX_MONTHLY_VOLATILITY = .007
FX_MEAN_REVERSION = .88
