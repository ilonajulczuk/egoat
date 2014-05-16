package protocol

import (
	. "gopkg.in/check.v1"
	"testing"
	"time"
)

func Test(t *testing.T) { TestingT(t) }

type TestProtocol struct{}

var _ = Suite(&TestProtocol{})

func (s *TestProtocol) TestStreamingFile(c *C) {
	downloads := make(chan []byte)
	peerAddress := "127.0.0.1:3333"
	downloadsDirectory := "Downloads"
	fileName := "test.txt"
	fileSize, err := FileSize(fileName)
	if err != nil {
		// Could not obtain stat, handle error
	}
	go StreamFile(peerAddress, fileName, fileSize)
	go func() {
		downloadedFile := DownloadFile(peerAddress, "test", fileSize, downloadsDirectory)
		downloads <- downloadedFile
	}()
	downloadedFile := <-downloads
	c.Assert(string(downloadedFile), Equals, "testing is good for you!\n")
}

func (s *TestProtocol) TestRequestingFile(c *C) {
	forUpload := make(chan []string)
	waitingAddress := "0.0.0.0:4444"
	outsideUrl := "127.0.0.1"
	requesterPort := "5444"
	bindingPort := "5678"

	checksums_filenames := map[string]string{"test": "test.txt", "test2": "test.txt"}
	checksum := "test"

	go func() {
		message := AcceptDownloadRequest(checksums_filenames, waitingAddress, bindingPort, outsideUrl)
		forUpload <- message
	}()
	time.Sleep(30 * time.Millisecond)
	response := RequestFile(checksum, waitingAddress, requesterPort, outsideUrl)

	<-forUpload
	c.Assert(response.Checksum, Equals, checksum)
	c.Assert(response.StreamingAddress, Equals, outsideUrl+":"+bindingPort)
}
