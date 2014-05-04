from nose import tools as nt
from multiprocessing import Process
from protocol import(
    send_file,
    compute_checksum,
    download_file,
)
import os


def test_sending_file():
    sending_address = "127.0.0.1:6666"

    filenames = [
        'test_files/short_file.txt',
        'test_files/short_file.txt',
        'test_files/file_for_upload.txt',
        'test_files/goat.jpg',
    ]

    for filename in filenames:
        with open(filename) as f:
            file_content = f.read()
        checksum = compute_checksum(file_content)

        file_size = os.path.getsize(filename)
        Process(target=send_file, args=(sending_address, filename)).start()
        downloaded_file = download_file(sending_address, checksum,
                                        file_size, 'test_results')

        new_checksum = compute_checksum(downloaded_file)
        nt.eq_(len(file_content.split('\n')), len(downloaded_file.split('\n')))
        nt.eq_(new_checksum, checksum)

