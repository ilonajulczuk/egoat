import requests
import random
from hashlib import sha512
from multiprocessing import Process, Queue
import os
import argparse
import time
import json
import logging
import socket


log = logging

def start_connection(peer_address, check_sum, filesize):
    UDP_IP, UDP_PORT  = peer_address
    UDP_PORT = int(UDP_PORT)
    sock = socket.socket(socket.AF_INET, # Internet
                          socket.SOCK_DGRAM) # UDP
    sock.sendto(json.dumps([check_sum, filesize]), (UDP_IP, UDP_PORT))
    return peer_address


def send_file(sending_address, filename):
    while True:
        try:
            UDP_IP, UDP_PORT  = sending_address
            UDP_PORT = int(UDP_PORT)
            sock = socket.socket(socket.AF_INET, # Internet
                                  socket.SOCK_DGRAM) # UDP
            chunksize = 1024
            file_size = os.path.getsize(filename)
            sent = 0
            with open(filename, 'r') as f:
                chunk = f.read(chunksize)
                while sent < file_size:
                    sent += chunksize
                    time.sleep(0.001)
                    sock.sendto(chunk, tuple(sending_address))
            return True
        except:
            import traceback
            log.exception(traceback.format_exc())



def sender(upload, upload_done):
    for deal_address, peer_address, checksum, filename in iter(upload.get, 'STOP'):
        try:
            result = send_file(peer_address, filename)
            upload_done.put((checksum, peer_address, result))
            log.info("Sending done!")
        except:
            import traceback
            log.info("Sending failure!")
            log.exception(traceback.format_exc())

def downloader(download, download_done):
    for peer_address, checksum, file_size in iter(download.get, 'STOP'):
        while True:
            try:
                UDP_IP, UDP_PORT  = peer_address
                UDP_PORT = int(UDP_PORT)
                sock = socket.socket(socket.AF_INET, # Internet
                                     socket.SOCK_DGRAM) # UDP
                sock.bind((UDP_IP, UDP_PORT))
                downloaded = 0
                chunksize = 1024
                downloaded_file = ""
                with open(checksum, 'w') as f:
                    while downloaded < file_size:
                        chunk, addr = sock.recvfrom(chunksize)
                        downloaded_file += chunk
                        downloaded += len(chunk)
                        f.write(chunk)
                        log.info(float(downloaded)/file_size)
                sock.close()
                log.info("Downloaded: %s..." % checksum[:6])
                download_done.put((checksum, peer_address, True))
                break

            except:
                import traceback
                log.exception(traceback.format_exc())
                time.sleep(4)
                log.info("will restart soon...")


def dealer_upload(upload_address, checksum_files, upload):
    UDP_IP, UDP_PORT  = upload_address.split(":")
    UDP_PORT = int(UDP_PORT)
    log.info("will wait at: %s" % upload_address)
    sock = socket.socket(socket.AF_INET, # Internet
                         socket.SOCK_DGRAM) # UDP
    sock.bind((UDP_IP, UDP_PORT))

    while True:
        message, addr = sock.recvfrom(1024) # buffer size is 1024 bytes
        time.sleep(1)
        deal_address, sending_address, checksum = json.loads(message)
        filename = checksum_files[checksum]
        ack_message = (checksum, os.path.getsize(filename))
        deal_UDP_IP, deal_UDP_PORT = deal_address
        deal_UDP_PORT = int(deal_UDP_PORT)
        sock.sendto(json.dumps(ack_message), (deal_UDP_IP, deal_UDP_PORT))
        time.sleep(1)
        upload.put((deal_address, sending_address, checksum, filename ))


def get_uploader_addresses(server_url, checksum):
    url = server_url + 'file/' + checksum
    response = requests.get(url)
    addresses = json.loads(response.text)
    return addresses


def dealer_download(server_url, downloader_address, waiting_address, wanted_checksums, download):
    while wanted_checksums:
        wanted_checksum = wanted_checksums[0]
        time.sleep(1)
        try:
            all_addresses = get_uploader_addresses(server_url, wanted_checksum)
            if downloader_address in all_addresses:
                all_addresses.remove(downloader_address)
            if not all_addresses:
                time.sleep(2)
                log.info("No one has it!")
                log.info("Checksum: %s..." % wanted_checksum[:6])
                continue
            download_address = all_addresses[0]
            UDP_IP, UDP_PORT  = download_address.split(":")
            UDP_PORT = int(UDP_PORT)
            sock = socket.socket(socket.AF_INET, # Internet
                                  socket.SOCK_DGRAM) # UDP

            waiting_UDP_IP, waiting_UDP_PORT  = waiting_address
            log.info("Here waiting: %s" % waiting_UDP_PORT)

            downloader_address = ('127.0.0.1', 3300 + random.randint(0, 20) + int(str(int(wanted_checksum, 16))[:4]))
            message = [((waiting_UDP_IP, waiting_UDP_PORT)), downloader_address, wanted_checksum]
            sock.sendto(json.dumps(message), (UDP_IP, UDP_PORT))

            waiting_UDP_PORT = int(waiting_UDP_PORT)
            sock = socket.socket(socket.AF_INET, # Internet
                                  socket.SOCK_DGRAM) # UDP
            sock.bind((waiting_UDP_IP, waiting_UDP_PORT))
            json_data, addr = sock.recvfrom(1024) # buffer size is 1024 bytes
            sock.close()
            checksum, filesize = json.loads(json_data)
            if checksum != wanted_checksum:
                log.info("Whut?? It's a mistake!")
                continue

            if filesize:
                download.put((downloader_address, checksum, filesize))
                wanted_checksums.remove(wanted_checksum)
            else:
                log.info("oh, no deal")
        except:
            import traceback
            log.exception(traceback.format_exc())
            time.sleep(1)


