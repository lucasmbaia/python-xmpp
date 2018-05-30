from kafka import KafkaConsumer
import avro.schema
import avro.io
import io

# To consume messages
consumer = KafkaConsumer('monitoring',
                         group_id='my_group',
                         bootstrap_servers=['toti-2:9092'])

schema_path = "user.avsc"
schema = avro.schema.parse(open(schema_path).read())

for msg in consumer:
    bytes_reader = io.BytesIO(msg.value)
        decoder = avro.io.BinaryDecoder(bytes_reader)
            reader = avro.io.DatumReader(schema)
                user1 = reader.read(decoder)
                #attr1 = user1.split("-")[0]
                #print "user1['hostname']: ", user1['hostname']
                #print "user1['check']: ", user1['check']
                #print "user1['metric']: ", user1['metric']
                    print user1
                    # .split("-")[0]   print user1[1]
