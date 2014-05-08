package main

import (
        "github.com/atteroTheGreatest/protocol"
        "io/ioutil"
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

func Announce(checksums_filenames map[string]string, serverUrl string) {

}

func ChoosePeer(serverUrl string, checksum string) {

}

func main() {
}
