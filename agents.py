import time
import logging
from socket_helpers import sock_bind, convert_address
from protocol import (
    accept_download_request,
    send_file,
    choose_peer,
    request_download,
    compute_checksum,
    download_file,
)


logger = logging


def dealer_upload(upload_address, checksum_files, upload):
    sock = sock_bind(upload_address)
    while True:
        request = accept_download_request(sock, checksum_files)
        if request:
            sending_address, checksum, filename = request
            upload.put((sending_address, checksum, filename))
    sock.close()


def dealer_download(
        server_url,
        dealer_downloader_address,
        waiting_address,
        wanted_checksums,
        download):
    waiting_ip, last_port = convert_address(waiting_address)

    for wanted_checksum in iter(wanted_checksums.get, 'STOP'):
        try:
            download_address = choose_peer(server_url, wanted_checksum, dealer_downloader_address)
            last_port += 1

            if download_address is None:
                wanted_checksums.put(wanted_checksum)
            new_address = (waiting_ip, last_port)
            response = request_download(new_address, download_address, wanted_checksum)

            if response is not None:
                downloader_address, file_size = response
                download.put((downloader_address, wanted_checksum, file_size))
                wanted_checksums.remove(wanted_checksum)
        except:
            import traceback
            logger.exception(traceback.format_exc())
            time.sleep(1)



def uploader(upload, upload_done):
    for peer_address, checksum, filename in iter(upload.get, 'STOP'):
        try:
            time.sleep(0.2)
            result = send_file(peer_address, filename)
            upload_done.put((checksum, peer_address, result))
            logger.info("Sending done!")
        except:
            import traceback
            logger.info("Sending failure!")
            logger.exception(traceback.format_exc())



def downloader(download, download_done, downloads_directory):
    for peer_address, checksum, file_size in iter(download.get, 'STOP'):
        try:
            downloaded_file = download_file(peer_address, checksum,
                                            file_size, downloads_directory)
            downloaded_checksum = compute_checksum(downloaded_file)
            download_correct = downloaded_checksum == checksum
            download_done.put((checksum, peer_address, download_correct))
        except:
            import traceback
            logger.exception(traceback.format_exc())
            time.sleep(4)
            logger.info("will restart soon...")

