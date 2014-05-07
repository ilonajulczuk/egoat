package protocol

import (
	"crypto/sha512"
	"encoding/hex"
	"fmt"
    "net"
    "io"
    "os"
)

var CHUNKSIZE int = 512
func ComputeChecksum(data []byte) string {
	hasher := sha512.New()
	sha := hex.EncodeToString(hasher.Sum(nil))
	return sha
}

func ChoosePeer(server_url string, wantedChecksum string, downloaderAddress string) string {
	return "127.0.0.1:6666"
}

func AcceptDownloadRequest(sock string, checksum string) {

}

func DownloadFile(peerAddress string, checksum string, fileSize int, downloadsDirectory string, downloads chan []byte) {
    conn, err := net.Dial("tcp", peerAddress)
    if err != nil { panic(err) }

    buf := make([]byte, CHUNKSIZE)

    defer conn.Close()
    // open output file
    fo, err := os.Create(downloadsDirectory + "/" + checksum)
    if err != nil { panic(err) }
    // close fo on exit and check for its returned error
    defer func() {
        if err := fo.Close(); err != nil {
            panic(err)
        }
    }()

    n := 0
    fileBytes := make([]byte, 0)

    for n < fileSize - CHUNKSIZE{
        n, err = conn.Read(buf)
        if err != nil && err != io.EOF { panic(err) }
        if n == 0 { break }

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
        if err != nil && err != io.EOF { panic(err) }
        fileBytes = append(fileBytes, buf...)
        _, err = fo.Write(buf)
    }

	downloads <- fileBytes
}


func StreamFile(bindingAddress string, fileName string, fileSize int, done chan bool) {
    psock, err := net.Listen("tcp", bindingAddress)

    if err != nil {
        return
    }

    fi, err := os.Open(fileName)
    if err != nil { panic(err) }
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
        if err != nil && err != io.EOF { panic(err) }
        if n == 0 { break }

        _, err = conn.Write(buf)
	    if err != nil {
		    fmt.Println("Error send reply:", err.Error())
	    }
    }
    done <- true
}

func RequestDownload(waiting_address string, download_address string, wanted_checksum string) {
}
