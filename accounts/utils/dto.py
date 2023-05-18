from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Union, ClassVar


@dataclass
class BaseEvent:
    def serialize(self):
        pass


@dataclass
class SignupEvent(BaseEvent):
    user_id: int
    first_name: str
    last_name: str
    phone: str
    email: str
    referrer_id: str
    device: str
    topic: ClassVar[str] = 'signup'
    v: ClassVar[str] = '1'
    created: datetime = field(default_factory=datetime.utcnow)

    def serialize(self):
        return {
            'user_id': self.user_id,
            'created': self.created,
            'v': self.v,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'phone': self.phone,
            'email': self.email,
            'referrer_id': self.referrer_id,
            'device': self.device
        }


@dataclass
class DepositEvent(BaseEvent):
    id: int
    user_id: int
    amount: Union[int, float, Decimal]
    coin: str
    topic: ClassVar[str] = 'deposit'
    v: ClassVar[str] = '1'
    created: datetime = field(default_factory=datetime.utcnow)

    def serialize(self):
        return {
            'id': self.id,
            'created': self.created,
            'v': self.v,
            'user_id': self.user_id,
            'amount': self.amount,
            'coin': self.coin
        }


@dataclass
class WithdrawEvent(BaseEvent):
    id: int
    user_id: int
    amount: Union[int, float, Decimal]
    coin: str
    topic: ClassVar[str] = 'withdraw'
    v: ClassVar[str] = '1'
    created: datetime = field(default_factory=datetime.utcnow)

    def serialize(self):
        return {
            'id': self.id,
            'created': self.created,
            'v': self.v,
            'user_id': self.user_id,
            'amount': self.amount,
            'coin': self.coin
        }


@dataclass
class TradeEvent(BaseEvent):
    id: int
    user_id: int
    amount: Union[int, float, Decimal]
    symbol: str
    price: Union[int, float, Decimal]
    type: str
    market: str
    irt_value: Union[int, float, Decimal]
    usdt_value: Union[int, float, Decimal]
    topic: ClassVar[str] = 'trade'
    v: ClassVar[str] = '1'
    created: datetime = field(default_factory=datetime.utcnow)

    def serialize(self):
        return {
            'id': self.id,
            'created': self.created,
            'v': self.v,
            'user_id': self.user_id,
            'amount': self.amount,
            'symbol': self.symbol,
            'price': self.price,
            'type': self.type,
            'market': self.market,
            'irt_value': self.irt_value,
            'usdt_value': self.usdt_value
        }


@dataclass
class ChangeUserEvent(BaseEvent):
    user_id: int
    first_name: str
    last_name: str
    phone: str
    email: str
    topic: ClassVar[str] = 'change_user'
    v: ClassVar[str] = '1'
    created: datetime = field(default_factory=datetime.utcnow)

    def serialize(self):
        return {
            'user_id': self.user_id,
            'created': self.created,
            'v': self.v,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'phone': self.phone,
            'email': self.email
        }


@dataclass
class LoginEvent(BaseEvent):
    user_id: int
    device: str
    topic: ClassVar[str] = 'login'
    v: ClassVar[str] = '1'
    created: datetime = field(default_factory=datetime.utcnow)

    def serialize(self):
        return {
            'user_id': self.user_id,
            'created': self.created,
            'v': self.v,
            'device': self.device
        }
