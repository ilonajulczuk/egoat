from nose import tools as nt
from multiprocessing import Process
from protocol import(
    compute_checksum,
    Downloader,
    Uploader,
)
from socket_helpers import sock_send
import json
import os


def test_streaming_file():
    sending_address = "127.0.0.1:9631"

    filenames = [
        'test_files/short_file.txt',
        'test_files/short_file.txt',
        'test_files/file_for_upload.txt',
        'test_files/goat.jpg',
    ]

    for filename in filenames:
        print(filename)
        downloader = Downloader("test", "test")
        uploader = Uploader()
        with open(filename) as f:
            file_content = f.read()
        checksum = compute_checksum(file_content)

        file_size = os.path.getsize(filename)
        Process(target=uploader.stream_file, args=(sending_address, filename)).start()
        downloaded_file = downloader.download_file(sending_address, checksum,
                                        file_size)

        new_checksum = compute_checksum(downloaded_file)
        nt.eq_(len(file_content.split('\n')), len(downloaded_file.split('\n')))
        nt.eq_(new_checksum, checksum)


def test_downloading_file():
    sending_address = "127.0.0.1:9127"

    filenames = [
        'test_files/short_file.txt',
        'test_files/short_file.txt',
        'test_files/file_for_upload.txt',
        'test_files/goat.jpg',
    ]

    for filename in filenames:
        with open(filename) as f:
            file_content = f.read()
        checksum = compute_checksum(file_content)

        download_address = ("127.0.0.1", 9527)
        downloader = Downloader("test", download_address)
        uploader = Uploader()
        file_size = os.path.getsize(filename)
        Process(target=downloader.download_file, args=(sending_address, checksum,
                                        file_size)).start()
        uploader.stream_file(sending_address, filename)


def test_requesting_download():
    waiting_address = ("127.0.0.1", 9627)
    download_address = ("127.0.0.1", 9527)
    checksum = "test"
    downloader = Downloader(server_url="http://example.com", waiting_address=waiting_address)
    def mock_accept(download_address, waiting_address, checksum):
        ack_message = (download_address, checksum, 42)
        sock_send(json.dumps(ack_message), waiting_address)

    Process(target=mock_accept, args=(download_address, waiting_address, checksum)).start()
    downloader.request_download(download_address, checksum)


def test_accepting_request():
   pass
