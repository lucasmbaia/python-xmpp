package main

import (
  "net/http"
  "fmt"
  "log"
  "io/ioutil"
)

func main() {
  done := make(chan bool, 1)

  for i := 0; i < 10; i++ {
    go func(){
      for {
	resp, err := http.Get("http://lucas-dev.forcloudy.com")

	if err != nil {
	  log.Fatal(err)
	}

	defer resp.Body.Close()

	body, err := ioutil.ReadAll(resp.Body)

	fmt.Println(string(body))
      }
    }()
  }

  <-done
  /*for {
    resp, err := http.Get("http://lucas-dev.forcloudy.com")

    if err != nil {
      log.Fatal(err)
    }

    defer resp.Body.Close()

    body, err := ioutil.ReadAll(resp.Body)

    fmt.Println(string(body))
    count++
    fmt.Println(count)
  }*/
}
