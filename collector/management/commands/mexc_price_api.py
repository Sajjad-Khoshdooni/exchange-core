from django.core.management import BaseCommand

from collector.mexc_consumer import MexcConsumer


class Command(BaseCommand):
    help = 'Fetch mexc prices'

    def handle(self, *args, **options):
        consumer = MexcConsumer()
        consumer.api_consume()
