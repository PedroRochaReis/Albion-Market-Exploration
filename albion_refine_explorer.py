import re
import json
import pandas as pd
from albion_market_data_API import get_albion_prices
from mapping_generator import hide_to_previous_leather
from mapping_generator import generate_tiers



with open("albion_mapping.json", "r", encoding="utf-8") as f:
    mapping = json.load(f)

value_by_refined = mapping["value_by_refined"]
cities = mapping["royal_cities"]


def get_refined_data(max_tier=8):

    item_raw = generate_tiers("HIDE", max_tier=max_tier)
    item_raw2 = generate_tiers("LEATHER", max_tier=max_tier)
    item_refined = generate_tiers("LEATHER", max_tier=max_tier)

    prices_raw = get_albion_prices(item_raw, craft=False, locations=cities)
    prices_raw2 = get_albion_prices(item_raw2, craft=False, locations=cities)
    prices_refined = get_albion_prices(item_refined, craft=False, locations=cities)

    raw_resource_table = pd.DataFrame([
        {
            "raw": item.get("item_id"),
            "resource2": hide_to_previous_leather(item.get("item_id")),
            "city": item.get("city"),
            "sell_price_min": item.get("sell_price_min"),
            "sell_price_min_date": item.get("sell_price_min_date")
        }
        for item in prices_raw
    ])

    refined_resource_table = pd.DataFrame([
        {
            "raw": item.get("item_id"),
            "city": item.get("city"),
            "sell_price_min": item.get("sell_price_min"),
            "sell_price_min_date": item.get("sell_price_min_date")
        }
        for item in prices_raw2
    ])

    refined_result_table = pd.DataFrame([
        {
            "refined": item.get("item_id"),
            "city": item.get("city"),
            "buy_price_max": item.get("buy_price_max"),
            "buy_price_max_date": item.get("buy_price_max_date"),
            "sell_price_min": item.get("sell_price_min"),
            "sell_price_min_date": item.get("sell_price_min_date")
        }
        for item in prices_refined
    ])

    raw_resource_table = add_time_since_update(raw_resource_table, "sell_price_min_date")
    refined_resource_table = add_time_since_update(refined_resource_table, "sell_price_min_date")
    refined_result_table = add_time_since_update(refined_result_table, "buy_price_max_date")
    refined_result_table = add_time_since_update(refined_result_table, "sell_price_min_date")

    
    #Formação dos joins
    # Primeira tabela: combina o item bruto com cada cidade de origem
    table1 = pd.DataFrame({
        "resource1": raw_resource_table["raw"],
        "resource2": raw_resource_table["resource2"],
        "city_raw1": raw_resource_table["city"],
        "pelego_amount": 2,
        "pelego_raw": raw_resource_table["sell_price_min"],
        "time_pelego": raw_resource_table["time_since_update"],
    })

    refined_resource_table["resource2"] = refined_resource_table["raw"].apply(hide_to_previous_leather)

    # Segunda tabela: combina o item secundário com cada cidade de origem do segundo recurso
    table2 = pd.DataFrame({
        "resource2": refined_resource_table["resource2"],
        "city_raw2": refined_resource_table["city"],
        "couro_amount": 1,
        "couro_raw": refined_resource_table["sell_price_min"],
        "time_couro_raw": refined_resource_table["time_since_update"],
    })

    # Terceira tabela: combina os itens refinados com as cidades de venda
    table3 = pd.DataFrame({
        "resource1": refined_result_table.apply(lambda x: to_refined_item(x["refined"]), axis=1),
        "resource_end": refined_result_table["refined"],
        "city_sold": refined_result_table["city"],
        "couro_refined": 1,
        "couro_raw_instant": refined_result_table["buy_price_max"],
        "time_couro_raw_instant": refined_result_table["time_since_update"],
        "couro_raw_order": refined_result_table["sell_price_min"],
        "time_couro_raw_order": refined_result_table["time_since_update"],
    })

    # Produto cartesiano entre as tabelas 1 e 2 usando o recurso comum
    base = table1.merge(table2, on=["resource2"], how="outer")
    merged = base.merge(table3, on=["resource1"], how="left")


    merged["retorno"] = 0.438
    merged["fee"] = round(get_value_for_item(merged["resource_end"], value_by_refined) * 1.05, 0)
    merged["consumo_efetivo"] = (merged["pelego_amount"] * merged["pelego_raw"] + merged["couro_amount"] * merged["couro_raw"]) * (1 - merged["retorno"]) + merged["fee"]
    merged["sell_tax"] = 0.04
    merged["sell_tax_order"] = 0.025
    merged["profit_instant"] = merged["couro_raw_instant"] - merged["consumo_efetivo"] - (merged["couro_raw_instant"] * merged["sell_tax"])
    merged["profit_order"] = merged["couro_raw_order"] - merged["consumo_efetivo"] - (merged["couro_raw_order"] * merged["sell_tax"]) + merged["couro_raw_order"] * merged["sell_tax_order"]
    merged["profit_percentage_instant"] = round((merged["profit_instant"] / merged["consumo_efetivo"]) * 100, 2)
    merged["profit_percentage_order"] = round((merged["profit_order"] / merged["consumo_efetivo"]) * 100, 2)
    merged["best_profit_percentage"] = merged[["profit_percentage_instant", "profit_percentage_order"]].max(axis=1)


    df_instant = merged[merged["profit_instant"] > 0]
    df_order = merged[merged["profit_order"] > 0]

    df_result = pd.concat([df_instant, df_order]).drop_duplicates().reset_index(drop=True).sort_values("best_profit_percentage", ascending=False)

    df_result = df_result[(df_result['pelego_raw'] > 0) & (df_result['couro_raw'] > 0) & (df_result['couro_raw_instant'] > 0) & (df_result['couro_raw_order'] > 0)]

    return df_result



def format_timedelta(td):
    if pd.isna(td):
        return None
    total_seconds = int(td.total_seconds())
    if total_seconds >= 86400:
        return ""
    value = f"{total_seconds // 3600:02d}:{(total_seconds % 3600) // 60:02d}:{total_seconds % 60:02d}"
    return re.sub(r"^(\d{2}):(\d{2}):(\d{2})$", r"\1:\2:\3", value)


def safe_dt(value):
    if value is None or value == 0 or pd.isna(value):
        return pd.NaT
    try:
        return pd.to_datetime(value, utc=True, errors="coerce")
    except Exception:
        return pd.NaT


def add_time_since_update(df, date_col):
    df = df.copy()
    df[date_col] = df[date_col].apply(safe_dt)
    df["time_since_update"] = df.apply(
        lambda row: (
            pd.Timestamp.utcnow() - row[date_col]
        ) if pd.notna(row[date_col]) else pd.NaT,
        axis=1,
    )
    df["time_since_update"] = df["time_since_update"].apply(format_timedelta)
    return df

def get_value_for_item(item_name, mapping):
    if hasattr(item_name, "apply"):
        return item_name.apply(lambda x: get_value_for_item(x, mapping))

    if item_name is None or pd.isna(item_name):
        return 0

    if item_name in mapping:
        return mapping[item_name]

    for key, value in mapping.items():
        if isinstance(item_name, str) and item_name.startswith(key.split("_LEVEL")[0]):
            return value

    return 0


def to_refined_item(item_name):
    return re.sub(r"LEATHER", "HIDE", item_name)