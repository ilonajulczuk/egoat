package protocol

import (
	"crypto/sha512"
	"encoding/hex"
	"fmt"
)

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

func DownloadFile(peerAddress string, checksum string, fileSize int, downloadsDirectory string) []byte {
	return []byte("hello!")
}

func SendFile() {
	fmt.Println("Sending file")
	hasher := sha512.New()
	hasher.Write([]byte("hello, go!"))
	sha := hex.EncodeToString(hasher.Sum(nil))
	fmt.Println(sha)
}

func RequestDownload(waiting_address string, download_address string, wanted_checksum string) {
}
