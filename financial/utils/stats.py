from financial.utils.withdraw import ZibalChannel, PayirChannel
from ledger.utils.cache import cache_for


@cache_for(time=60)
def get_total_fiat_irt():
    channels = [ZibalChannel(), PayirChannel()]

    total = 0

    for channel in channels:
        if channel.is_active():
            try:
                total += channel.get_total_wallet_irt_value()
            except:
                continue

    return total
