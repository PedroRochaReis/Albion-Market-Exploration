import json
import re
from typing import Dict, List, Optional



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


def hide_to_previous_leather(item_id: str) -> str:
    m = re.match(r"^T(\d+)_HIDE(?:_LEVEL(\d)@\d)?$", item_id)
    if not m:
        return item_id

    tier = int(m.group(1))
    level = m.group(2)
    previous_tier = tier - 1

    if previous_tier == 3:
        return "T3_LEATHER"

    if level:
        return f"T{previous_tier}_LEATHER_LEVEL{level}@{level}"

    return f"T{previous_tier}_LEATHER"