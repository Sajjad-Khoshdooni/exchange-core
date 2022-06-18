from django.core.management import BaseCommand

from collector.binance_consumer import BinanceConsumer


class Command(BaseCommand):
    help = 'Fetch interface prices'

    def handle(self, *args, **options):
        consumer = BinanceConsumer()
        consumer.consume()
