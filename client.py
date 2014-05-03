import requests
from multiprocessing import Process, Queue
import os
import argparse
from protocol import compute_checksum
import time
import json
import logging
from agents import (
    dealer_upload,
    dealer_download,
    uploader,
    downloader
)


logger = logging



class Client(object):
    def __init__(self, directory, server_url, address, waiting_port,
                 downloads_directory):
        self.directory = directory
        self.downloads_directory = downloads_directory
        self.waiting_port = waiting_port
        self.server_url = server_url
        self.address = address
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
        requests.post(self.server_url + 'hello/',
                      params={'checksum_files': json.dumps(self.check_sums),
                              'address': self.address})

    def serve(self, wanted_checksums):
        NUMBER_OF_UPLOADING_PROCESSES = 4
        NUMBER_OF_DOWNLOADING_PROCESSES = 4

        # Create queues
        wanted_checksums_queue = Queue()
        task_queue_upload = Queue()
        task_queue_download = Queue()
        done_queue_upload = Queue()
        done_queue_download = Queue()

        Process(
            target=dealer_upload,
            args=(
                self.address,
                self.check_sums,
                task_queue_upload)).start()

        waiting_address = ('127.0.0.1', self.waiting_port)
        Process(
            target=dealer_download,
            args=(
                self.server_url,
                self.address,
                waiting_address,
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
            self.announce()


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
    parser.add_argument("-d", "--downloads_directory", type=str, default='Downloads',
                        help="Directory to store downloads")
    args = parser.parse_args()

    if args.port:
        port = args.port
    else:
        port = 6666
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
