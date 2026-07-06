import json
import re
from typing import Dict, List, Optional

with open("albion_mapping.json", "r", encoding="utf-8") as f:   
    mapping = json.load(f)

def generate_tiers(base: str, max_tier: int = 8) -> List[str]:
    out: List[str] = []
    for tier in range(3, max_tier + 1):
        base_name = f"T{tier}_{base}"
        
        out.append(base_name)

        if tier == 3:
            continue
        
        for lvl in range(1, 5):
            out.append(f"{base_name}_LEVEL{lvl}@{lvl}")

    return out


def to_refined_item(item_name: str) -> str:
    pattern = "|".join(mapping["raw_refined_map"].keys())
    return re.sub(pattern, lambda m: mapping["raw_refined_map"][m.group(0)], item_name)

def from_refined_item(item_name: str) -> str:
    reverse_map = {v: k for k, v in mapping["raw_refined_map"].items()}
    pattern = "|".join(reverse_map.keys())
    return re.sub(pattern, lambda m: reverse_map[m.group(0)], item_name)


def previous_refined_item(item_id: str) -> str:
    # Converte qualquer recurso bruto para o refinado
    item_id = to_refined_item(item_id)

    m = re.match(r"^T(\d+)_(LEATHER|METALBAR|PLANKS|CLOTH|STONEBLOCK)(?:_LEVEL(\d)@\d)?$", item_id)
    if not m:
        return item_id

    tier = int(m.group(1))
    resource = m.group(2)
    level = m.group(3)
    previous_tier = tier - 1

    if previous_tier == 3:
        result = f"T3_{resource}"
    elif level:
        result = f"T{previous_tier}_{resource}_LEVEL{level}@{level}"
    else:
        result = f"T{previous_tier}_{resource}"

    # Volta para o recurso bruto
    return from_refined_item(result)