package main

import (
	"fmt"
	"io/ioutil"
	"log"
	"net/http"
)

func request(url string) {
	for i := 0; i < 10; i++ {
		go func() {
			for {
				resp, err := http.Get(url)

				if err != nil {
					log.Fatal(err)
				}

				defer resp.Body.Close()

				body, err := ioutil.ReadAll(resp.Body)

				fmt.Println(string(body))
			}
		}()
	}
}

func main() {
	done := make(chan bool, 1)

	request("http://192.168.204.132:32768")
	request("http://192.168.204.132:32769")
	request("http://192.168.204.132:32770")

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
