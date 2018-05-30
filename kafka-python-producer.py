from kafka import SimpleProducer, KafkaClient
import avro.schema
import io
import random
from avro.io import DatumWriter

# To send messages synchronously
kafka = KafkaClient('toti-2:9092')
producer = SimpleProducer(kafka)

# Kafka topic
topic = "monitoring"

# Path to user.avsc avro schema
schema_path = "user.avsc"
schema = avro.schema.parse(open(schema_path).read())


for i in xrange(10):
    writer = avro.io.DatumWriter(schema)
        bytes_writer = io.BytesIO()
            encoder = avro.io.BinaryEncoder(bytes_writer)
                writer.write({"hostname": "totino-1", "check": "memory",
                              "metric": random.randint(0, 10)}, encoder)
                    raw_bytes = bytes_writer.getvalue()
                    producer.send_messages(topic, raw_bytes)
