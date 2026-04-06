COUNTRY_META = {
    "Czech Republic":   {"qid": "Q213",  "iso": "cz", "lang": "cs"},
    "Slovakia":         {"qid": "Q214",  "iso": "sk", "lang": "sk"},
    "Austria":          {"qid": "Q40",   "iso": "at", "lang": "de"},
    "Germany":          {"qid": "Q183",  "iso": "de", "lang": "de"},
    "Poland":           {"qid": "Q36",   "iso": "pl", "lang": "pl"},
    "Hungary":          {"qid": "Q28",   "iso": "hu", "lang": "hu"},
    "Latvia":           {"qid": "Q211",  "iso": "lv", "lang": "lv"},
    "Lithuania":        {"qid": "Q37",   "iso": "lt", "lang": "lt"},
    "Estonia":          {"qid": "Q191",  "iso": "ee", "lang": "et"},
    "Norway":           {"qid": "Q20",   "iso": "no", "lang": "no"},
    "Sweden":           {"qid": "Q34",   "iso": "se", "lang": "sv"},
    "Finland":          {"qid": "Q33",   "iso": "fi", "lang": "fi"},
    "Denmark":          {"qid": "Q35",   "iso": "dk", "lang": "da"},
    "Portugal":         {"qid": "Q45",   "iso": "pt", "lang": "pt"},
    "Spain":            {"qid": "Q29",   "iso": "es", "lang": "es"},
    "France":           {"qid": "Q142",  "iso": "fr", "lang": "fr"},
    "Italy":            {"qid": "Q38",   "iso": "it", "lang": "it"},
    "Netherlands":      {"qid": "Q55",   "iso": "nl", "lang": "nl"},
    "Belgium":          {"qid": "Q31",   "iso": "be", "lang": "fr"},
    "Switzerland":      {"qid": "Q39",   "iso": "ch", "lang": "de"},
    "Greece":           {"qid": "Q41",   "iso": "gr", "lang": "el"},
    "Romania":          {"qid": "Q218",  "iso": "ro", "lang": "ro"},
    "Bulgaria":         {"qid": "Q219",  "iso": "bg", "lang": "bg"},
    "Croatia":          {"qid": "Q224",  "iso": "hr", "lang": "hr"},
    "Slovenia":         {"qid": "Q215",  "iso": "si", "lang": "sl"},
    "Serbia":           {"qid": "Q403",  "iso": "rs", "lang": "sr"},
}

def country_meta(country_name):
    """Get qid, iso, lang for a country name (as used in filenames)."""
    return COUNTRY_META.get(country_name, {"qid": None, "iso": None, "lang": "en"})
