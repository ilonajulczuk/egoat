package protocol

import (
	"crypto/sha512"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"net"
	"os"
)

var CHUNKSIZE int = 512
var INSIDE_URL = "0.0.0.0"

// Structs useful for communication
type RequesterMessage struct {
	Checksum       string `json:"checksum"`
	WaitingAddress string `json:"waiting_address"`
}

type AcceptMessage struct {
	Checksum         string `json:"checksum"`
	StreamingAddress string `json:"streaming_address"`
	FileSize         int    `json:"file_size"`
}

func ComputeChecksum(data []byte) string {
	hasher := sha512.New()
	hasher.Write(data)
	sha := hex.EncodeToString(hasher.Sum(nil))
	return sha
}

// Helper functions
func First0(buf []byte) (first0 int) {
	for i, b := range buf {
		if b == 0 {
			first0 = i
			break
		}
	}
	return
}

func FileSize(fileName string) (fileSize int, err error) {
	f, err := os.Open(fileName)
	if err != nil {
		panic(err)
	}
	fistat, err := f.Stat()
	fileSize = int(fistat.Size())
	return
}

func Check(err error) {
	if err != nil {
		panic(err)
	}
}

// Function used to P2P file sharing
func AcceptDownloadRequest(checksums_filenames map[string]string, waitingAddress string, bindingPort string, outsideUrl string) []string {
	buf := make([]byte, CHUNKSIZE)

	addr, err := net.ResolveUDPAddr("udp", waitingAddress)

	if err != nil {
		panic(err)
	}
	sock, err := net.ListenUDP("udp", addr)

	defer sock.Close()
	Check(err)
	sock.ReadFromUDP(buf)
	first0 := First0(buf)
	res := &RequesterMessage{}
	err = json.Unmarshal([]byte(string(buf[:first0])), &res)
	Check(err)
	filename, ok := checksums_filenames[res.Checksum]
	if ok {
		fileSize, err := FileSize(filename)
		Check(err)

		bindingOutsideAddress := outsideUrl + ":" + bindingPort
		acceptMessage := &AcceptMessage{res.Checksum, bindingOutsideAddress, fileSize}
		replyConn, err := net.Dial("udp", res.WaitingAddress)
		messageInJSON, _ := json.Marshal(acceptMessage)
		Check(err)
		replyConn.Write(messageInJSON)
		bindingAddress := INSIDE_URL + ":" + bindingPort
		message := []string{bindingAddress, res.Checksum}

		return message
	} else {
		panic(ok)
	}
}

func RequestFile(checksum string, uploaderAddress string, waitingPort string, outsideUrl string) (response *AcceptMessage) {
	conn, err := net.Dial("udp", uploaderAddress)
	Check(err)

	waitingOutsideAddress := outsideUrl + ":" + waitingPort
	message := &RequesterMessage{
		Checksum:       checksum,
		WaitingAddress: waitingOutsideAddress}

	messageInJSON, _ := json.Marshal(message)
	conn.Write(messageInJSON)

	buf := make([]byte, CHUNKSIZE)
	waitingAddress := INSIDE_URL + ":" + waitingPort
	addr, err := net.ResolveUDPAddr("udp", waitingAddress)
	if err != nil {
		panic(err)
	}

	sock, err := net.ListenUDP("udp", addr)
	sock.ReadFromUDP(buf)
	first0 := First0(buf)
	acceptMessage := &AcceptMessage{}
	err = json.Unmarshal([]byte(string(buf[:first0])), &acceptMessage)
	Check(err)
	return acceptMessage
}

func DownloadFile(peerAddress string, checksum string, fileSize int, downloadsDirectory string) (fileBytes []byte) {
	conn, err := net.Dial("tcp", peerAddress)
	if err != nil {
		panic(err)
	}

	buf := make([]byte, CHUNKSIZE)

	defer conn.Close()
	// open output file
	fo, err := os.Create(downloadsDirectory + "/" + checksum)
	if err != nil {
		panic(err)
	}
	// close fo on exit and check for its returned error
	defer func() {
		if err := fo.Close(); err != nil {
			panic(err)
		}
	}()

	downloaded := 0

	n := 0
	for downloaded < fileSize-CHUNKSIZE {
		n, err = conn.Read(buf)
		if err != nil && err != io.EOF {
			panic(err)
		}
		downloaded += n

		_, err = fo.Write(buf)
		if err != nil {
			fmt.Println("Error send reply:", err.Error())
		}
		fileBytes = append(fileBytes, buf...)
	}

	left := fileSize - downloaded
	if left > 0 {
		buf := make([]byte, left)
		n, err = conn.Read(buf)
		if err != nil && err != io.EOF {
			panic(err)
		}
		downloaded += n
		fileBytes = append(fileBytes, buf...)
		_, err = fo.Write(buf)
	}
	return
}

func StreamFile(bindingAddress string, fileName string, fileSize int) {
	psock, err := net.Listen("tcp", bindingAddress)

	if err != nil {
		return
	}

	fi, err := os.Open(fileName)
	if err != nil {
		panic(err)
	}
	// close fi on exit and check for its returned error
	defer func() {
		if err := fi.Close(); err != nil {
			panic(err)
		}
	}()

	n := 0
	buf := make([]byte, CHUNKSIZE)

	conn, err := psock.Accept()
	if err != nil {
		return
	}

	defer conn.Close()

	for n < fileSize {
		n, err := fi.Read(buf)
		if err != nil && err != io.EOF {
			panic(err)
		}
		if n == 0 {
			break
		}

		_, err = conn.Write(buf)
		if err != nil {
			fmt.Println("Error send reply:", err.Error())
		}
	}
}
