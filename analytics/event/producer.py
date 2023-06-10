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
    else:
        data = json.loads(msg.value().decode('utf-8'))
        _type = data.get('type')
        event_id = data.get('id')

        tracker, _ = EventTracker.objects.get_or_create(name='kafka')

        if _type == 'user':
            # tracker.last_user_id = max(event_id, tracker.last_user_id)
            pass
        elif _type == 'transfer':
            if data.get('coin') == 'IRT' and data.get('network') == 'IRT':
                if data.get('is_deposit'):
                    tracker.last_payment_id = event_id
                else:
                    tracker.last_fiat_withdraw_id = event_id
            else:
                tracker.last_transfer_id = event_id
        elif _type == 'trade':
            if data.get('trade_type') == 'otc':
                tracker.last_otc_trade_id = event_id
            else:
                tracker.last_trade_id = event_id
        elif _type == 'login':
            tracker.last_login_id = event_id
        elif _type == 'traffic_source':
            tracker.last_traffic_source_id = event_id
        elif _type == 'staking':
            tracker.last_staking_id = event_id
        elif _type == 'prize':
            tracker.last_prize_id = event_id
        else:
            raise NotImplementedError
        tracker.save()


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

    def produce(self, event: BaseEvent):
        data = json.dumps(event.serialize())

        if not settings.KAFKA_HOST_URL:
            return

        try:
            self.producer.produce('crm', data.encode('utf-8'), callback=delivery_report)
            self.producer.poll(1)

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
