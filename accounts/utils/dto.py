from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Union, ClassVar
from uuid import UUID


@dataclass
class BaseEvent:
    v: ClassVar[str] = '1'
    created: datetime
    user_id: int
    event_id: UUID

    def serialize(self):
        pass


@dataclass
class UserEvent(BaseEvent):
    first_name: str
    last_name: str
    referrer_id: str
    type: ClassVar[str] = 'user'

    def serialize(self):
        return {
            'user_id': self.user_id,
            'created': self.created.isoformat(),
            'v': self.v,
            'event_id': self.event_id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'referrer_id': self.referrer_id,
            'type': self.type
        }


@dataclass
class TransferEvent(BaseEvent):
    id: int
    amount: Union[int, float, Decimal]
    coin: str
    network: str
    is_deposit: bool
    type: ClassVar[str] = 'transfer'
    value_irt: float
    value_usdt: float

    def serialize(self):
        return {
            'id': self.id,
            'created': self.created.isoformat(),
            'v': self.v,
            'event_id': self.event_id,
            'user_id': self.user_id,
            'amount': self.amount,
            'coin': self.coin,
            'network': self.network,
            'type': self.type,
            'is_deposit': self.is_deposit,
            'value_irt': self.value_irt,
            'value_usdt': self.value_usdt,
        }


@dataclass
class TradeEvent(BaseEvent):
    id: int
    amount: Union[int, float, Decimal]
    symbol: str
    price: Union[int, float, Decimal]
    trade_type: str
    market: str
    value_irt: Union[int, float, Decimal]
    value_usdt: Union[int, float, Decimal]
    type: ClassVar[str] = 'trade'

    def serialize(self):
        return {
            'id': self.id,
            'created': self.created.isoformat(),
            'v': self.v,
            'event_id': self.event_id,
            'user_id': self.user_id,
            'amount': self.amount,
            'symbol': self.symbol,
            'price': self.price,
            'type': self.type,
            'trade_type': self.trade_type,
            'market': self.market,
            'value_irt': self.value_irt,
            'value_usdt': self.value_usdt,
        }


@dataclass
class LoginEvent(BaseEvent):
    device: str
    type: ClassVar[str] = 'login'
    is_signup: bool

    def serialize(self):
        return {
            'user_id': self.user_id,
            'created': self.created.isoformat(),
            'v': self.v,
            'event_id': self.event_id,
            'device': self.device,
            'type': self.type,
            'is_signup': self.is_signup
        }
