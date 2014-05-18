import argparse
import json
import logging
import os
import requests
import time

from multiprocessing import Process, Queue
from threading import Timer

from agents import (
    dealer_upload,
    dealer_download,
    uploader,
    downloader
)
from protocol import compute_checksum
from protocol import Downloader, Uploader


logger = logging


class Client(object):
    def __init__(self, directory, server_url, uploader_port, downloader_port,
                 downloads_directory):
        self.directory = directory
        self.downloads_directory = downloads_directory
        self.server_url = server_url

        self.inside_ip = "0.0.0.0"
        self.outside_ip = "127.0.0.1"

        self.downloader_port = downloader_port
        self.uploader_port = uploader_port

        self.address = self.inside_ip + ":" + self.uploader_port
        self.check_sums = self.load_state()

    def discover(self):
        return [os.path.join(self.directory, filename)
                for filename in (os.listdir(self.directory))
                if os.path.isfile(os.path.join(self.directory, filename))]

    def compute_checksums(self, filenames):
        checksums = {}
        for filename in filenames:
            with open(filename, 'r') as file_to_check:
                file_content = file_to_check.read()
                checksums[compute_checksum(file_content)] = filename

        return checksums

    def load_state(self):
        check_sums = self.compute_checksums(self.discover())
        return check_sums

    def announce(self):
        response = requests.post(self.server_url + 'hello/',
                                 params={'checksum_files': json.dumps(self.check_sums),
                                         'port': self.uploader_port})
        self.outside_ip = response.text
        Timer(20, self.announce).start()

    def serve(self, wanted_checksums):
        NUMBER_OF_UPLOADING_PROCESSES = 4
        NUMBER_OF_DOWNLOADING_PROCESSES = 4

        # Create queues
        wanted_checksums_queue = Queue()
        task_queue_upload = Queue()
        task_queue_download = Queue()
        done_queue_upload = Queue()
        done_queue_download = Queue()
        self.announce()
        upload_helper = Uploader(inside_ip=self.inside_ip,
                                 outside_ip=self.outside_ip,
                                 port=self.uploader_port)

        Process(
            target=dealer_upload,
            args=(
                upload_helper,
                self.address,
                self.check_sums,
                task_queue_upload)).start()

        downloader_address = (self.inside_ip, self.downloader_port)
        download_helper = Downloader(self.server_url,
                                     self.downloader_port,
                                     inside_ip=self.inside_ip,
                                     outside_ip=self.outside_ip)

        Process(
            target=dealer_download,
            args=(
                download_helper,
                self.address,
                downloader_address,
                wanted_checksums_queue,
                task_queue_download)).start()

        # Start worker processes
        for i in range(NUMBER_OF_UPLOADING_PROCESSES):
            Process(
                target=uploader,
                args=(
                    task_queue_upload,
                    done_queue_upload)).start()

        for checksum in wanted_checksums:
            wanted_checksums_queue.put(checksum)

        for i in range(NUMBER_OF_DOWNLOADING_PROCESSES):
            Process(
                target=downloader,
                args=(
                    task_queue_download,
                    done_queue_download,
                    self.downloads_directory)).start()

        while True:
            if not done_queue_download.empty():
                download_result = done_queue_download.get()
                checksum, _, success = download_result
                if success:
                    print('Downloaded:\t%s %s %s' % download_result)
                else:
                    print('Retrying download:\t%s' % checksum)
                    wanted_checksums_queue.put(checksum)

            if not done_queue_upload.empty():
                print('Uploaded:\t%s %s %s' % done_queue_upload.get())
            time.sleep(0.05)


def main():
    parser = argparse.ArgumentParser(description="P2P file sharing client.")
    parser.add_argument("-q", "--quiet", action="store_true")

    parser.add_argument("directory", type=str, help="Directory to serve.")
    parser.add_argument("address", type=str, help="Addres to serve on.")
    parser.add_argument("-s", "--server_url", type=str, default="atte.ro",
                        help="Server to announce files.")
    parser.add_argument("-c", "--checksum", type=str, default=None,
                        help="Checksum of file you want to download")
    parser.add_argument(
        "-f",
        "--checksum_file",
        type=str,
        default=None,
        help="List with stored checksums of files you want to download")
    parser.add_argument("-p", "--port", type=str, default=None,
                        help="Port to wait for comming requests")
    parser.add_argument(
        "-d",
        "--downloads_directory",
        type=str,
        default='Downloads',
        help="Directory to store downloads")
    args = parser.parse_args()

    port = args.port
    client = Client(args.directory, args.server_url, args.address,
                    port, args.downloads_directory)

    wanted_checksums = []
    if args.checksum:
        wanted_checksums.append(args.checksum)
    elif args.checksum_file:
        with open(args.checksum_file) as file_with_list_of_downloads:
            for line in file_with_list_of_downloads.readlines():
                wanted_checksums.append(line.strip())

    if args.quiet:
        pass
    else:
        logging.basicConfig(filename='egoat.log', level=logging.INFO)
    client.announce()
    client.serve(wanted_checksums)


if __name__ == '__main__':
    main()
