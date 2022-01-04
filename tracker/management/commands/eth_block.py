from django.core.management import BaseCommand


class Command(BaseCommand):
    help = 'Consume events for handling tag subscription'

    def handle(self, *args, **options):
        tag_consumer = TagEventConsumer()
        tag_consumer.consume()
