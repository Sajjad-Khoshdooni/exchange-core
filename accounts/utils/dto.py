from dataclasses import dataclass
from decimal import Decimal
from typing import Union


@dataclass
class BaseEvent:
    topic: str

    def serialize(self):
        pass


@dataclass
class SignupEvent(BaseEvent):
    topic = 'signup'
    user_id: int
    first_name: str
    last_name: str
    phone: str
    email: str
    referrer_id: str
    device: str

    def serialize(self):
        return {
            'user_id': self.user_id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'phone': self.phone,
            'email': self.email,
            'referrer_id': self.referrer_id,
            'device': self.device
        }


@dataclass
class DepositEvent(BaseEvent):
    topic = 'deposit'
    id: int
    user_id: int
    amount: Union[int, float, Decimal]
    coin: str

    def serialize(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'amount': self.amount,
            'coin': self.coin
        }


@dataclass
class WithdrawEvent(BaseEvent):
    topic = 'withdraw'
    id: int
    user_id: int
    amount: Union[int, float, Decimal]
    coin: str

    def serialize(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'amount': self.amount,
            'coin': self.coin
        }


@dataclass
class TradeEvent(BaseEvent):
    topic = 'trade'
    id: int
    user_id: int
    amount: Union[int, float, Decimal]
    symbol: str
    price: Union[int, float, Decimal]
    type: str
    market: str
    irt_value: Union[int, float, Decimal]
    usdt_value: Union[int, float, Decimal]

    def serialize(self):
        return {
            'id': self.id,
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
    topic = 'change_user'
    user_id: int
    first_name: str
    last_name: str
    phone: str
    email: str

    def serialize(self):
        return {
            'user_id': self.user_id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'phone': self.phone,
            'email': self.email
        }


@dataclass
class LoginEvent(BaseEvent):
    topic = 'login'
    user_id: int
    device: str

    def serialize(self):
        return {
            'user_id': self.user_id,
            'device': self.device
        }
