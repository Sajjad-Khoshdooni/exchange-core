from django.core.management import BaseCommand

from tracker.blockchain.eth import EthBlockConsumer


class Command(BaseCommand):
    help = 'Consume events for handling tag subscription'

    def handle(self, *args, **options):
        consumer = EthBlockConsumer()
        consumer.consume()
