import json


def _load_data(path: str):
    with open(path) as f:
        return json.load(f)


_rules = {}

_rule_names = {
    'spot': 'provider/data/binance/spot_rules.json'
}


def get_rules(name: str):
    if name not in _rules:
        _rules[name] = _load_data(_rule_names[name])

    return _rules[name]
