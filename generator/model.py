"""Wektorowy model sprzedaży oraz miesięczny rachunek wyników."""

import numpy as np
import pandas as pd

import config as cfg
from kalendarz import fiscal_year, foreign_closed, last_weekday, month_start


def active_fraction(months, openings, closings):
    start = pd.DatetimeIndex(months)
    end = start + pd.offsets.MonthBegin(1)
    opening = pd.DatetimeIndex(openings).fillna(pd.Timestamp("2099-01-01"))
    closing = pd.DatetimeIndex(closings).fillna(pd.Timestamp("2099-01-01")) + pd.Timedelta(days=1)
    lower = np.maximum(start.values, opening.values)
    upper = np.minimum(end.values, closing.values)
    active = np.maximum((upper - lower) / np.timedelta64(1, "D"), 0.)
    return active / ((end.values - start.values) / np.timedelta64(1, "D"))


def utilities_season(months):
    months = np.asarray(months)
    return np.where(np.isin(months, [11, 12, 1, 2]), cfg.UTILITY_WINTER_FACTOR,
                    np.where(np.isin(months, [6, 7, 8]), cfg.UTILITY_SUMMER_FACTOR, 1.))


def ramp_factor(dates, openings):
    dates, openings = pd.DatetimeIndex(dates), pd.DatetimeIndex(openings)
    end = openings + pd.DateOffset(months=cfg.RAMP_MONTHS)
    elapsed = (dates.values - openings.values) / np.timedelta64(1, "D")
    length = (end.values - openings.values) / np.timedelta64(1, "D")
    return np.clip(cfg.RAMP_START + (1. - cfg.RAMP_START) * elapsed / length, cfg.RAMP_START, 1.)


def sales_profile(calendar, mpk, economics, planned=False):
    """Siatka dzień razy MPK powstaje na tablicach, bez pętli po wierszach."""
    cal = calendar.loc[calendar["data"] <= cfg.FORECAST_END].reset_index(drop=True)
    shops = mpk.loc[mpk["typ_mpk"] != "Centrala"].sort_values("mpk_id").reset_index(drop=True)
    dates = pd.DatetimeIndex(cal["data"])
    di = np.repeat(np.arange(len(dates)), len(shops))
    mi = np.tile(np.arange(len(shops)), len(dates))
    ec = shops["typ_mpk"].eq("E-commerce").to_numpy()[mi]
    pl = shops["kraj_kod"].eq("PL").to_numpy()[mi]
    opening_column = "data_otwarcia_plan" if planned else "data_otwarcia"
    openings = pd.DatetimeIndex(shops[opening_column]).fillna(pd.Timestamp("2099-01-01"))
    closings = pd.DatetimeIndex(shops["data_zamkniecia"]).fillna(pd.Timestamp("2099-01-01"))
    trading = np.where(pl, cal["czy_dzien_handlowy_pl"].to_numpy()[di],
                       ~foreign_closed(dates)[di])
    keep = (dates.values[di] >= openings.values[mi]) & \
        (dates.values[di] <= closings.values[mi]) & (ec | trading)
    di, mi, ec, pl = di[keep], mi[keep], ec[keep], pl[keep]
    month = dates.month.to_numpy()[di]
    weekday = dates.weekday.to_numpy()[di]
    weight = np.take(cfg.MONTH_SEASONALITY, month - 1) / np.mean(cfg.MONTH_SEASONALITY)
    dow = np.take(cfg.WEEKDAY_FACTOR, weekday)
    dow = np.where((weekday == 6) & pl & ~ec, cfg.PL_TRADING_SUNDAY_FACTOR, dow)
    dow = np.where((weekday == 6) & ec, cfg.ECOM_SUNDAY_FACTOR, dow)
    weight *= dow
    day = dates.day.to_numpy()[di]
    weight *= np.where((month == 12) & (day >= 10) & (day <= 23), cfg.CHRISTMAS_FORTNIGHT_FACTOR, 1.)
    weight *= np.where((month == 12) & (day == 24) & ~ec, cfg.CHRISTMAS_EVE_STORE_FACTOR, 1.)
    bf_dates = pd.DatetimeIndex([last_weekday(int(year), 11, 4) for year in dates.year])
    bf_delta = np.asarray((dates - bf_dates).days)[di]
    weight *= np.where((bf_delta >= -7) & (bf_delta <= -1), cfg.BLACK_FRIDAY_PRE_WEEK_FACTOR, 1.)
    weight *= np.where(bf_delta == 0, np.where(ec, cfg.BLACK_FRIDAY_ECOM_FACTOR, cfg.BLACK_FRIDAY_STORE_FACTOR), 1.)
    weight *= np.where(np.isin(bf_delta, [1, 2]), cfg.BLACK_FRIDAY_POST_WEEKEND_FACTOR, 1.)
    weight *= np.where((bf_delta == 3) & ec, cfg.CYBER_MONDAY_ECOM_FACTOR, 1.)
    ramp = ramp_factor(dates.values[di], openings.values[mi])
    weight *= np.where(ec, 1., ramp) / 365.
    brand_margin = shops["marka_kod"].map(cfg.GROSS_MARGIN).to_numpy()[mi]
    offsets = shops["mpk_id"].map(economics["margin_offset"]).to_numpy()[mi]
    margin = brand_margin + offsets + np.take(cfg.MARGIN_MONTH_ADJUSTMENT, month - 1)
    margin += np.where(ec, cfg.ECOM_MARGIN_ADJUSTMENT, 0.) \
        + np.where(bf_delta == 0, cfg.BLACK_FRIDAY_MARGIN_ADJUSTMENT, 0.)
    return pd.DataFrame({
        "data": dates.values[di], "mpk_id": shops["mpk_id"].to_numpy()[mi],
        "weight": weight, "cogs_weight": weight * (1. - margin),
    })


