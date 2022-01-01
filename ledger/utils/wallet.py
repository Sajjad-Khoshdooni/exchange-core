from ledger.models import Wallet, NetworkWallet, Network


def generate_deposit_address(wallet: Wallet, network: Network) -> NetworkWallet:

    return NetworkWallet.objects.create(
        wallet=wallet, network=network, address='test'
    )
