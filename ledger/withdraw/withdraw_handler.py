from accounts.models import Account
from ledger.models import DepositAddress, Transfer
from ledger.withdraw.fee_handler import FeeHandler
from ledger.withdraw.transaction_creator import TransactionCreatorBuilder
from wallet.models import Secret


class WithdrawHandler:
    @classmethod
    def withdraw_from_transfer(cls, transfer):
        fee_handler = FeeHandler(transfer.network, transfer.wallet.asset)

        if not fee_handler.is_balance_enough_for_fee(transfer.wallet.account):
            fee_handler.supply_fee_for_asset(Account.system(), transfer.wallet.account)
            return
        return cls._creat_transaction_from_transfer(transfer)

    @classmethod
    def _creat_transaction_from_transfer(cls, transfer):
        print('create transaction...')
        deposit_address: DepositAddress = transfer.network.get_deposit_address(transfer.wallet.account)
        wallet_class = Secret.get_secret_wallet(transfer.network.symbol)
        wallet = deposit_address.account_secret.secret
        wallet.__class__ = wallet_class
        transaction_creator = TransactionCreatorBuilder(transfer.network, transfer.wallet.asset,
                                                        wallet).build()
        txid = transaction_creator.from_transfer(transfer)
        transfer.trx_hash = txid
        transfer.status = Transfer.PENDING
        print('change transfer status to %s' % transfer.status)
        transfer.save()

    @classmethod
    def create_transaction_from_not_broadcasts(cls):
        transfers = Transfer.objects.filter(status=Transfer.PROCESSING, source=Transfer.SELF)
        for transfer in transfers:
            fee_handler = FeeHandler(transfer.network, transfer.wallet.asset)

            if not fee_handler.is_balance_enough_for_fee(transfer.wallet.account):
                continue

            cls._creat_transaction_from_transfer(transfer)
