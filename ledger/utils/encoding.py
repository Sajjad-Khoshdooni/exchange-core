import base58


def base58_from_hex(hex_string):
    return base58.b58encode_check(bytes.fromhex(hex_string)).decode()
