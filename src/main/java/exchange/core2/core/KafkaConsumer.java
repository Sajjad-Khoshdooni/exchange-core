package exchange.core2.core;

import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.apache.kafka.clients.consumer.ConsumerRecords;

import java.time.Duration;
import java.util.Arrays;
import java.util.Properties;


public class KafkaConsumer {

    public static void main(String[] args) {
        int timeInterval = 10;
        // 1. Configure the consumer
        Properties props = new Properties();
        props.put("bootstrap.servers", "localhost:9092"); // Kafka server address
        props.put("group.id", "test-group"); // Consumer group ID
        props.put("enable.auto.commit", "true"); // Enable auto commit
        props.put("auto.commit.interval.ms", String.valueOf(timeInterval)); // Auto commit interval
        props.put("key.deserializer", "org.apache.kafka.common.serialization.StringDeserializer");
        props.put("value.deserializer", "org.apache.kafka.common.serialization.StringDeserializer");

        // 2. Create the consumer
        org.apache.kafka.clients.consumer.KafkaConsumer<String, String> consumer = new org.apache.kafka.clients.consumer.KafkaConsumer<>(props);

        // 3. Subscribe to topics
        consumer.subscribe(Arrays.asList("test_topic"));

        // 4. Poll for new data
        try {
            while (true) {
                ConsumerRecords<String, String> records = consumer.poll(Duration.ofMillis(timeInterval));
                for (ConsumerRecord<String, String> record : records) {
                    System.out.printf("offset = %d, key = %s, value = %s%n", record.offset(), record.key(), record.value());
                }
            }
        } finally {
            consumer.close(); // Ensure the consumer is closed properly
        }
    }
}