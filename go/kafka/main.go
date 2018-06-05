package main

import (
  "github.com/Shopify/sarama"
  "log"
  "fmt"
)

func main() {
  producer, err := sarama.NewSyncProducer([]string{"172.16.95.111:9092"}, nil)

  if err != nil {
    log.Fatal(err)
  }

  defer func() {
    if err := producer.Close(); err != nil {
      log.Fatal(err)
    }
  }()

  msg := `{"hostname":"lucas-dev","check":"memory","metric":1}`
  message := &sarama.ProducerMessage{Topic: "monitoring", Value: sarama.StringEncoder(msg)}
  partition, offset, err := producer.SendMessage(message)

  if err != nil {
    log.Fatal(err)
  }

  fmt.Println(partition, offset)
  fmt.Println("vim-go")
}
