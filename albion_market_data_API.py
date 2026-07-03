import re
from typing import Dict, Iterable, List, Optional, Tuple

import pandas as pd
import requests

BASE_URL = "https://west.albion-online-data.com/api/v2/stats/prices"


#Recebe uma lista itens para pesquisar e retorna um dicionário com os preços de cada item
def get_albion_prices(item_id, craft=True, locations=None):
    """Busca os preços de um item no endpoint da Albion Online."""
    item_search = ""
    for i in item_id:
        item_search = item_search + f'{i},'
    url = f"https://west.albion-online-data.com/api/v2/stats/prices/{item_search}.json"
    params = {"locations": ",".join(locations)} if locations else None

    print(url)

    response = requests.get(url, params=params, timeout=20)
    response.raise_for_status()

    #Se não for item de craft, sem tier, retorna apenas so de qualidade 1
    if not craft:
        filtered_data = filter_nonzero_prices(response.json())
        return filtered_data

    return response.json()


def filter_nonzero_prices(prices):
    keys = ("sell_price_min", "sell_price_max", "buy_price_min", "buy_price_max")
    return [p for p in prices if any(int(p.get(k, 0)) > 0 for k in keys)]