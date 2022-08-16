from django.core.management import BaseCommand

from collector.kucoin_consumer import KucoinConsumer


class Command(BaseCommand):
    help = 'Fetch kucoin prices'

    def handle(self, *args, **options):
        consumer = KucoinConsumer()
        consumer.consume()
