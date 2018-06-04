package main

import (
  "bytes"
  "strings"
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
{{printf "listen %s-%s_balance" .Application .PortBind}}
{{printf "\tbind 192.168.0.1:%s" .PortBind}}
{{printf "\tuse_backend %s-%s" .Application .PortBind}}
{{printf "Application %s-%s" .Application .PortBind}}
{{printf "\tbalance roundrobin"}}
{{range $index, $ip := .Addresses -}}
{{printf "\tserver application-%d %s check" $index $ip}}
{{end -}}
{{end}}`

type Client struct {
  client client.KeysAPI
}

type Infos map[string][]InfosLB

type InfosLB struct {
  Address string    `json:"address,omitempty"`
  Ports	  []string  `json:"ports,omitempty"`
}

type Conf struct {
  Application string
  Addresses   []string
  PortBind    string
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
    hosts  = []string{"http://172.16.95.183:2379"}
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
      var address []string
      var addr string
      var ports []string

      if file, err = os.Create("haproxy.cfg"); err != nil {
	log.Println(err)
	continue
      }

      if err = json.Unmarshal([]byte(value), &infos); err != nil {
	log.Println(err)
	continue
      }

      for key, info := range infos {
	ports = []string{}

	for _, port := range info[0].Ports {
	  ports = append(ports, strings.Split(port, ":")[0])
	}

	for _, p := range ports {
	  for _, lb := range info {
	    for _, port := range lb.Ports {
	      if strings.Split(port, ":")[0] == p {
		addr = strings.TrimSpace(lb.Address)
		address = append(address, fmt.Sprintf("%s:%s", strings.Replace(addr, "\"", "", -1), strings.Split(port, ":")[1]))
	      }
	    }
	  }

	  conf = append(conf, Conf{Application: key, Addresses: address, PortBind: p})
	  address = []string{}
	}
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
    if err = cli.Watch("/haproxy", values); err != nil {
      log.Fatal(err)
    }
  }()

  <-done
}
