package main

import "fmt"
import "github.com/atteroTheGreatest/protocol"

func main() {
    fmt.Println("Hello, new gopher!")
    protocol.SendFile()
    fmt.Println(protocol.ComputeChecksum([]byte("test")))
}