def monthly_profile(profile, mpk, planned=False):
    result = profile.assign(miesiac=month_start(profile["data"])).groupby(
        ["miesiac", "mpk_id"], as_index=False, sort=True
    )[["weight", "cogs_weight"]].sum()
    metadata = mpk.set_index("mpk_id")
    opening_column = "data_otwarcia_plan" if planned else "data_otwarcia"
    result["fraction"] = active_fraction(
        result["miesiac"], result["mpk_id"].map(metadata[opening_column]),
        result["mpk_id"].map(metadata["data_zamkniecia"]),
    )
    result["utility_fraction"] = result["fraction"] * utilities_season(result["miesiac"].dt.month)
    return result


def build_daily(profile, mpk, economics, rng):
    p = profile.loc[profile["data"] <= cfg.DAILY_END].copy()
    meta = mpk.set_index("mpk_id")
    brand = p["mpk_id"].map(meta["marka_kod"])
    ec = p["mpk_id"].map(meta["typ_mpk"]).eq("E-commerce").to_numpy()
    fy = fiscal_year(p["data"])
    trend = (1. + cfg.STORE_LFL_GROWTH) ** (fy - 2023)
    declining, current = {2023: 1.}, 1.
    for year, growth in cfg.DECLINING_STORE_GROWTH.items():
        current *= 1. + growth
        declining[year] = current
    trend = np.where(brand.eq(cfg.DECLINING_BRAND) & ~ec, pd.Series(fy).map(declining), trend)
    ec_growth = np.where(brand.eq(cfg.FAST_ECOM_BRAND), cfg.FAST_ECOM_GROWTH, cfg.ECOM_GROWTH)
    trend = np.where(ec, (1. + ec_growth) ** (fy - 2023), trend)
    warm = month_start(p["data"]).to_numpy() == np.datetime64(cfg.WEATHER_MONTH)
    weather = np.where(warm, brand.map(cfg.WARM_MONTH_FACTOR), 1.)
    sigma = np.where(ec, cfg.DAILY_SIGMA_ECOM, cfg.DAILY_SIGMA_STORE)
    noise = rng.lognormal(-sigma * sigma / 2., sigma)
    sales = p["mpk_id"].map(economics["annual_base"]).to_numpy() * p["weight"].to_numpy() \
        * trend * weather * noise
    base_year = fy == 2023
    ec_scale = (sales[base_year & ~ec].sum() * cfg.ECOM_SHARE_2023 /
                (1. - cfg.ECOM_SHARE_2023) / sales[base_year & ec].sum())
    sales *= np.where(ec, ec_scale, 1.)
    sales = np.round(sales, 2)
    cogs_ratio = (p["cogs_weight"] / p["weight"]).to_numpy() \
        - np.where(warm, cfg.WARM_MONTH_MARGIN_PP, 0.)
    basket = brand.map(cfg.BASKET).to_numpy() * np.where(ec, cfg.ECOM_BASKET_FACTOR, 1.)
    receipts = np.maximum(1, np.rint(sales / basket)).astype(np.int64)
    items = np.rint(receipts * np.where(brand.eq(cfg.MULTI_ITEM_BRAND), cfg.MULTI_ITEM_PER_BASKET,
                                       cfg.ITEMS_PER_BASKET)).astype(np.int64)
    return pd.DataFrame({
        "data": p["data"].to_numpy(), "mpk_id": p["mpk_id"].to_numpy(),
        "sprzedaz_netto_pln": sales, "koszt_wlasny_pln": np.round(sales * cogs_ratio, 2),
        "liczba_paragonow": receipts, "liczba_sztuk": items,
    })


