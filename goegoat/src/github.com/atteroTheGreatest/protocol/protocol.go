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

func ComputeChecksum(data []byte) string {
	hasher := sha512.New()
	sha := hex.EncodeToString(hasher.Sum(nil))
	return sha
}

func Contains(list []string, elem string) bool {
	for _, t := range list {
		if t == elem {
			return true
		}
	}
	return false
}

func First0(buf []byte) (first0 int) {
	for i, b := range buf {
		if b == 0 {
			first0 = i
			break
		}
	}
	return
}

func ChoosePeer(server_url string, wantedChecksum string, downloaderAddress string) string {
	return "127.0.0.1:6666"
}

func check(err error) {
	if err != nil {
		panic(err)
	}
}

func AcceptDownloadRequest(checksums_filenames map[string]string, waitingAddress string, forUpload chan string, bindingAddress string) {
	buf := make([]byte, CHUNKSIZE)

	addr, err := net.ResolveUDPAddr("udp", waitingAddress)

	if err != nil {
		panic(err)
	}
	sock, err := net.ListenUDP("udp", addr)

	check(err)
	for {
		sock.ReadFromUDP(buf)
		first0 := First0(buf)
		res := &RequesterMessage{}
		err = json.Unmarshal([]byte(string(buf[:first0])), &res)
		check(err)
		filename, ok := checksums_filenames[res.Checksum]
		if ok {
			fileSize, err := FileSize(filename)
			check(err)
			acceptMessage := &AcceptMessage{res.Checksum, bindingAddress, fileSize}

			replyConn, err := net.Dial("udp", res.WaitingAddress)
			messageInJSON, _ := json.Marshal(acceptMessage)
			check(err)
			replyConn.Write(messageInJSON)

			forUpload <- string(res.Checksum)
		} else {
		}
	}
}

type RequesterMessage struct {
	Checksum       string
	WaitingAddress string
}

type AcceptMessage struct {
	Checksum         string
	StreamingAddress string
	FileSize         int
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

func RequestFile(checksum string, uploaderAddress string, waitingAddress string) (response *AcceptMessage) {

	conn, err := net.Dial("udp", uploaderAddress)
	check(err)
	message := &RequesterMessage{
		Checksum:       checksum,
		WaitingAddress: waitingAddress}

	messageInJSON, _ := json.Marshal(message)
	conn.Write(messageInJSON)

	buf := make([]byte, CHUNKSIZE)
	addr, err := net.ResolveUDPAddr("udp", waitingAddress)
	if err != nil {
		panic(err)
	}

	sock, err := net.ListenUDP("udp", addr)
	sock.ReadFromUDP(buf)
	first0 := First0(buf)
	acceptMessage := &AcceptMessage{}
	err = json.Unmarshal([]byte(string(buf[:first0])), &acceptMessage)
	fmt.Println(acceptMessage)
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

	n := 0

	for n < fileSize-CHUNKSIZE {
		n, err = conn.Read(buf)
		if err != nil && err != io.EOF {
			panic(err)
		}
		if n == 0 {
			break
		}

		_, err = fo.Write(buf)
		if err != nil {
			fmt.Println("Error send reply:", err.Error())
		}
		fileBytes = append(fileBytes, buf...)
	}

	left := fileSize - n
	if left > 0 {
		buf := make([]byte, left)
		n, err = conn.Read(buf)
		if err != nil && err != io.EOF {
			panic(err)
		}
		fileBytes = append(fileBytes, buf...)
		_, err = fo.Write(buf)
	}
	return
}

func StreamFile(bindingAddress string, fileName string, fileSize int, done chan bool) {
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
	done <- true
}

func RequestDownload(waiting_address string, download_address string, wanted_checksum string) {
}
