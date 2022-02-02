from celery import shared_task


@shared_task()
def handle_withdraw(transfer_id: int):
    pass
