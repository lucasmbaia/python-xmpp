package main

import (
	"context"
	"encoding/json"
	"github.com/Shopify/sarama"
	"github.com/olivere/elastic"
	"log"
	"os"
	"os/signal"
)

type Metrics struct {
	ContainerID   string `json:",omitempty"`
	ContainerName string `json:",omitempty"`
	CpuUsage      string `json:",omitempty"`
	MemoryUsage   string `json:",omitempty"`
	MemoryTotal   string `json:",omitempty"`
}

func main() {
	var (
		consumer          sarama.Consumer
		err               error
		partitionConsumer sarama.PartitionConsumer
		signals           = make(chan os.Signal, 1)
		ctx               = context.Background()
		client            *elastic.Client
		exists            bool
		metrics           []Metrics
	)

	if client, err = elastic.NewClient(
		elastic.SetURL("http://192.168.204.135:9200")); err != nil {
		log.Fatal(err)
	}

	if consumer, err = sarama.NewConsumer([]string{"192.168.204.134:9092"}, nil); err != nil {
		log.Fatal(err)
	}

	defer func() {
		if err = consumer.Close(); err != nil {
			log.Fatal(err)
		}
	}()

	if partitionConsumer, err = consumer.ConsumePartition("monitoring", 0, sarama.OffsetNewest); err != nil {
		log.Fatal(err)
	}

	defer func() {
		if err = partitionConsumer.Close(); err != nil {
			log.Fatal(err)
		}
	}()

	signal.Notify(signals, os.Interrupt)

ConsumerLoop:
	for {
		select {
		case msg := <-partitionConsumer.Messages():
			log.Println(string(msg.Value))

			if err = json.Unmarshal(msg.Value, &metrics); err != nil {
				log.Println(err)
				continue
			}

			for _, metric := range metrics {
				if exists, err = client.IndexExists(metric.ContainerName).Do(ctx); err != nil {
					log.Println(err)
					continue
				}

				if !exists {
					log.Println("Nao existe Index")
					if _, err = client.CreateIndex(metric.ContainerName).Do(ctx); err != nil {
						log.Println(err)
						continue
					}
				}

				if _, err = client.Index().Index(metric.ContainerName).Type("monitoring").BodyJson(metric).Do(ctx); err != nil {
					log.Println(err)
					continue
				}

				log.Println(metric.ContainerName)
			}
		case <-signals:
			break ConsumerLoop
		}
	}
}