def monthly_sales(daily):
    return daily.assign(miesiac=month_start(daily["data"])).groupby(
        ["miesiac", "mpk_id"], as_index=False, sort=True
    )[["sprzedaz_netto_pln", "koszt_wlasny_pln", "liczba_paragonow", "liczba_sztuk"]].sum()


def long_accounts(frame, accounts, scenario):
    result = frame.melt(id_vars=["miesiac", "mpk_id"], value_vars=accounts,
                        var_name="konto_id", value_name="kwota_pln").dropna(subset=["kwota_pln"])
    result["scenariusz_kod"] = scenario
    result["kwota_pln"] = result["kwota_pln"].round(2)
    return result[["miesiac", "mpk_id", "konto_id", "scenariusz_kod", "kwota_pln"]]


def build_actual(monthly, mpk, actual_profile):
    sales = monthly.loc[monthly["miesiac"] <= cfg.CLOSED_END].merge(mpk, on="mpk_id")
    sales = sales.merge(actual_profile[["miesiac", "mpk_id", "fraction"]],
                        on=["miesiac", "mpk_id"], validate="one_to_one")
    sales["4010"], sales["4510"] = sales["sprzedaz_netto_pln"], sales["koszt_wlasny_pln"]
    stores = sales.loc[sales["typ_mpk"] == "Sklep"].copy()
    fy = fiscal_year(stores["miesiac"])
    age = fy - 2023
    nominal = stores["powierzchnia_m2"].astype(float) * stores["marka_kod"].map(cfg.DENSITY) \
        * stores["kraj_kod"].map(cfg.COUNTRY_FACTOR) * cfg.SALES_SCALE / 12.
    fixed = nominal * stores["fraction"]
    stores["5110"] = fixed * cfg.STORE_PAYROLL_FIXED_SHARE \
        * stores["kraj_kod"].map(cfg.WAGE_COUNTRY_INDEX) * (1. + cfg.WAGE_GROWTH) ** age \
        + cfg.STORE_PAYROLL_VARIABLE_SHARE * stores["4010"]
    rent_index, cumulative = {}, 1.
    for year, increase in cfg.RENT_INDEX_ACT.items():
        cumulative *= increase
        rent_index[year] = cumulative
    rent = pd.Series(fy, index=stores.index).map(rent_index)
    shock = (stores["marka_kod"] == cfg.RENT_SHOCK_BRAND) & (stores["kraj_kod"] == cfg.RENT_SHOCK_COUNTRY) \
        & (stores["miesiac"] >= cfg.RENT_SHOCK_START)
    rent *= np.where(shock, (1. + cfg.RENT_SHOCK_INCREASE) / cfg.RENT_INDEX_ACT[2026], 1.)
    stores["5120"] = fixed * cfg.STORE_RENT_SHARE * rent
    stores["5130"] = fixed * cfg.STORE_UTILITIES_SHARE * utilities_season(stores["miesiac"].dt.month) \
        * (1. + cfg.UTILITY_GROWTH) ** age
    stores["5910"] = cfg.STORE_OTHER_SHARE * stores["4010"] + stores["powierzchnia_m2"].astype(float) \
        * cfg.STORE_OTHER_FIXED_PER_M2 * stores["fraction"] * (1. + cfg.HQ_OTHER_GROWTH) ** age
    stores["6010"] = stores["powierzchnia_m2"].astype(float) * cfg.STORE_DEPRECIATION_PER_M2 * stores["fraction"]
    ecom = sales.loc[sales["typ_mpk"] == "E-commerce"].copy()
    fy_ec = fiscal_year(ecom["miesiac"])
    rate = np.where(ecom["kraj_kod"].eq("PL"), cfg.ORDER_COST_PL_2023, cfg.ORDER_COST_OTHER_2023) \
        * (1. + cfg.ORDER_COST_GROWTH) ** (fy_ec - 2023)
    rate *= np.where(ecom["kraj_kod"].eq(cfg.ORDER_SHOCK_COUNTRY) & (ecom["miesiac"] >= cfg.ORDER_SHOCK_START),
                     1. + cfg.ORDER_SHOCK_INCREASE, 1.)
    ecom["5220"] = ecom["liczba_paragonow"] * rate
    ecom["5230"] = ecom["4010"] * cfg.ECOM_PAYMENT_SHARE
    ecom["5210"] = ecom["4010"] * cfg.ECOM_MARKETING_SHARE
    result = [
        long_accounts(stores, ["4010", "4510", "5110", "5120", "5130", "5910", "6010"], "ACT"),
        long_accounts(ecom, ["4010", "4510", "5210", "5220", "5230"], "ACT"),
    ]
    hq = build_hq_actual(sales, mpk)
    result.append(long_accounts(hq, ["5210", "5310", "5410", "5420", "5910", "6010"], "ACT"))
    return pd.concat(result, ignore_index=True)


