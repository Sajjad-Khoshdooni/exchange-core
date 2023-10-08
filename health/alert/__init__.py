from health.alert.types import *

_ALERT_TYPES = [
    UnhandledCryptoWithdrawAlert, UnhandledFiatWithdrawAlert, CanceledOTCAlert, AssetHedgeAlert, TotalHedgeAlert,
    RiskyMarginRatioAlert, VaultLowBaseBalanceAlert, HotWalletLowBalanceAlert
]

ALERTS = {t.NAME: t for t in _ALERT_TYPES}

assert len(set(ALERTS)) == len(_ALERT_TYPES)
