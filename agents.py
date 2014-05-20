import time
import logging
from protocol import Downloader, Uploader, compute_checksum


logger = logging


def accept_upload_requests(uploader_helper, checksum_files, upload_queue):
    """Listen using uploader_helper and put accepted requests on upload queue.

    :param uploader_helper: helper implementing `accept_download_requests(checksum_files)`
    :param checksum_files: mapping between checksums - strings and file_names
    :param upload_queue: queue to put accepted requests in
    form `(sending_address, checksum, filename)`
    """
    while True:
        request = uploader_helper.accept_download_request(checksum_files)
        if request:
            sending_address, checksum, filename = request
            upload_queue.put((sending_address, checksum, filename))


def request_uploads(
        downloader_helper,
        wanted_checksums,
        download_queue):

    """Request uploads of wanted checksums and if agreed put in on download_queue.

    :param downloader_helper: helper to choose peer and request downloading
    :param wanted_checksums:
    :param download_queue:

    Will choose peer communicating using a tracker server.
    """
    for wanted_checksum in iter(wanted_checksums.get, 'STOP'):
        try:
            download_address = downloader_helper.choose_peer(
                wanted_checksum)
            if download_address is None:
                wanted_checksums.put(wanted_checksum)
                time.sleep(1)
                continue

            response = downloader_helper.request_download(
                download_address,
                wanted_checksum)
            if response is not None:
                selected_streaming_binding_address, file_size = response
                download_queue.put(
                    (selected_streaming_binding_address,
                     wanted_checksum,
                     file_size))
        except:
            import traceback
            logger.exception(traceback.format_exc())
            time.sleep(1)


def uploader(to_upload_queue, upload_done_queue):
    """Upload files using and put upload results on queue.

    :param to_upload_queue: queue with streaming specifications:
        binding_address on which streaming server socket would stream,
        checksum of file to stream,
        filename of file to stream,
    :param upload_done_queue: queue to put download results in form (checksum, success)
    """
    uploader_helper = Uploader()
    for binding_address, checksum, filename in iter(to_upload_queue.get, 'STOP'):
        try:
            result = uploader_helper.stream_file(binding_address, filename)
            upload_done_queue.put((checksum, binding_address, result))
            logger.info("Sending done!")
        except:
            import traceback
            logger.info("Sending failure!")
            logger.exception(traceback.format_exc())


def downloader(to_download_queue, download_done_queue, downloads_directory):
    """Download files from queue and put results on download_done_queue.

    :param to_download_queue: queue with downloads specifications:
        peer_address which will stream file
        checksum of file to assure if file was downloaded correctly
        file_size of file
    :param download_done_queue: queue to put download results
    :param downloads_directory: place to save downloaded files
    """
    uploader_helper = Downloader(downloads_directory=downloads_directory)
    for peer_address, checksum, file_size in iter(to_download_queue.get, 'STOP'):
        try:
            downloaded_file = uploader_helper.download_file(peer_address, checksum,
                                                            file_size)
            downloaded_checksum = compute_checksum(downloaded_file)
            download_correct = downloaded_checksum == checksum
            download_done_queue.put((checksum, peer_address, download_correct))
        except:
            import traceback
            logger.exception(traceback.format_exc())
            time.sleep(4)
            logger.info("will restart soon...")
