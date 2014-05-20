from hashlib import sha512
import json
import logging
import os
import random
import requests
import socket
import time


from socket_helpers import (
    sock_send,
    create_socket,
    sock_bind,
    sock_connect,
    convert_address,
)

CHUNKSIZE = 512

logger = logging


def compute_checksum(data):
    """Compute sha512 hexdigest of binary string.

    :param data: binary string
    :return: hexdigest string
    """
    return str(sha512(data).hexdigest())


class Uploader(object):

    def __init__(self, outside_ip='127.0.0.1', inside_ip='0.0.0.0', port=6666):
        """

        :param outside_ip: will be passed to peer to use in p2p communication
        :param inside_ip: will be used internally to bind sockets
        :param port: port to listen for uploading requests
        """
        self.port = port
        self.outside_ip = outside_ip
        self.inside_ip = inside_ip

    @staticmethod
    def stream_file(binding_address, filename):
        """Stream file `filename` on binding_address.

        :param binding_address: address which will be used to bind streaming socket
        :param filename:
        :return:
        """
        sock = create_socket(socktype="tcp")
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(convert_address(binding_address))
        logger.info("starting listening!")
        sock.listen(5)
        comm_sock, _ = sock.accept()
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

    def accept_download_request(self, checksum_files):
        """Accept download requests for given checksum_files.

        :param checksum_files: mapping between checksums and names of files
        :return: streaming_address, accepted_checksum and filename
        """
        address = (self.inside_ip, self.port)
        sock = sock_bind(address)
        message, _ = sock.recvfrom(1024)

        sock.close()
        loaded_json = json.loads(message)
        deal_address = loaded_json['waiting_address']
        checksum = loaded_json['checksum']
        filename = checksum_files[checksum]

        binding_port = 7381

        # notice difference between outside and inside addresses
        outside_binding_address = (self.outside_ip, binding_port)

        inside_binding_address = (self.inside_ip, binding_port)
        ack_message = {
            "streaming_address": ":".join([str(el) for el in outside_binding_address]),
            "checksum": checksum,
            "file_size": os.path.getsize(filename)
        }
        sock_send(json.dumps(ack_message), deal_address)
        return inside_binding_address, checksum, filename


class Downloader(object):

    def __init__(
            self,
            server_url=None,
            downloader_port=None,
            outside_ip='127.0.0.1',
            inside_ip='0.0.0.0',
            downloads_directory='Downloads'):

        self.server_url = server_url
        self.outside_ip = outside_ip
        self.inside_ip = inside_ip
        self.downloader_port = downloader_port
        self.downloads_directory = downloads_directory

    def get_uploader_addresses(self, checksum):
        url = self.server_url + 'file/' + checksum
        response = requests.get(url)
        addresses = json.loads(response.text)['addresses']
        return addresses

    def choose_peer(self, wanted_checksum):
        """Choose address of client which has wanted checksum"""
        all_addresses = self.get_uploader_addresses(wanted_checksum)

        if all_addresses:
            download_address = random.choice(all_addresses)
        else:
            time.sleep(2)
            logger.info("No one has it!")
            logger.info("Checksum: %s..." % wanted_checksum[:6])
            download_address = None
        return download_address

    def request_download(self, download_address, wanted_checksum):
        message = {
            "waiting_address": ":".join((self.outside_ip,
            str(self.downloader_port))),
            "checksum": wanted_checksum}

        downloader_address = ":".join((self.inside_ip,
                                      str(self.downloader_port)))

        checksum_request = json.dumps(message)
        sock = sock_bind(downloader_address)
        sock_send(checksum_request, download_address)

        json_data, _ = sock.recvfrom(1024)
        sock.close()
        payload = json.loads(json_data)
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
                while downloaded < file_size:
                    chunk = sock.recv(CHUNKSIZE)
                    downloaded_file += chunk
                    downloaded += len(chunk)
                    target_file.write(chunk)

            sock.close()
            return downloaded_file[:file_size]
        except socket.error:
            import traceback
            logger.exception(traceback.format_exc())
            return ""
