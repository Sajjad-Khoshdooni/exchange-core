from financial.utils.withdraw import ZibalChanel


def get_total_fiat_irt():
    channel = ZibalChanel()
    wallet = channel.get_wallet_data(channel.get_wallet_id())
    return wallet.balance
