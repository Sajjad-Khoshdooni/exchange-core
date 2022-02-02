import base58


def get_base58_address(base16_address: str):
    return base58.b58encode_check(bytes.fromhex(base16_address)).decode()


def get_presentation_address(address: str, network: str) -> str:
    from wallet.models import Secret, CryptoWallet

    wallet_class: CryptoWallet = Secret.get_secret_wallet(network)
    return wallet_class.get_presentation_address(address)
