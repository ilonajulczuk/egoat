import requests
import os
import json
import time
import logging
import random
from hashlib import sha512
from socket_helpers import (
    sock_send,
    create_socket,
    sock_bind
)


logger = logging

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


def send_file(sending_address, filename):
    while True:
        try:
            sock = create_socket()
            chunksize = 1024
            file_size = os.path.getsize(filename)
            sent = 0
            with open(filename, 'r') as source_file:
                chunk = source_file.read(chunksize)
                while sent < file_size:
                    sent += len(chunk)
                    time.sleep(0.001)
                    sock_send(chunk, sending_address, sock)

            return True
        except:
            time.sleep(1)
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

    sock = sock_bind(waiting_address)
    json_data, addr = sock.recvfrom(1024)  # buffer size is 1024 bytes
    sock.close()
    checksum, file_size = json.loads(json_data)
    if checksum != wanted_checksum or file_size == 0:
        return None
    else:
        return downloader_address, file_size


def download_file(peer_address, checksum, file_size):
    sock = sock_bind(peer_address)
    downloaded = 0
    chunksize = 1024
    downloaded_file = ""
    with open(checksum, 'w') as target_file:
        while (downloaded + 2 * chunksize) < file_size:
            chunk, _ = sock.recvfrom(chunksize)
            downloaded_file += chunk
            downloaded += len(chunk)
            time.sleep(0.01)
            target_file.write(chunk)
        last_size = file_size - downloaded
        chunk, _ = sock.recvfrom(last_size)
        target_file.write(chunk)
        sock.close()
    return downloaded_file

def compute_checksum(data):
    return str(sha512(data).hexdigest())