def build_hq_actual(sales, mpk):
    base = sales.loc[fiscal_year(sales["miesiac"]) == 2023]
    base_group = base["4010"].sum()
    brand_shares = base.groupby("marka_kod")["4010"].sum() / base_group
    base_group *= cfg.HQ_COST_SCALE
    months = pd.DataFrame({"miesiac": pd.date_range(cfg.DAILY_START, cfg.CLOSED_END, freq="MS")})
    hq = months.merge(mpk.loc[mpk["typ_mpk"] == "Centrala"], how="cross")
    dates = pd.DatetimeIndex(hq["miesiac"])
    age = fiscal_year(dates) - 2023
    weight = hq["mpk_id"].map(cfg.HQ_PAYROLL_WEIGHTS).fillna(cfg.HQ_MARKETING_PAYROLL_WEIGHT)
    pay_step = fiscal_year(dates) - 2023
    hq["5410"] = base_group * cfg.HQ_PAYROLL_SHARE / 12. / (1. + cfg.HQ_ANNUAL_BONUS / 12.) \
        * weight * (1. + cfg.WAGE_GROWTH) ** pay_step \
        * np.where(dates.month == cfg.HQ_BONUS_MONTH, 1. + cfg.HQ_ANNUAL_BONUS, 1.)
    license_season = 1. + pd.Series(dates.month).map(cfg.HQ_IT_RENEWALS).fillna(0.).to_numpy()
    license_norm = 1. + sum(cfg.HQ_IT_RENEWALS.values()) / 12.
    other_units = hq["mpk_id"].nunique() - 1
    it_weights = np.where(hq["mpk_id"].eq(cfg.HQ_IT_MPK), cfg.HQ_IT_DEPARTMENT_SHARE,
                          (1. - cfg.HQ_IT_DEPARTMENT_SHARE) / other_units)
    hq["5420"] = base_group * cfg.HQ_IT_SHARE / 12. * it_weights * license_season / license_norm \
        * (1. + cfg.HQ_IT_GROWTH) ** age
    hq["5910"] = base_group * cfg.HQ_OTHER_SHARE / 12. * weight * (1. + cfg.HQ_OTHER_GROWTH) ** age
    hq["6010"] = base_group * cfg.HQ_DEPRECIATION_SHARE / 12. * weight * (1. + cfg.HQ_OTHER_GROWTH) ** age
    marketing = hq["dzial_centrali"].eq("Marketing")
    hq["5210"] = np.where(
        marketing,
        base_group * cfg.HQ_MARKETING_SHARE / 12. * hq["marka_kod"].map(brand_shares).fillna(0)
        * np.take(cfg.HQ_MARKETING_SEASONALITY, dates.month - 1) / np.mean(cfg.HQ_MARKETING_SEASONALITY)
        * (1. + cfg.HQ_MARKETING_GROWTH) ** age,
        np.nan,
    )
    stores_total = sales.loc[sales["typ_mpk"] == "Sklep"].groupby("miesiac")["4010"].sum()
    hq["5310"] = np.where(hq["mpk_id"].eq(cfg.HQ_LOGISTICS_MPK),
                        hq["miesiac"].map(stores_total) * cfg.HQ_LOGISTICS_STORE_SHARE, np.nan)
    return hq


