import json
import logging

from confluent_kafka import Producer, KafkaException
from django.conf import settings

from accounts.utils.dto import BaseEvent


logger = logging.getLogger(__name__)


def delivery_report(err, msg):
    if err is not None:
        logger.info('Message delivery failed: {}'.format(err))
    else:
        logger.info('Message delivered to {} [{}]'.format(msg.topic(), msg.partition()))


class KafkaProducer:
    def __init__(self):
        try:
            self.producer = Producer({
                'bootstrap.servers': settings.KAFKA_HOST_URL,
                'socket.timeout.ms': 5000,  # timeout to 5 seconds',
                'delivery.timeout.ms': 5000,
                'message.send.max.retries': 5,
                'request.timeout.ms': 5
            })
        except KafkaException as e:
            logger.warning('KafkaException', extra={
                'e': e
            })
        except Exception as e:
            logger.warning('KafkaClientException', extra={
                'e': e
            })

    def produce(self, event: BaseEvent):
        data = json.dumps(event.serialize())

        if not settings.KAFKA_HOST_URL:
            return

        try:
            self.producer.poll(0)
            self.producer.produce('crm', data.encode('utf-8'), callback=delivery_report)

            self.producer.flush()
        except KafkaException as e:
            logger.warning('KafkaException', extra={
                'e': e,
                'event': event
            })
        except Exception as e:
            logger.warning('KafkaClientException', extra={
                'e': e,
                'event': event
            })


_producer = None


def get_kafka_producer() -> KafkaProducer:
    global _producer
    if _producer is None:
        _producer = KafkaProducer()
    return _producer
