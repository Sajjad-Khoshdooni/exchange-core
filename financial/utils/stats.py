from financial.utils.withdraw import ZibalChanel, PayirChanel


def get_total_fiat_irt():
    channels = [ZibalChanel(), PayirChanel()]

    total = 0

    for channel in channels:
        if channel.is_active():
            try:
                total += channel.get_total_wallet_irt_value()
            except:
                continue

    return total