def fill_peer_rates(rates, metadata):
    area = metadata["powierzchnia_m2"].astype(float).fillna(1.)
    unit = metadata[["marka_kod", "kraj_kod", "typ_mpk"]].copy()
    unit["rate"] = rates.reindex(metadata.index) / area
    peers = unit.groupby(["marka_kod", "kraj_kod", "typ_mpk"])["rate"].transform("mean")
    result = unit["rate"].fillna(peers) * area
    if result.isna().any():
        missing = result.index[result.isna()].tolist()
        raise ValueError(f"Brak bazy ACT i porównywalnych MPK: {missing}")
    return result


def build_budget(actual, monthly, mpk, actual_profile, planned_profile):
    metadata = mpk.loc[(mpk["typ_mpk"] != "Centrala") & (mpk["status"] != "Planowany")].set_index("mpk_id")
    blocks = []
    for year in (2024, 2025, 2026):
        prior = actual.loc[fiscal_year(actual["miesiac"]) == year - 1]
        previous = prior.pivot_table(index="mpk_id", columns="konto_id", values="kwota_pln",
                                     aggfunc="sum").reindex(metadata.index)
        prof_previous = actual_profile.loc[fiscal_year(actual_profile["miesiac"]) == year - 1] \
            .groupby("mpk_id")[["weight", "fraction", "utility_fraction"]].sum().reindex(metadata.index)
        current = planned_profile.loc[fiscal_year(planned_profile["miesiac"]) == year].merge(
            metadata.reset_index(), on="mpk_id", validate="many_to_one"
        )
        annual_base = fill_peer_rates(previous["4010"] / prof_previous["weight"], metadata)
        current["growth"] = np.where(current["typ_mpk"].eq("E-commerce"), 1. + cfg.BUD_ECOM_GROWTH,
                                     1. + current["marka_kod"].map(cfg.BUD_STORE_GROWTH))
        base = current["mpk_id"].map(annual_base) * current["growth"]
        current["4010"], current["4510"] = base * current["weight"], base * current["cogs_weight"]
        stores = current.loc[current["typ_mpk"] == "Sklep"].copy()
        store_meta = metadata.loc[metadata["typ_mpk"] == "Sklep"]
        fixed_pay = (previous["5110"] - cfg.STORE_PAYROLL_VARIABLE_SHARE * previous["4010"]) / prof_previous["fraction"]
        pay_rate = fill_peer_rates(fixed_pay, store_meta)
        rent_rate = fill_peer_rates(previous["5120"] / prof_previous["fraction"], store_meta)
        media_rate = fill_peer_rates(previous["5130"] / prof_previous["utility_fraction"], store_meta)
        other_fixed = (previous["5910"] - cfg.STORE_OTHER_SHARE * previous["4010"]) / prof_previous["fraction"]
        other_rate = fill_peer_rates(other_fixed, store_meta)
        depreciation_rate = fill_peer_rates(previous["6010"] / prof_previous["fraction"], store_meta)
        stores["5110"] = stores["mpk_id"].map(pay_rate) * (1. + cfg.WAGE_GROWTH) * stores["fraction"] \
            + cfg.STORE_PAYROLL_VARIABLE_SHARE * stores["4010"]
        stores["5120"] = stores["mpk_id"].map(rent_rate) * (1. + cfg.BUD_RENT_GROWTH) * stores["fraction"]
        stores["5130"] = stores["mpk_id"].map(media_rate) * (1. + cfg.UTILITY_GROWTH) * stores["utility_fraction"]
        stores["5910"] = stores["mpk_id"].map(other_rate) * (1. + cfg.HQ_OTHER_GROWTH) * stores["fraction"] \
            + cfg.STORE_OTHER_SHARE * stores["4010"]
        stores["6010"] = stores["mpk_id"].map(depreciation_rate) * stores["fraction"]
        ecom = current.loc[current["typ_mpk"] == "E-commerce"].copy()
        prev_orders = monthly.loc[fiscal_year(monthly["miesiac"]) == year - 1] \
            .groupby("mpk_id")["liczba_paragonow"].sum()
        prior_order_rate = previous["5220"] / prev_orders.reindex(previous.index)
        estimated_orders = ecom["4010"] / (ecom["marka_kod"].map(cfg.BASKET) * cfg.ECOM_BASKET_FACTOR)
        ecom["5220"] = estimated_orders * ecom["mpk_id"].map(prior_order_rate) * (1. + cfg.ORDER_COST_GROWTH)
        ecom["5230"] = ecom["4010"] * cfg.ECOM_PAYMENT_SHARE
        ecom["5210"] = ecom["4010"] * cfg.ECOM_MARKETING_SHARE
        blocks.extend([
            long_accounts(stores, ["4010", "4510", "5110", "5120", "5130", "5910", "6010"], "BUD"),
            long_accounts(ecom, ["4010", "4510", "5210", "5220", "5230"], "BUD"),
        ])
        hq_prior = prior.loc[prior["mpk_id"].str.startswith("HQ-")].groupby(
            ["mpk_id", "konto_id"], as_index=False
        )["kwota_pln"].sum()
        months = pd.DataFrame({"miesiac": pd.date_range(f"{year}-04-01", f"{year + 1}-03-01", freq="MS")})
        hq = hq_prior.merge(months, how="cross")
        month = hq["miesiac"].dt.month.to_numpy()
        season = np.ones(len(hq))
        season = np.where(hq["konto_id"].eq("5410"),
                          np.where(month == cfg.HQ_BONUS_MONTH, 1. + cfg.HQ_ANNUAL_BONUS, 1.), season)
        season = np.where(hq["konto_id"].eq("5420"),
                          1. + pd.Series(month).map(cfg.HQ_IT_RENEWALS).fillna(0.).to_numpy(), season)
        season = np.where(hq["konto_id"].eq("5210"), np.take(cfg.HQ_MARKETING_SEASONALITY, month - 1), season)
        hq["season"] = season
        annual_growth = hq["konto_id"].map({
            "5410": cfg.WAGE_GROWTH, "5420": cfg.HQ_IT_GROWTH, "5210": cfg.HQ_MARKETING_GROWTH,
            "5310": cfg.HQ_OTHER_GROWTH, "5910": cfg.HQ_OTHER_GROWTH, "6010": cfg.HQ_OTHER_GROWTH,
        })
        hq["kwota_pln"] *= (1. + annual_growth) * hq["season"] / \
            hq.groupby(["mpk_id", "konto_id"])["season"].transform("sum")
        warehouse = hq["konto_id"].eq("5310")
        total_stores = stores.groupby("miesiac")["4010"].sum()
        hq.loc[warehouse, "kwota_pln"] = hq.loc[warehouse, "miesiac"].map(total_stores) * cfg.HQ_LOGISTICS_STORE_SHARE
        hq["scenariusz_kod"] = "BUD"
        hq["kwota_pln"] = hq["kwota_pln"].round(2)
        blocks.append(hq[["miesiac", "mpk_id", "konto_id", "scenariusz_kod", "kwota_pln"]])
    return pd.concat(blocks, ignore_index=True)


