package exchange.core2.tests.examples;

import exchange.core2.core.ExchangeApi;
import exchange.core2.core.ExchangeCore;
import exchange.core2.core.IEventsHandler;
import exchange.core2.core.SimpleEventsProcessor;
import exchange.core2.core.common.CoreSymbolSpecification;
import exchange.core2.core.common.OrderAction;
import exchange.core2.core.common.OrderType;
import exchange.core2.core.common.SymbolType;
import exchange.core2.core.common.api.ApiAddUser;
import exchange.core2.core.common.api.ApiAdjustUserBalance;
import exchange.core2.core.common.api.ApiPlaceOrder;
import exchange.core2.core.common.api.binary.BatchAddSymbolsCommand;
import exchange.core2.core.common.api.reports.SingleUserReportQuery;
import exchange.core2.core.common.api.reports.SingleUserReportResult;
import exchange.core2.core.common.api.reports.TotalCurrencyBalanceReportQuery;
import exchange.core2.core.common.api.reports.TotalCurrencyBalanceReportResult;
import exchange.core2.core.common.cmd.CommandResultCode;
import exchange.core2.core.common.config.ExchangeConfiguration;
import lombok.extern.slf4j.Slf4j;
import org.junit.jupiter.api.Test;

import java.util.concurrent.Future;

@Slf4j
public class ITCoreExampleAccountSpeceficFee {

    @Test
    public void sampleTest() throws Exception {

        // simple async events handler
        SimpleEventsProcessor eventsProcessor = new SimpleEventsProcessor(new IEventsHandler() {
            @Override
            public void tradeEvent(TradeEvent tradeEvent) {
                System.out.println("Trade event: " + tradeEvent);
            }

            @Override
            public void reduceEvent(ReduceEvent reduceEvent) {
                System.out.println("Reduce event: " + reduceEvent);
            }

            @Override
            public void rejectEvent(RejectEvent rejectEvent) {
                System.out.println("Reject event: " + rejectEvent);
            }

            @Override
            public void commandResult(ApiCommandResult commandResult) {
                System.out.println("Command result: " + commandResult);
            }

            @Override
            public void orderBook(OrderBook orderBook) {
                System.out.println("OrderBook event: " + orderBook);
            }
        });

        // default exchange configuration
        ExchangeConfiguration conf = ExchangeConfiguration.defaultBuilder().build();

        // build exchange core
        ExchangeCore exchangeCore = ExchangeCore.builder()
                .resultsConsumer(eventsProcessor)
                .exchangeConfiguration(conf)
                .build();

        // start up disruptor threads
        exchangeCore.startup();

        // get exchange API for publishing commands
        ExchangeApi api = exchangeCore.getApi();

        Future<CommandResultCode> future;

        // create user uid=301
        future = api.submitCommandAsync(ApiAddUser.builder()
                .uid(301L)
                .makerFee(7L)
                .takerFee(8L)
                .build());

        System.out.println("ApiAddUser 1 result: " + future.get());


        // create user uid=302
        future = api.submitCommandAsync(ApiAddUser.builder()
                .uid(302L)
                .makerFee(7L)
                .takerFee(8L)
                .build());

        System.out.println("ApiAddUser 2 result: " + future.get());

    }
}
