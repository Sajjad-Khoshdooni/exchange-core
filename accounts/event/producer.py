import json
import logging

from confluent_kafka import Producer
from django.conf import settings

from accounts.utils.dto import BaseEvent


logger = logging.getLogger(__name__)


def delivery_report(err, msg):
    if err is not None:
        logger.info('Message delivery failed: {}'.format(err))
    else:
        logger.warning('Message delivered to {} [{}]'.format(msg.topic(), msg.partition()))


class KafkaProducer:
    def __init__(self):
        self.producer = Producer({'bootstrap.servers': settings.KAFKA_HOST_URL})

    def produce(self, event: BaseEvent):
        data = json.dumps(event.serialize())

        self.producer.poll(0)
        self.producer.produce(event.topic, data.encode('utf-8'), callback=delivery_report)

        self.producer.flush()


def get_kafka_producer() -> KafkaProducer:
    global _producer
    if _producer is None:
        _producer = KafkaProducer()
    return _producer