def build_forecast(actual, budget, mpk, actual_profile, planned_profile):
    closed = actual.loc[fiscal_year(actual["miesiac"]) == 2026].copy()
    closed["scenariusz_kod"] = "FC"
    future = budget.loc[budget["miesiac"].between(cfg.FORECAST_START, cfg.FORECAST_END)].pivot(
        index=["miesiac", "mpk_id"], columns="konto_id", values="kwota_pln"
    ).reset_index().merge(mpk, on="mpk_id")
    actual_w = actual_profile.set_index(["miesiac", "mpk_id"])["weight"]
    planned_w = planned_profile.set_index(["miesiac", "mpk_id"])["weight"]
    ratios = actual_w / planned_w
    keys = pd.MultiIndex.from_frame(future[["miesiac", "mpk_id"]])
    delayed = future["mpk_id"].isin(cfg.DELAYED_OPENINGS)
    multiplier = np.where(future["marka_kod"].eq(cfg.DECLINING_BRAND), cfg.FC_DECLINING_FACTOR, 1.)
    multiplier *= np.where(delayed, ratios.reindex(keys).fillna(1.).to_numpy(), 1.)
    sales_change = future["4010"] * (multiplier - 1.)
    future["4010"] *= multiplier
    future["4510"] *= multiplier
    stores = future["typ_mpk"].eq("Sklep")
    ecom = future["typ_mpk"].eq("E-commerce")
    future.loc[stores, "5110"] += cfg.STORE_PAYROLL_VARIABLE_SHARE * sales_change[stores]
    future.loc[stores, "5910"] += cfg.STORE_OTHER_SHARE * sales_change[stores]
    for account in ("5210", "5220", "5230"):
        future.loc[ecom, account] *= multiplier[ecom]
    shocked_rent = stores & future["marka_kod"].eq(cfg.RENT_SHOCK_BRAND) & future["kraj_kod"].eq(cfg.RENT_SHOCK_COUNTRY)
    future.loc[shocked_rent, "5120"] *= (1. + cfg.RENT_SHOCK_INCREASE) / (1. + cfg.BUD_RENT_GROWTH)
    future.loc[ecom & future["kraj_kod"].eq(cfg.ORDER_SHOCK_COUNTRY), "5220"] *= 1. + cfg.ORDER_SHOCK_INCREASE
    result = long_accounts(future, [account[0] for account in cfg.ACCOUNTS], "FC")
    return pd.concat([closed, result], ignore_index=True)


