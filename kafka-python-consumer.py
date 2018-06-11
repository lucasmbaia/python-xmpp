from kafka import KafkaConsumer
#import avro.schema
#import avro.io
import io

# To consume messages
consumer = KafkaConsumer('monitoring',
                         group_id='my_group',
                         bootstrap_servers=['192.168.204.134:9092'])

#schema_path = "user.avsc"
#schema = avro.schema.parse(open(schema_path).read())

for msg in consumer:
	bytes_reader = io.BytesIO(msg.value)
	#decoder = avro.io.BinaryDecoder(bytes_reader)
	#reader = avro.io.DatumReader(schema)
	print(msg.value)
