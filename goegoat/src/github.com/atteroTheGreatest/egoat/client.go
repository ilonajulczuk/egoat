package main

import "fmt"
import "github.com/atteroTheGreatest/protocol"

func main() {
    fmt.Println("Hello, new gopher!")
    protocol.StreamFile("127.0.0.1:4444", "test.txt")
    fmt.Println(protocol.ComputeChecksum([]byte("test")))
}