def build_categories(daily, mpk):
    closed = daily.loc[daily["data"] <= cfg.CLOSED_END].merge(
        mpk[["mpk_id", "marka_kod", "kraj_kod", "kanal"]], on="mpk_id", validate="many_to_one"
    )
    closed["miesiac"] = month_start(closed["data"])
    keys = ["miesiac", "marka_kod", "kraj_kod", "kanal"]
    totals = closed.groupby(keys, as_index=False, sort=True)[
        ["sprzedaz_netto_pln", "koszt_wlasny_pln", "liczba_sztuk"]
    ].sum()
    weights = np.array([cfg.CATEGORY_BASE_WEIGHTS[brand] for brand in totals["marka_kod"]], dtype=float)
    month = totals["miesiac"].dt.month.to_numpy()
    summer = np.isin(month, [5, 6, 7, 8])
    winter = np.isin(month, [10, 11, 12, 1, 2])
    weights[:, 1] *= np.where(winter, cfg.SWEATERS_WINTER_FACTOR, 1.)
    weights[:, 3] *= np.where(summer, cfg.SUMMER_DRESSES_TSHIRTS_FACTOR, 1.)
    weights[:, 4] *= np.where(summer, cfg.SUMMER_DRESSES_TSHIRTS_FACTOR, 1.)
    weights[:, 6:8] *= np.where(month == 12, cfg.DECEMBER_ACCESSORIES_UNDERWEAR_FACTOR, 1.)[:, None]
    outerwear = np.where(np.isin(month, [10, 11, 12, 1]), cfg.OUTERWEAR_WINTER_SHARE,
                         np.where(summer, cfg.OUTERWEAR_SUMMER_SHARE,
                                  np.where(month == 9, cfg.OUTERWEAR_SEPTEMBER_SHARE, cfg.OUTERWEAR_OTHER_SHARE)))
    outerwear *= totals["marka_kod"].map(cfg.OUTERWEAR_BRAND_FACTOR).to_numpy()
    outerwear *= np.where(totals["miesiac"].eq(cfg.WEATHER_MONTH), cfg.OUTERWEAR_WEATHER_FACTOR, 1.)
    weights[:, 0] = 0.
    weights *= ((1. - outerwear) / weights.sum(axis=1))[:, None]
    weights[:, 0] = outerwear
    category_codes = np.array([row[0] for row in cfg.CATEGORIES])
    indexes = np.repeat(np.arange(len(totals)), len(category_codes))
    allowed = weights.ravel() > 0
    result = totals.iloc[indexes][keys].reset_index(drop=True)
    result["kategoria_kod"] = np.tile(category_codes, len(totals))
    anchor = weights.argmax(axis=1)
    for column in ("sprzedaz_netto_pln", "koszt_wlasny_pln", "liczba_sztuk"):
        scale = 1 if column == "liczba_sztuk" else 100
        total_units = np.rint(totals[column].to_numpy() * scale).astype(np.int64)
        parts = np.rint(total_units[:, None] * weights).astype(np.int64)
        parts[np.arange(len(totals)), anchor] += total_units - parts.sum(axis=1)
        result[column] = parts.ravel() if scale == 1 else parts.ravel() / scale
    return result.loc[allowed].reset_index(drop=True)


