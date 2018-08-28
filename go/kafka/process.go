package main

import (
  "os/exec"
  //"syscall"
  "fmt"
  "os"
  //"bytes"
  "encoding/json"
  "errors"
  "github.com/Shopify/sarama"
  "log"
  "strings"
  "time"
)

type Metrics struct {
  Hostname  string	`json:",omitempty"`
  Customers []Customers	`json:",omitempty"`
}

type Customers struct {
  Name		string		`json:",omitempty"`
  Applications	[]Applications	`json:",omitempty"`
}

type Applications struct {
  Name	      string	    `json:",omitempty"`
  Containers  []Containers  `json:",omitempty"`
}

type Containers struct {
  ContainerID   string `json:",omitempty"`
  ContainerName string `json:",omitempty"`
  CpuUsage      string `json:",omitempty"`
  MemoryUsage   string `json:",omitempty"`
  MemoryTotal   string `json:",omitempty"`
}

var r *strings.Replacer = strings.NewReplacer("KiB", "", "MiB", "", "GiB", "")

func dockerStats() (Metrics, error) {
  var (
    output  []byte
    err     error
    metrics Metrics
    m       []string
    info    []string
  )

  if output, err = exec.Command("docker", "stats", "--all", "--no-stream", "--format", "'{{.Container}}#{{ .Name }}#{{.CPUPerc}}#{{.MemUsage}}'").CombinedOutput(); err != nil {
    return metrics, errors.New(fmt.Sprintf("Code Error: %s, Error Message: %s", err.Error(), string(output)))
  }

  m = strings.Split(strings.Replace(string(output), "'", "", -1), "\n")

  for _, infos := range m {
    if len(infos) > 0 {
      info = strings.Split(infos, "#")

      var containsCustomer = false
      var memory = strings.Split(info[3], "/")
      var cn = strings.Split(strings.TrimSpace(info[1]), "_app-")
      var as = strings.Split(cn[1], "-")
      var app = strings.Join(as[:len(as) -1], "-")

      for i, customer := range metrics.Customers {
	if customer.Name == cn[0] {
	  var containsApplication = false

	  for j, application := range metrics.Customers[i].Applications {
	    if application.Name == app {
	      metrics.Customers[i].Applications[j].Containers = append(metrics.Customers[i].Applications[j].Containers, Containers{
		ContainerID:    strings.TrimSpace(info[0]),
		ContainerName:  strings.TrimSpace(info[1]),
		CpuUsage:       strings.TrimSpace(strings.Replace(info[2], "%", "", 1)),
		MemoryUsage:    strings.TrimSpace(memory[0]),
		MemoryTotal:    strings.TrimSpace(memory[1]),
	      })

	      containsApplication = true
	      break
	    }
	  }

	  if !containsApplication {
	    metrics.Customers[i].Applications = append(metrics.Customers[i].Applications, Applications{
	      Name: app,
	      Containers: []Containers{{
		ContainerID:    strings.TrimSpace(info[0]),
		ContainerName:  strings.TrimSpace(info[1]),
		CpuUsage:       strings.TrimSpace(strings.Replace(info[2], "%", "", 1)),
		MemoryUsage:    strings.TrimSpace(memory[0]),
		MemoryTotal:    strings.TrimSpace(memory[1]),
	      }},
	    })
	  }

	  containsCustomer = true
	  break
	}
      }

      if !containsCustomer {
	metrics.Customers = append(metrics.Customers, Customers{
	  Name:	cn[0],
	  Applications:	[]Applications{{
	    Name: app,
	    Containers:	[]Containers{{
	      ContainerID:    strings.TrimSpace(info[0]),
	      ContainerName:  strings.TrimSpace(info[1]),
	      CpuUsage:	      strings.TrimSpace(strings.Replace(info[2], "%", "", 1)),
	      MemoryUsage:    strings.TrimSpace(memory[0]),
	      MemoryTotal:    strings.TrimSpace(memory[1]),
	    }},
	  }},
	})
      }
    }
  }

  return metrics, nil
}

func main() {
  var (
    ticker    *time.Ticker
    metrics   Metrics
    body      []byte
    err	      error
    config    *sarama.Config
    producer  sarama.SyncProducer
    msg	      *sarama.ProducerMessage
    hostname  string
  )

  config = sarama.NewConfig()
  config.Producer.Retry.Max = 5

  if hostname, err = os.Hostname(); err != nil {
    log.Fatal(err)
  }

  if producer, err = sarama.NewSyncProducer([]string{"172.16.95.183:9092"}, nil); err != nil {
    log.Fatal(err)
  }

  defer func() {
    if err = producer.Close(); err != nil {
      log.Fatal(err)
    }
  }()

  ticker = time.NewTicker(2 * time.Second)
  defer ticker.Stop()

  for {
    select {
    case _ = <-ticker.C:
      if metrics, err = dockerStats(); err != nil {
	fmt.Println(err)
	continue
      }

      metrics.Hostname = hostname
      if body, err = json.Marshal(metrics); err != nil {
	fmt.Println(err)
	continue
      }

      fmt.Println(string(body))

      msg = &sarama.ProducerMessage{
	Topic: "monitoring",
	Key:   sarama.ByteEncoder([]byte("meu_ovo")),
	Value: sarama.ByteEncoder(body),
      }

      if _, _, err = producer.SendMessage(msg); err != nil {
	fmt.Println(err)
      }
    }
  }

  /*var stdout bytes.Buffer
  cmd := exec.Command("docker", "stats", "--all", "--no-stream", "--no-trunc", "--format", "'{{.Container}}#{{ .Name }}#{{.CPUPerc}}#{{.MemUsage}}#{{ .NetIO }}'")
  cmd.Stdout = &stdout
  var waitStatus syscall.WaitStatus

  if err := cmd.Run(); err != nil {
    if err != nil {
      os.Stderr.WriteString(fmt.Sprintf("Error: %s\n", err.Error()))
    }

    if exitError, ok := err.(*exec.ExitError); ok {
      waitStatus = exitError.Sys().(syscall.WaitStatus)
      fmt.Printf("Output: %s\n", []byte(fmt.Sprintf("%d", waitStatus.ExitStatus())))
    }
  } else {
    fmt.Println(string(stdout.Bytes()))
    waitStatus = cmd.ProcessState.Sys().(syscall.WaitStatus)
    fmt.Printf("Output: %s\n", []byte(fmt.Sprintf("%d", waitStatus.ExitStatus())))
  }*/
}
