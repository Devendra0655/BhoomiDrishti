DISTRICT_NAME_MAP = {
    "Buldhana":   ["Buldhana", "Buldana"],
    "Gondia":     ["Gondia", "Gondiya"],
    "Gadchiroli": ["Gadchiroli", "Garhchiroli"],
    "Akola":      ["Akola"],
    "Amravati":   ["Amravati"],
    "Bhandara":   ["Bhandara"],
    "Chandrapur": ["Chandrapur"],
    "Nagpur":     ["Nagpur"],
    "Wardha":     ["Wardha"],
    "Washim":     ["Washim"],
    "Yavatmal":   ["Yavatmal"],
}

VARIANT_TO_CANONICAL = {v: k for k, variants in DISTRICT_NAME_MAP.items() for v in variants}
VIDARBHA_DISTRICTS_CANONICAL = list(DISTRICT_NAME_MAP.keys())


def standardize_district_name(name):
    return VARIANT_TO_CANONICAL.get(str(name).strip(), name)