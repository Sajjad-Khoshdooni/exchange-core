from django.conf import settings

from financial.models import BankCard, Gateway

if settings.TESTING:
    from accounts.models import User

    def new_user(name='test_user', phone='09121111111', level=User.LEVEL2) -> User:
        name = name,
        phone = phone
        user = User.objects.create(username=name, phone=phone, level=level)
        return user

    def new_bank_card(user: User) -> BankCard:
        bank_card = BankCard.objects.create(user=user, card_pan='6104337574599260', verified=True)
        return bank_card

    def new_gate_way() ->Gateway:
        name ='test_gateway'
        type = Gateway.PAYDOTIR
        gateway = Gateway.objects.create(name=name, type=type, merchant_id='test', active=True)
        return gateway
