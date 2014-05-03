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


logger = logging

def convert_address(address):
    if isinstance(address, (unicode, str)):
        udp_ip, udp_port = address.split(":")
    elif len(address) == 2:
        udp_ip, udp_port = address
    else:
        raise ValueError("Wrong address for a socket!")
    udp_port = int(udp_port)
    return udp_ip, udp_port


def sock_send(payload, address, sock=None):
    if sock is None:
        sock = socket.socket(socket.AF_INET,  # Internet
                             socket.SOCK_DGRAM)  # UDP
    udp_ip, udp_port = convert_address(address)
    sock.sendto(payload, (udp_ip, udp_port))


def sock_bind(address):
    udp_ip, udp_port = convert_address(address)
    sock = socket.socket(socket.AF_INET,  # Internet
                         socket.SOCK_DGRAM)  # UDP
    sock.bind((udp_ip, udp_port))
    return sock


def send_file(sending_address, filename):
    while True:
        try:
            sock = socket.socket(socket.AF_INET,  # Internet
                                 socket.SOCK_DGRAM)  # UDP
            chunksize = 1024
            file_size = os.path.getsize(filename)
            sent = 0
            with open(filename, 'r') as f:
                chunk = f.read(chunksize)
                while sent < file_size:
                    sent += chunksize
                    time.sleep(0.001)
                    sock_send(chunk, sending_address, sock)
            return True
        except:
            import traceback
            logger.exception(traceback.format_exc())


def accept_download_request(sock, checksum_files):
    message, addr = sock.recvfrom(1024)
    deal_address, sending_address, checksum = json.loads(message)
    filename = checksum_files[checksum]
    ack_message = (checksum, os.path.getsize(filename))
    sock_send(json.dumps(ack_message), deal_address)
    return sending_address, checksum, filename


def request_download(waiting_address, download_address, wanted_checksum):
    waiting_udp_ip, waiting_udp_port = waiting_address
    waiting_udp_port = int(waiting_udp_port)
    downloader_address = ('127.0.0.1', 3300 +
                          random.randint(0, 20) +
                          int(str(int(wanted_checksum, 16))[:4]))
    message = [
        ((waiting_udp_ip,
          waiting_udp_port)),
        downloader_address,
        wanted_checksum]

    checksum_request = json.dumps(message)
    sock_send(checksum_request, download_address)

    sock = socket.socket(socket.AF_INET,  # Internet
                         socket.SOCK_DGRAM)  # udp
    sock.bind((waiting_udp_ip, waiting_udp_port))
    json_data, addr = sock.recvfrom(1024)  # buffer size is 1024 bytes
    sock.close()
    checksum, file_size = json.loads(json_data)
    if checksum != wanted_checksum or file_size == 0:
        return None
    else:
        return downloader_address, file_size

def uploader(upload, upload_done):
    for peer_address, checksum, filename in iter(upload.get, 'STOP'):
        try:
            result = send_file(peer_address, filename)
            upload_done.put((checksum, peer_address, result))
            logger.info("Sending done!")
        except:
            import traceback
            logger.info("Sending failure!")
            logger.exception(traceback.format_exc())


def download_file(peer_address, checksum, file_size):
    udp_ip, udp_port = peer_address
    udp_port = int(udp_port)
    sock = socket.socket(socket.AF_INET,  # Internet
                         socket.SOCK_DGRAM)  # UDP
    sock.bind((udp_ip, udp_port))
    downloaded = 0
    chunksize = 1024
    downloaded_file = ""
    with open(checksum, 'w') as f:
        while downloaded < file_size:
            chunk, _ = sock.recvfrom(chunksize)
            downloaded_file += chunk
            downloaded += len(chunk)
            f.write(chunk)
            logger.info(float(downloaded) / file_size)
    sock.close()
    return downloaded_file


