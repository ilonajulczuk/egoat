package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"github.com/atteroTheGreatest/protocol"
	"io/ioutil"
	"net/http"
        "time"
	"net/url"
        "strconv"
)

func Discover(directory string) (checksums_filenames map[string]string) {
	files, _ := ioutil.ReadDir(directory)
	checksums_filenames = make(map[string]string)
	for _, f := range files {
		buf, err := ioutil.ReadFile(directory + "/" + f.Name())
		protocol.Check(err)
		checksum := protocol.ComputeChecksum(buf)
		checksums_filenames[checksum] = f.Name()
	}
	return
}

func Announce(checksums_filenames map[string]string, announceUrl string, address string) {

	marshalled, err := json.Marshal(checksums_filenames)
	protocol.Check(err)
	checksum_files_json := string(marshalled)
	protocol.Check(err)
	values := url.Values{"address": {address}, "checksum_files": {checksum_files_json}}
	protocol.Check(err)
	resp, err := http.PostForm(announceUrl, values)
	protocol.Check(err)
	fmt.Println(resp)

	defer resp.Body.Close()
}

func ChoosePeer(serverUrl string, checksum string) (string) {
    return "127.0.0.1:5022"
}

type AnnounceMessage struct {
	address        string
	checksum_files map[string]string
}

func main() {
	serverUrl := flag.String("server_url", "http://127.0.0.1:5000/", "Url of tracker server")
	baseUrl := "127.0.0.1:"
	uploaderPort := flag.Int("uploader_port", 5673, "Port for uploader")
	downloaderPort := flag.Int("downloader_port", 5674, "Port for downloader")
	wantedChecksum := flag.String("checksum", "", "Checksum to download")
	directory := flag.String("directory", "test_files/", "Directory to share")
	flag.Parse()
	downloaderAddress := baseUrl + strconv.Itoa(*downloaderPort)
	uploaderAddress := baseUrl + strconv.Itoa(*uploaderPort)
	fmt.Println("word:", *serverUrl)
	fmt.Println("numb:", *uploaderPort)
	fmt.Println("numb:", *downloaderPort)
	fmt.Println("numb:", *wantedChecksum)
        fmt.Println("downloaderAddress:", downloaderAddress)
        fmt.Println("will discover directories!")
	checksums_filenames := Discover(*directory)

        fmt.Println("Discovered!")
        done := make(chan bool)
	ticker := time.NewTicker(time.Millisecond * 5000)
	go func() {
		for _ = range ticker.C {
			Announce(checksums_filenames, *serverUrl+"hello/", uploaderAddress)
		}
	}()

	forUpload := make(chan string)
        toRequest := make(chan string, 5)
        toDownload := make(chan *protocol.AcceptMessage)

        fmt.Println("putting checksum into channel")
        toRequest<-*wantedChecksum

	bindingAddress := "127.0.0.1:5678"


	go protocol.AcceptDownloadRequest(checksums_filenames, uploaderAddress, forUpload, bindingAddress)


        go func () {
            for checksum := range(toRequest){
                fmt.Println("requesting", checksum)
                newPeer := ChoosePeer(*serverUrl, checksum)
                fmt.Println("info", checksum, newPeer, downloaderAddress)
                response := protocol.RequestFile(checksum, newPeer, downloaderAddress)
                fmt.Println("requesting successful!", response)
                //toDownload<-response
            }
        }()
        downloadsDirectory := "Downloads/"
	downloads := make(chan []byte)
	go func() {
            for response := range(toDownload) {
		downloadedFile := protocol.DownloadFile(response.StreamingAddress, response.Checksum, response.FileSize, downloadsDirectory)
		downloads <- downloadedFile
            }
	}()

	<-forUpload
        <-done

}
