# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
"""Client and server classes corresponding to protobuf-defined services."""
import grpc

from collector import trade_pb2 as trade__pb2


class TradeStub(object):
    """Missing associated documentation comment in .proto file."""

    def __init__(self, channel):
        """Constructor.

        Args:
            channel: A grpc.Channel.
        """
        self.GetCurrentTrades = channel.unary_unary(
                '/trade.Trade/GetCurrentTrades',
                request_serializer=trade__pb2.TradeParams.SerializeToString,
                response_deserializer=trade__pb2.TradeList.FromString,
                )
        self.GetTradesAvgPrice = channel.unary_unary(
                '/trade.Trade/GetTradesAvgPrice',
                request_serializer=trade__pb2.TradeParams.SerializeToString,
                response_deserializer=trade__pb2.AggregatedValue.FromString,
                )
        self.GetTradesAvgPriceByTime = channel.unary_unary(
                '/trade.Trade/GetTradesAvgPriceByTime',
                request_serializer=trade__pb2.TradeTimeParams.SerializeToString,
                response_deserializer=trade__pb2.AggregatedValue.FromString,
                )
        self.GetTradesSumQuantity = channel.unary_unary(
                '/trade.Trade/GetTradesSumQuantity',
                request_serializer=trade__pb2.TradeParams.SerializeToString,
                response_deserializer=trade__pb2.AggregatedValue.FromString,
                )


class TradeServicer(object):
    """Missing associated documentation comment in .proto file."""

    def GetCurrentTrades(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def GetTradesAvgPrice(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def GetTradesAvgPriceByTime(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def GetTradesSumQuantity(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')


def add_TradeServicer_to_server(servicer, server):
    rpc_method_handlers = {
            'GetCurrentTrades': grpc.unary_unary_rpc_method_handler(
                    servicer.GetCurrentTrades,
                    request_deserializer=trade__pb2.TradeParams.FromString,
                    response_serializer=trade__pb2.TradeList.SerializeToString,
            ),
            'GetTradesAvgPrice': grpc.unary_unary_rpc_method_handler(
                    servicer.GetTradesAvgPrice,
                    request_deserializer=trade__pb2.TradeParams.FromString,
                    response_serializer=trade__pb2.AggregatedValue.SerializeToString,
            ),
            'GetTradesAvgPriceByTime': grpc.unary_unary_rpc_method_handler(
                    servicer.GetTradesAvgPriceByTime,
                    request_deserializer=trade__pb2.TradeTimeParams.FromString,
                    response_serializer=trade__pb2.AggregatedValue.SerializeToString,
            ),
            'GetTradesSumQuantity': grpc.unary_unary_rpc_method_handler(
                    servicer.GetTradesSumQuantity,
                    request_deserializer=trade__pb2.TradeParams.FromString,
                    response_serializer=trade__pb2.AggregatedValue.SerializeToString,
            ),
    }
    generic_handler = grpc.method_handlers_generic_handler(
            'trade.Trade', rpc_method_handlers)
    server.add_generic_rpc_handlers((generic_handler,))


 # This class is part of an EXPERIMENTAL API.
class Trade(object):
    """Missing associated documentation comment in .proto file."""

    @staticmethod
    def GetCurrentTrades(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/trade.Trade/GetCurrentTrades',
            trade__pb2.TradeParams.SerializeToString,
            trade__pb2.TradeList.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def GetTradesAvgPrice(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/trade.Trade/GetTradesAvgPrice',
            trade__pb2.TradeParams.SerializeToString,
            trade__pb2.AggregatedValue.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def GetTradesAvgPriceByTime(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/trade.Trade/GetTradesAvgPriceByTime',
            trade__pb2.TradeTimeParams.SerializeToString,
            trade__pb2.AggregatedValue.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def GetTradesSumQuantity(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/trade.Trade/GetTradesSumQuantity',
            trade__pb2.TradeParams.SerializeToString,
            trade__pb2.AggregatedValue.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)