def downloader(download, download_done):
    for peer_address, checksum, file_size in iter(download.get, 'STOP'):
        while True:
            try:
                downloaded_file = download_file(peer_address, checksum, file_size)
                downloaded_checksum = compute_checksum(downloaded_file)
                download_correct = downloaded_checksum == checksum
                if download_correct:
                    download_done.put((checksum, peer_address, True))
                    break
            except:
                import traceback
                logger.exception(traceback.format_exc())
                time.sleep(4)
                logger.info("will restart soon...")


def dealer_upload(upload_address, checksum_files, upload):
    sock = sock_bind(upload_address)
    while True:
        request = accept_download_request(sock, checksum_files)
        if request:
            sending_address, checksum, filename = request
            upload.put((sending_address, checksum, filename))
    sock.close()


def get_uploader_addresses(server_url, checksum):
    url = server_url + 'file/' + checksum
    response = requests.get(url)
    addresses = json.loads(response.text)
    return addresses


def choose_peer(server_url, wanted_checksum, downloader_address):
    all_addresses = get_uploader_addresses(server_url, wanted_checksum)
    if downloader_address in all_addresses:
        all_addresses.remove(downloader_address)
    if not all_addresses:
        time.sleep(2)
        logger.info("No one has it!")
        logger.info("Checksum: %s..." % wanted_checksum[:6])
    if all_addresses:
        download_address = random.choice(all_addresses)
    else:
        download_address = None
    return download_address


def dealer_download(
        server_url,
        dealer_downloader_address,
        waiting_address,
        wanted_checksums,
        download):
    while wanted_checksums:
        wanted_checksum = wanted_checksums[0]
        try:
            download_address = choose_peer(server_url, wanted_checksum, dealer_downloader_address)

            if download_address is None:
                continue
            response =  request_download(waiting_address, download_address, wanted_checksum)

            if response is not None:
                downloader_address, file_size = response
                download.put((downloader_address, wanted_checksum, file_size))
                wanted_checksums.remove(wanted_checksum)
        except:
            import traceback
            logger.exception(traceback.format_exc())
            time.sleep(1)


def compute_checksum(data):
    return str(sha512(data).hexdigest())


class Client(object):
    CHECKSUM_STORAGE_BASE = '.checksums'

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

    def compute_checksums(self, filenames):
        checksums = {}
        for filename in filenames:
            with open(filename, 'r') as f:
                file_content = f.read()
                checksums[compute_checksum(file_content)] = filename

        return checksums

    def load_state(self):
        try:
            storage_filename = self.CHECKSUM_STORAGE_BASE + \
                str(sha512(self.directory).hexdigest())
            with open(storage_filename, 'r') as f:
                check_sums = json.load(f)
        except IOError:
            check_sums = self.compute_checksums(self.discover())
            with open(storage_filename, 'w') as f:
                json.dump(check_sums, f)
        return check_sums

    def announce(self):
        requests.post(self.server_url + 'hello/',
                      params={'checksum_files': json.dumps(self.check_sums),
                              'address': self.address})

    def serve(self, wanted_checksums):
        NUMBER_OF_UPLOADING_PROCESSES = 4
        NUMBER_OF_DOWNLOADING_PROCESSES = 4

        # Create queues
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
                wanted_checksums,
                task_queue_download)).start()

        # Start worker processes
        for i in range(NUMBER_OF_UPLOADING_PROCESSES):
            Process(
                target=uploader,
                args=(
                    task_queue_upload,
                    done_queue_upload)).start()

        for i in range(NUMBER_OF_DOWNLOADING_PROCESSES):
            Process(
                target=downloader,
                args=(
                    task_queue_download,
                    done_queue_download)).start()
        while True:
            if not done_queue_download.empty():
                print('Downloaded\t%s %s %s' % done_queue_download.get())

            if not done_queue_upload.empty():
                print('Uploaded:\t%s %s %s' % done_queue_upload.get())
            time.sleep(2)
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
