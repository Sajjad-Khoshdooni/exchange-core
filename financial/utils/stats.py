from financial.utils.withdraw import ZibalChanel


def get_total_fiat_irt():
    channel = ZibalChanel()
    if channel.is_active():
        wallet = channel.get_wallet_data(channel.get_wallet_id())
        return wallet.balance
    else:
        return 0
