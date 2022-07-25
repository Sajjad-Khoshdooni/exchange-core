from financial.utils.withdraw import ZibalChanel, PayirChanel


def get_total_fiat_irt():
    channels = [ZibalChanel(), PayirChanel()]

    total = 0

    for channel in channels:
        if channel.is_active():
            try:
                wallet = channel.get_wallet_data(channel.get_wallet_id())
                total += wallet.balance
            except:
                continue

    return total
