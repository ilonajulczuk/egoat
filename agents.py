import time
import logging
from socket_helpers import sock_bind
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



def downloader(download, download_done):
    for peer_address, checksum, file_size in iter(download.get, 'STOP'):
        while True:
            try:
                downloaded_file = download_file(peer_address, checksum, file_size)
                downloaded_checksum = compute_checksum(downloaded_file)
                download_correct = downloaded_checksum == checksum
                if download_correct:
                    print("correct download")
                    download_done.put((checksum, peer_address, True))
                    break
                else:
                    print("problem")
                    print("Downloaded: %s" % len(downloaded_file))
                    logger.warning("Incorrect download")
            except:
                import traceback
                logger.exception(traceback.format_exc())
                time.sleep(4)
                logger.info("will restart soon...")

