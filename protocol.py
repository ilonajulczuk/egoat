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
    sock_bind,
    sock_connect,
    convert_address,
)

import socket


CHUNKSIZE = 512

logger = logging


class Uploader(object):

    def __init__(self, outside_ip='127.0.0.1', inside_ip='0.0.0.0'):
        pass

    def stream_file(self, binding_address, filename):
        sock = create_socket(socktype="tcp")
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(convert_address(binding_address))
        logger.info("starting listening!")
        sock.listen(5)
        try:
            comm_sock, addr = sock.accept()
            sent = 0
            file_size = os.path.getsize(filename)
            with open(filename, 'r') as source_file:
                while sent < file_size:
                    chunk = source_file.read(CHUNKSIZE)
                    comm_sock.send(chunk)
                    sent += len(chunk)
            sock.shutdown(1)
            sock.close()
            return True
        except:
            import traceback
            logger.exception(traceback.format_exc())

    def accept_download_request(self, sock, checksum_files):
        message, addr = sock.recvfrom(1024)

        loaded_json = json.loads(message)
        try:
            deal_address, checksum = loaded_json
            filename = checksum_files[checksum]
        except:
            deal_address = loaded_json['waiting_address']
            checksum = loaded_json['checksum']
            filename = checksum_files[checksum]

        # outside address
        binding_address = ('127.0.0.1', 7381 + random.randint(0, 30))
        ack_message = {
            "streaming_address": ":".join([str(el) for el in binding_address]),
            "checksum": checksum,
            "file_size": os.path.getsize(filename)
        }
        sock_send(json.dumps(ack_message), deal_address)
        return binding_address, checksum, filename


class Downloader(object):

    def __init__(
            self,
            server_url=None,
            waiting_address=None,
            outside_ip='127.0.0.1',
            inside_ip='0.0.0.0',
            downloads_directory='Downloads',):
        self.server_url = server_url
        self.waiting_address = waiting_address
        self.downloads_directory = downloads_directory

    def get_uploader_addresses(self, checksum):
        url = self.server_url + 'file/' + checksum
        response = requests.get(url)
        addresses = json.loads(response.text)['addresses']
        return addresses

    def choose_peer(self, wanted_checksum, downloader_address):
        """Choose address of client which has wanted checksum"""
        all_addresses = self.get_uploader_addresses(wanted_checksum)
        if downloader_address in all_addresses:
            all_addresses.remove(downloader_address)

        if all_addresses:
            download_address = random.choice(all_addresses)
        else:
            time.sleep(2)
            logger.info("No one has it!")
            logger.info("Checksum: %s..." % wanted_checksum[:6])
            download_address = None
        return download_address

    def request_download(self, download_address, wanted_checksum):

        # outside address
        waiting_udp_ip, waiting_udp_port = self.waiting_address
        waiting_udp_port = int(waiting_udp_port)
        message = {
            "waiting_address": ":".join((waiting_udp_ip,
              str(waiting_udp_port))),
            "checksum": wanted_checksum}

        checksum_request = json.dumps(message)
        sock = sock_bind(self.waiting_address)
        sock_send(checksum_request, download_address)

        json_data, addr = sock.recvfrom(1024)  # buffer size is 1024 bytes
        sock.close()
        payload =  json.loads(json_data)
        peer_uploader_address = payload['streaming_address']
        checksum = payload['checksum']
        file_size = payload['file_size']
        if checksum != wanted_checksum or file_size == 0:
            return None
        else:
            return peer_uploader_address, file_size

    def download_file(self, peer_address, checksum, file_size):
        try:
            time.sleep(0.01)
            sock = sock_connect(peer_address)
            downloaded = 0
            sock.settimeout(4)
            downloaded_file = ""
            if not os.path.exists(self.downloads_directory):
                os.makedirs(self.downloads_directory)
            output_filename = os.path.join(self.downloads_directory, checksum)
            with open(output_filename, 'w') as target_file:
                while (downloaded) < file_size:
                    chunk = sock.recv(CHUNKSIZE)
                    downloaded_file += chunk
                    downloaded += len(chunk)
                    target_file.write(chunk)

            sock.close()
            return downloaded_file[:file_size]
        except:
            import traceback
            logger.warning(traceback.format_exc())
            return ""


def compute_checksum(data):
    return str(sha512(data).hexdigest())
