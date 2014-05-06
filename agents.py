import time
import logging
from socket_helpers import sock_bind, convert_address
from protocol import Downloader, Uploader, compute_checksum


logger = logging


def dealer_upload(upload_address, checksum_files, upload):
    sock = sock_bind(upload_address)
    uploader = Uploader()
    while True:
        request = uploader.accept_download_request(sock, checksum_files)
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

    downloader = Downloader(server_url, waiting_address=waiting_address)
    for wanted_checksum in iter(wanted_checksums.get, 'STOP'):
        try:
            download_address = downloader.choose_peer(wanted_checksum, dealer_downloader_address)
            last_port += 1

            if download_address is None:
                wanted_checksums.put(wanted_checksum)
            response = downloader.request_download(download_address, wanted_checksum)
            if response is not None:
                peer_uploader_address, file_size = response
                download.put((peer_uploader_address, wanted_checksum, file_size))
        except:
            import traceback
            logger.exception(traceback.format_exc())
            time.sleep(1)



def uploader(upload, upload_done):
    uploader = Uploader()
    for peer_address, checksum, filename in iter(upload.get, 'STOP'):
        try:
            result = uploader.stream_file(peer_address, filename)
            upload_done.put((checksum, peer_address, result))
            logger.info("Sending done!")
        except:
            import traceback
            logger.info("Sending failure!")
            logger.exception(traceback.format_exc())



def downloader(download, download_done, downloads_directory):
    downloader = Downloader(downloads_directory=downloads_directory)
    for peer_address, checksum, file_size in iter(download.get, 'STOP'):
        try:
            downloaded_file = downloader.download_file(peer_address, checksum,
                                            file_size)
            downloaded_checksum = compute_checksum(downloaded_file)
            download_correct = downloaded_checksum == checksum
            download_done.put((checksum, peer_address, download_correct))
        except:
            import traceback
            logger.exception(traceback.format_exc())
            time.sleep(4)
            logger.info("will restart soon...")

