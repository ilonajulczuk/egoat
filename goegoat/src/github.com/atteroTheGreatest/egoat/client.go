package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"github.com/atteroTheGreatest/protocol"
	"io/ioutil"
	"net/http"
	"net/url"
	"strconv"
	"time"
)

type Tuple []interface{}

func Discover(directory string) (checksums_filenames map[string]string) {
	files, _ := ioutil.ReadDir(directory)
	checksums_filenames = make(map[string]string)
	for _, f := range files {
		buf, err := ioutil.ReadFile(directory + "/" + f.Name())
		protocol.Check(err)
		checksum := protocol.ComputeChecksum(buf)
		checksums_filenames[checksum] = directory + "/" + f.Name()
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

	defer resp.Body.Close()
}

func ChoosePeer(serverUrl string, checksum string) string {
        resp, err := http.Get(serverUrl + "file/" + checksum)
	protocol.Check(err)
        data, err := ioutil.ReadAll(resp.Body)
        protocol.Check(err)
        var peersMessage map[string]interface{}
        err = json.Unmarshal(data, &peersMessage)
        protocol.Check(err)

	return peersMessage["addresses"].( []interface {})[0].(string)
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
	checksums_filenames := Discover(*directory)

	done := make(chan bool)
	ticker := time.NewTicker(time.Millisecond * 5000)
	go func() {
		for _ = range ticker.C {
			Announce(checksums_filenames, *serverUrl+"hello/", uploaderAddress)
		}
	}()

	forUpload := make(chan []string)
	toRequest := make(chan string, 5)
	toDownload := make(chan *protocol.AcceptMessage)
        uploads := make(chan bool)
        uploadedFiles := make(chan string)

	toRequest <- *wantedChecksum

	bindingAddress := "127.0.0.1:5678"

	go protocol.AcceptDownloadRequest(checksums_filenames, uploaderAddress, forUpload, bindingAddress)

	go func() {
		for checksum := range toRequest {
			newPeer := ChoosePeer(*serverUrl, checksum)
			response := protocol.RequestFile(checksum, newPeer, downloaderAddress)
			toDownload <- response
		}
	}()
	downloadsDirectory := "Downloads"
	downloads := make(chan Tuple, 5)
	go func() {
		for response := range toDownload {
			time.Sleep(100 * time.Millisecond)
			downloadedFile := protocol.DownloadFile(response.StreamingAddress, response.Checksum, response.FileSize, downloadsDirectory)
			newChecksum := protocol.ComputeChecksum(downloadedFile)
			if newChecksum == response.Checksum {
				downloads <- Tuple{response.Checksum, true}
			} else {
				downloads <- Tuple{response.Checksum, false}
			}
		}
	}()

        go func() {
		for uploadArray := range forUpload {
                    bindingAddress := uploadArray[0]
                    checksum := uploadArray[1]
                    fileName := checksums_filenames[checksum]
                    fileSize, err := protocol.FileSize(fileName)
                    protocol.Check(err)
                    fmt.Println(bindingAddress)
                    protocol.StreamFile(bindingAddress, fileName, fileSize, uploads)
                    fmt.Println("streaming ready!")
                    uploadedFiles<-checksum
		}
	}()

	go func() {
		for downloadResult := range downloads {
			checksum := downloadResult[0].(string)
			success := downloadResult[1].(bool)
			fmt.Println("Download result", checksum, success)
			if !success {
				fmt.Println("Retrying download", checksum)
				toRequest <- checksum
			}
		}
	}()
	go func() {
		for checksum := range uploadedFiles {
			fmt.Println("Upload result", checksum)
		}
	}()

	<-done

}
