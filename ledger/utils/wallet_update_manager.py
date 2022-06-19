from typing import Tuple

from ledger.utils.wallet_updater import WalletUpdater


class WalletUpdateManager:
    pipeline = None

    def __enter__(self):
        WalletUpdateManager.pipeline = WalletUpdater()

    def __exit__(self, exc_type, exc_val, exc_tb):
        WalletUpdateManager.pipeline.execute()
        WalletUpdateManager.pipeline = None

    @classmethod
    def get_active_or_instant(self) -> WalletUpdater:
        if WalletUpdateManager.pipeline:
            return WalletUpdateManager.pipeline
        else:
            return WalletUpdater(instant=True)
