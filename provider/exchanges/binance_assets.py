import json


def _get_assets_dict() -> dict:
    with open('provider/data/binance/spot.json') as f:
        assets = json.load(f)

    return {
        a['symbol']: a for a in assets['symbols']
    }


_spot_dict = _get_assets_dict()


def get_spot_data(symbol: str):
    return _spot_dict.get(symbol)


def get_spot_filter(symbol: str, filter_type: str):
    data = get_spot_data(symbol)

    if not data:
        return

    _filters = list(filter(lambda f: f['filterType'] == filter_type, data['filters']))

    if len(_filters) > 0:
        return _filters[0]
