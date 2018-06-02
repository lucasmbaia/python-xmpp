package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"github.com/coreos/etcd/client"
	"log"
	"os"
	"sync"
	"text/template"
	"time"
)

const ha = `
global
{{printf "\tlog \t\t127.0.0.1 local2"}}
{{printf "\tchroot \t\t/var/lib/haproxy"}}
{{printf "\tpidfile \t/var/run/haproxy.pid"}}
{{printf "\tmaxconn \t4000"}}
{{printf "\tuser \t\thtaproxy"}}
{{printf "\tgroup \t\thaproxy"}}
{{printf "\tdaemon"}}
{{printf "\tstats socket /var/lib/haproxy/stats"}}
{{printf "\n"}}
defaults
{{printf "\tmode \t\t\t\thttp"}}
{{printf "\tlog \t\t\t\tglobal"}}
{{printf "\toption \t\t\t\thttplog"}}
{{printf "\toption \t\t\t\tdontlognull"}}
{{printf "\toption http-server-close"}}
{{printf "\toption forwardfor \t\texcept 127.0.0.0/8"}}
{{printf "\toption \tredispatch"}}
{{printf "\tretries \t\t\t3"}}
{{printf "\ttimeout http-request \t\t10s"}}
{{printf "\ttimeout queue \t\t\t1m"}}
{{printf "\ttimeout connect \t\t10s"}}
{{printf "\ttimeout client \t\t\t1m"}}
{{printf "\ttimeout server \t\t\t1m"}}
{{printf "\ttimeout http-keep-alive \t10s"}}
{{printf "\ttimeout check \t\t\t10s"}}
{{printf "\tmaxconn \t\t\t3000"}}
{{range .}}
{{$portDst := .PortDst}}
listen {{.Application}}
{{printf "\tbind 192.168.0.1:%s" .PortSrc}}
{{printf "\tdefault_backend %s" .Application}}
Application {{.Application}}
{{printf "\tbalance roundrobin"}}
{{range $index, $ip := .Addresses -}}
	{{printf "\tserver application-%d %s:%s check" $index $ip $portDst}}
{{- end}}
{{end}}`

type Client struct {
	client client.KeysAPI
}

type Infos map[string]InfosLB

type InfosLB struct {
	Addresses []string `json:"ips,omitempty"`
	PortSrc   string   `json:"portSRC,omitempty"`
	PortDst   string   `json:"portDST,omitempty"`
}

type Conf struct {
	Application string
	Addresses   []string
	PortSrc     string
	PortDst     string
}

func New(hosts []string, timeout int) (*Client, error) {
	var (
		cli  client.Client
		err  error
		resp = &Client{}
	)

	if cli, err = client.New(client.Config{
		Endpoints:               hosts,
		Transport:               client.DefaultTransport,
		HeaderTimeoutPerRequest: time.Duration(timeout) * time.Second,
	}); err != nil {
		return resp, err
	}

	resp.client = client.NewKeysAPI(cli)

	return resp, nil
}

func (c *Client) Watch(key string, values chan<- string) error {
	var (
		watch    client.Watcher
		err      error
		response *client.Response
	)

	for {
		watch = c.client.Watcher(key, &client.WatcherOptions{Recursive: true})

		if response, err = watch.Next(context.Background()); err != nil {
			return err
		}

		values <- response.Node.Value
	}
}

func main() {
	var (
		done   = make(chan bool, 1)
		cli    *Client
		values = make(chan string)
		err    error
		hosts  = []string{"http://192.168.204.128:2379"}
		infos  Infos
		mutex  = &sync.Mutex{}
		t      *template.Template
		file   *os.File
	)

	if cli, err = New(hosts, 5); err != nil {
		log.Fatal(err)
	}

	go func() {
		for {
			value := <-values

			mutex.Lock()
			var conf []Conf
			var buf bytes.Buffer

			if file, err = os.Create("haproxy.cfg"); err != nil {
				log.Println(err)
				continue
			}

			if err = json.Unmarshal([]byte(value), &infos); err != nil {
				log.Println(err)
				continue
			}

			for key, info := range infos {
				conf = append(conf, Conf{Application: key, Addresses: info.Addresses, PortSrc: info.PortSrc, PortDst: info.PortDst})
			}

			fmt.Println(conf)
			t = template.Must(template.New("HA").Parse(ha))

			if err = t.Execute(&buf, conf); err != nil {
				log.Println(err)
				continue
			}

			if _, err = file.Write(buf.Bytes()); err != nil {
				log.Println(err)
				continue
			}

			if err = file.Close(); err != nil {
				log.Println(err)
				continue
			}

			fmt.Println(buf.String())
			mutex.Unlock()
		}
	}()

	go func() {
		if err = cli.Watch("/python/app", values); err != nil {
			log.Fatal(err)
		}
	}()

	<-done
}
