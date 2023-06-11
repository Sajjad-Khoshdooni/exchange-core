import json
import logging

from confluent_kafka import Producer, KafkaException
from django.conf import settings

from analytics.models import EventTracker
from analytics.utils.dto import BaseEvent


logger = logging.getLogger(__name__)


def delivery_report(err, msg):
    if err is not None:
        logger.info('Message delivery failed: {}'.format(err))
        raise Exception('Kafka Message delivery failed')
    else:
        pass


class KafkaProducer:
    def __init__(self):
        try:
            self.producer = Producer({
                'bootstrap.servers': settings.KAFKA_HOST_URL,
                'socket.timeout.ms': 5000,  # timeout to 5 seconds',
                'delivery.timeout.ms': 5000,
                'message.send.max.retries': 5,
                'request.timeout.ms': 5000
            })
        except KafkaException as e:
            logger.warning('KafkaException', extra={
                'e': e
            })
        except Exception as e:
            logger.warning('KafkaClientException', extra={
                'e': e
            })

    def produce(self, event: BaseEvent, instance=None):
        data = json.dumps(event.serialize())

        if not settings.KAFKA_HOST_URL:
            return

        try:
            self.producer.poll(0)
            self.producer.produce('crm', data.encode('utf-8'), callback=delivery_report)

            handle_event_tracker(data=event.serialize(), instance=instance)

            self.producer.flush()
        except KafkaException as e:
            logger.info(event)
            logger.warning('KafkaException', extra={
                'e': e,
                'event': event
            })
        except Exception as e:
            logger.info(event)
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


def handle_event_tracker(data, instance):
    if instance is None:
        return

    _type = data.get('type')

    if _type == 'user':
        return
    elif _type == 'transfer':
        if data.get('coin') == 'IRT' and data.get('network') == 'IRT':
            if data.get('is_deposit'):
                tracker, _ = EventTracker.objects.get_or_create(type=EventTracker.PAYMENT)
            else:
                tracker, _ = EventTracker.objects.get_or_create(type=EventTracker.FIAT_WITHDRAW)
        else:
            tracker, _ = EventTracker.objects.get_or_create(type=EventTracker.TRANSFER)
    elif _type == 'trade':
        if data.get('trade_type') == 'otc':
            tracker, _ = EventTracker.objects.get_or_create(type=EventTracker.OTC_TRADE)
        else:
            tracker, _ = EventTracker.objects.get_or_create(type=EventTracker.TRADE)

    elif _type == 'login':
        tracker, _ = EventTracker.objects.get_or_create(type=EventTracker.LOGIN)

    elif _type == 'traffic_source':
        tracker, _ = EventTracker.objects.get_or_create(type=EventTracker.TRAFFIC_SOURCE)

    elif _type == 'staking':
        tracker, _ = EventTracker.objects.get_or_create(type=EventTracker.STAKING)
    elif _type == 'prize':
        tracker, _ = EventTracker.objects.get_or_create(type=EventTracker.PRIZE)
    else:
        raise NotImplementedError

    tracker.last_id = instance.id
    tracker.save(update_fields=['last_id'])