def build_fx(rng):
    dates = pd.date_range(cfg.DAILY_START, cfg.FORECAST_START, freq="MS")
    currencies = list(cfg.FX_BASE)
    shock = rng.normal(0, cfg.FX_MONTHLY_VOLATILITY, (len(dates), len(currencies)))
    state = np.zeros_like(shock)
    for i in range(len(dates)):
        state[i] = (cfg.FX_MEAN_REVERSION * state[i - 1] if i else 0.) + shock[i]
    rates = np.array(list(cfg.FX_BASE.values())) * (1. + state)
    return pd.DataFrame({
        "miesiac": np.repeat(dates.values, len(currencies)),
        "waluta": np.tile(currencies, len(dates)), "kurs_sredni_pln": np.round(rates.ravel(), 6),
    })


def build_aggregate(pnl, mpk):
    source = pnl.loc[pnl["konto_id"].isin(["4010", "4510"])].merge(
        mpk[["mpk_id", "marka_kod", "kraj_kod", "kanal"]], on="mpk_id", validate="many_to_one"
    )
    keys = ["miesiac", "marka_kod", "kraj_kod", "kanal", "scenariusz_kod"]
    return source.pivot_table(index=keys, columns="konto_id", values="kwota_pln", aggfunc="sum") \
        .rename(columns={"4010": "sprzedaz_netto_pln", "4510": "koszt_wlasny_pln"}) \
        .reset_index().rename_axis(None, axis=1).round(2)


def build_plan(aggregate):
    keys = ["marka_kod", "kraj_kod", "kanal"]
    fc = aggregate.loc[aggregate["scenariusz_kod"].eq("FC")].groupby(keys, as_index=False)["sprzedaz_netto_pln"].sum()
    fc = fc.rename(columns={"sprzedaz_netto_pln": "sprzedaz_fc_2026_27_pln"})
    fc["wzrost_docelowy_pct"] = fc["marka_kod"].map(cfg.TARGET_GROWTH_2027) \
        + np.where(fc["kanal"].eq("E-commerce"), cfg.TARGET_ECOM_EXTRA_PP, 0.)
    fc["cel_roczny_pln"] = np.round(fc["sprzedaz_fc_2026_27_pln"] * (1. + fc["wzrost_docelowy_pct"]), -3)
    shares = []
    for year, label in [(2024, "prior"), (2025, "ly")]:
        rows = aggregate.loc[aggregate["scenariusz_kod"].eq("ACT") &
                             (fiscal_year(aggregate["miesiac"]) == year)].copy()
        rows["month"] = rows["miesiac"].dt.month
        rows[label] = rows["sprzedaz_netto_pln"] / rows.groupby(keys)["sprzedaz_netto_pln"].transform("sum")
        shares.append(rows[keys + ["month", label]])
    plan = shares[0].merge(shares[1], on=keys + ["month"], validate="one_to_one").merge(
        fc[keys + ["cel_roczny_pln"]], on=keys, validate="many_to_one"
    )
    plan["miesiac"] = pd.to_datetime({"year": np.where(plan["month"] < cfg.FY_START_MONTH, 2028, 2027),
                                     "month": plan["month"], "day": 1})
    plan["udzial_ly"] = plan["ly"]
    plan["udzial_sr2"] = (plan["ly"] + plan["prior"]) / 2.
    plan["plan_ly_pln"] = (plan["cel_roczny_pln"] * plan["udzial_ly"]).round(2)
    plan["plan_sr2_pln"] = (plan["cel_roczny_pln"] * plan["udzial_sr2"]).round(2)
    return plan, fc
