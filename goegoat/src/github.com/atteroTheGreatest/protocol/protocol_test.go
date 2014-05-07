package protocol

import (
    "testing"
    "fmt"
    "os"
    . "gopkg.in/check.v1"
)



func Test(t *testing.T) { TestingT(t) }

type MySuite struct{}

var _ = Suite(&MySuite{})

func (s * MySuite) TestStreamingFile(c *C) {
    done := make(chan bool)
    downloads := make(chan []byte)
    peerAddress := "127.0.0.1:3333"
    downloadsDirectory := "Downloads"
    fileName := "test.txt"

    f, err := os.Open(fileName)
    if err != nil { panic(err) }

    fistat, err := f.Stat()
    fileSize := int(fistat.Size())
    if err != nil {
      // Could not obtain stat, handle error
    }
    go StreamFile(peerAddress, fileName, fileSize, done)
    go DownloadFile(peerAddress, "test", fileSize, downloadsDirectory, downloads)
    <-done
    downloadedFile := <-downloads
    fmt.Println(string(downloadedFile))
    c.Assert(string(downloadedFile), Equals, "testing is good for you!\n")
}
