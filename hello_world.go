package main

import (
	"os"
	"fmt"
	"net/http"
)

func main() {
	hostname, _ := os.Hostname()

	http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		fmt.Fprintf(w, "Hello, you've requested: %s\n", hostname)
	})

	http.ListenAndServe(":8080", nil)
}
