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
public class ITCoreExampleBuyTakerUserFee {

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

        // currency code constants
        final int currencyCodeXbt = 11;
        final int currencyCodeLtc = 15;

        // symbol constants
        final int symbolXbtLtc = 241;

        Future<CommandResultCode> future;

        // create symbol specification and publish it
        CoreSymbolSpecification symbolSpecXbtLtc = CoreSymbolSpecification.builder()
                .symbolId(symbolXbtLtc)         // symbol id
                .type(SymbolType.CURRENCY_EXCHANGE_PAIR)
                .baseCurrency(currencyCodeXbt)    // base = satoshi (1E-8)
                .quoteCurrency(currencyCodeLtc)   // quote = litoshi (1E-8)
                .baseScaleK(1_000_000L) // 1 lot = 1M satoshi (0.01 BTC)
                .quoteScaleK(10_000L)   // 1 price step = 10K litoshi
                .takerFee(2000L)        // taker fee 1900 litoshi per 1 lot
                .makerFee(1000L)         // maker fee 700 litoshi per 1 lot
                .build();

        future = api.submitBinaryDataAsync(new BatchAddSymbolsCommand(symbolSpecXbtLtc));
        System.out.println("BatchAddSymbolsCommand result: " + future.get());


        // create user uid=301
        future = api.submitCommandAsync(ApiAddUser.builder()
                .uid(301L)
                .takerFee(4000L)
                .makerFee(2000L)
                .build());

        System.out.println("ApiAddUser 1 result: " + future.get());


        // create user uid=302
        future = api.submitCommandAsync(ApiAddUser.builder()
                .uid(302L)
                .takerFee(4000L)
                .makerFee(2000L)
                .build());

        System.out.println("ApiAddUser 2 result: " + future.get());

        // first user deposits 20 LTC
        future = api.submitCommandAsync(ApiAdjustUserBalance.builder()
                .uid(302L)
                .currency(currencyCodeLtc)
                .amount(2_000_000_000L)
                .transactionId(1L)
                .build());

        System.out.println("ApiAdjustUserBalance 2 result: " + future.get());


        // second user deposits 0.10 BTC
        future = api.submitCommandAsync(ApiAdjustUserBalance.builder()
                .uid(301L)
                .currency(currencyCodeXbt)
                .amount(10_000_000L)
                .transactionId(2L)
                .build());

        System.out.println("ApiAdjustUserBalance 1 result: " + future.get());


        Future<SingleUserReportResult> report1 = api.processReport(new SingleUserReportQuery(301), 0);
        System.out.println("SingleUserReportQuery 1 accounts: " + report1.get().getAccounts());

        Future<SingleUserReportResult> report2 = api.processReport(new SingleUserReportQuery(302), 0);
        System.out.println("SingleUserReportQuery 2 accounts: " + report2.get().getAccounts());



        // first user places Good-till-Cancel Bid order
        // he assumes BTCLTC exchange rate 154 LTC for 1 BTC
        // bid price for 1 lot (0.01BTC) is 1.54 LTC => 1_5400_0000 litoshi => 10K * 15_400 (in price steps)
        future = api.submitCommandAsync(ApiPlaceOrder.builder()
                .uid(301L)
                .orderId(5001L)
                .price(15_400L)
                .reservePrice(15_400L) // can move bid order up to the 1.56 LTC, without replacing it
                .size(10L) // order size is 12 lots
                .action(OrderAction.ASK)
                .orderType(OrderType.GTC) // Good-till-Cancel
                .symbol(symbolXbtLtc)
                .build());

        System.out.println("ApiPlaceOrder 1 result: " + future.get());


        // second user places Immediate-or-Cancel Ask (Sell) order
        // he assumes wost rate to sell 152.5 LTC for 1 BTC
        future = api.submitCommandAsync(ApiPlaceOrder.builder()
                .uid(302L)
                .orderId(5002L)
                .price(15_400L)
                .reservePrice(15_400L) // can move bid order up to the 1.56 LTC, without replacing it
                .size(10L) // order size is 10 lots
                .action(OrderAction.BID)
                .orderType(OrderType.GTC) // Immediate-or-Cancel
                .symbol(symbolXbtLtc)
                .build());

        System.out.println("ApiPlaceOrder 2 result: " + future.get());

        // check balances
        report1 = api.processReport(new SingleUserReportQuery(301), 0);
        System.out.println("SingleUserReportQuery 1 accounts: " + report1.get().getAccounts());

        report2 = api.processReport(new SingleUserReportQuery(302), 0);
        System.out.println("SingleUserReportQuery 2 accounts: " + report2.get().getAccounts());

        // check fees collected
        Future<TotalCurrencyBalanceReportResult> totalsReport = api.processReport(new TotalCurrencyBalanceReportQuery(), 0);
        System.out.println("LTC fees collected: " + totalsReport.get().getFees().get(currencyCodeLtc));
        System.out.println("BTC fees collected: " + totalsReport.get().getFees().get(currencyCodeXbt));

    }
}