class Client:
    CHECKSUM_STORAGE = '.checksums'
    def __init__(self, directory, server_url, address, waiting_port=6666):
        self.directory = directory
        self.waiting_port = waiting_port
        self.server_url = server_url
        self.address = address
        self.check_sums = self.load_state()

    def discover(self):
        def whole_path(base, filename):
            return base + "/" + filename

        return [whole_path(self.directory, filename)
                for filename in (os.listdir(self.directory))
                if os.path.isfile(whole_path(self.directory, filename))]


    def compute_check_sums(self, filenames):
        check_sums = {}
        for filename in filenames:
            with open(filename, 'r') as f:
                file_content = f.read()
                check_sums[str(sha512(file_content).hexdigest())] = filename

        return check_sums

    def load_state(self):
        try:
            storage_filename = self.CHECKSUM_STORAGE + str(sha512(self.directory).hexdigest())
            with open(storage_filename, 'r') as f:
                check_sums = json.load(f)
        except IOError:
            check_sums = self.compute_check_sums(self.discover())
            with open(storage_filename, 'w') as f:
                json.dump(check_sums, f)
        return check_sums

    def announce(self):
        requests.post(self.server_url + 'hello/',
                      params={'checksum_files': json.dumps(self.check_sums),
                     'address': self.address})

    def serve(self, wanted_checksums):
        NUMBER_OF_PROCESSES = 4

        # Create queues
        task_queue_upload = Queue()
        task_queue_download = Queue()
        done_queue_upload = Queue()
        done_queue_download = Queue()


        Process(target=dealer_upload, args=(self.address, self.check_sums, task_queue_upload)).start()

        waiting_address = ('127.0.0.1', self.waiting_port)
        Process(target=dealer_download, args=(self.server_url, self.address, waiting_address, wanted_checksums, task_queue_download)).start()

        # Start worker processes
        for i in range(NUMBER_OF_PROCESSES):
            Process(target=sender, args=(task_queue_upload, done_queue_upload)).start()

        for i in range(NUMBER_OF_PROCESSES):
            Process(target=downloader, args=(task_queue_download, done_queue_download)).start()
        while True:
            if not done_queue_download.empty():
                print('Downloaded\t%s %s %s' % done_queue_download.get())

            if not done_queue_upload.empty():
                print('Uploaded:\t%s %s %s' % done_queue_upload.get())
            time.sleep(2)
            self.announce()

        # Tell child processes to stop
        for i in range(NUMBER_OF_PROCESSES):
            task_queue_upload.put('STOP')
            task_queue_download.put('STOP')


def main(*args, **kwargs):
    parser = argparse.ArgumentParser(description="P2P file sharing client.")
    parser.add_argument("-q", "--quiet", action="store_true")

    parser.add_argument("directory", type=str, help="Directory to serve.")
    parser.add_argument("address", type=str, help="Addres to serve on.")
    parser.add_argument("-s", "--server_url", type=str, default="atte.ro",
                        help="Server to announce files.")
    parser.add_argument("-c", "--checksum", type=str, default=None,
                        help="Checksum of file you want to download")
    parser.add_argument("-f", "--checksum_file", type=str, default=None,
                        help="List with stored checksums of files you want to download")
    parser.add_argument("-p", "--port", type=str, default=None,
                        help="Port to wait for comming requests")
    args = parser.parse_args()

    if args.port:
        port = args.port
    else:
        port = 6666
    client = Client(args.directory, args.server_url, args.address, port)

    wanted_checksums = []
    if args.checksum:
        wanted_checksums.append(args.checksum)
    elif args.checksum_file:
        with open(args.checksum_file) as f:
            for line in f.readlines():
                wanted_checksums.append(line.strip())

    if args.quiet:
        pass
    else:
        logging.basicConfig(level=logging.INFO)
    client.announce()
    client.serve(wanted_checksums)


if __name__ == '__main__':
    main()
