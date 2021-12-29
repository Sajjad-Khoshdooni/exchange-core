import grpc
from django.conf import settings
from yekta_config import secret

import order_pb2
import order_pb2_grpc
import trade_pb2
import trade_pb2_grpc

if not settings.DEBUG:
    with open('server.crt', 'rb') as f:
        trusted_certs = f.read()


class gRPCClient(object):
    """
    Client for gRPC functionality
    """

    def __init__(self):
        self.host = secret('collector-server-ip', default='localhost')
        self.server_port = 50051

        # instantiate a channel
        if settings.DEBUG:
            self.channel = grpc.insecure_channel(
                '{}:{}'.format(self.host, self.server_port))
        else:
            credentials = grpc.ssl_channel_credentials(root_certificates=trusted_certs)
            self.channel = grpc.secure_channel('{}:{}'.format(self.host, self.server_port), credentials)

        # bind the client and the server
        self.order_stub = order_pb2_grpc.OrderStub(self.channel)
        self.trade_stub = trade_pb2_grpc.TradeStub(self.channel)

    def get_current_orders(self, **kwargs):
        params = order_pb2.OrderParams(**kwargs)
        return self.order_stub.GetCurrentOrders(params)

    def get_current_trades(self, **kwargs):
        params = trade_pb2.TradeParams(**kwargs)
        return self.trade_stub.GetCurrentTrades(params)

    def get_trades_average_price(self, **kwargs):
        params = trade_pb2.TradeParams(**kwargs)
        return self.trade_stub.GetTradesAvgPrice(params) or 0

    def get_trades_average_price_by_time(self, **kwargs):
        params = trade_pb2.TradeTimeParams(**kwargs)
        return self.trade_stub.GetTradesAvgPriceByTime(params) or 0

    def get_trades_sum_quantity(self, **kwargs):
        params = trade_pb2.TradeParams(**kwargs)
        return self.trade_stub.GetTradesSumQuantity(params) or 0
