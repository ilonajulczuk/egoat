import argparse
import logging

from client import Client

LOG_FILENAME = "egoat.log"


def handle_input_args():
    """Defines command line arguments and provide help.

    :return: parsed arguments set as attributes on args object.
    """
    parser = argparse.ArgumentParser(description="P2P file sharing client.")
    parser.add_argument("-q", "--quiet", action="store_true")

    parser.add_argument("directory", type=str, help="Directory to serve.")
    parser.add_argument("address", type=str, help="Address to serve on.")
    parser.add_argument("-s", "--server_url", type=str, default="http://127.0.0.1:5000/",
                        help="Server to announce files.")
    parser.add_argument("-c", "--checksum", type=str, default=None,
                        help="Checksum of file you want to download")
    parser.add_argument("-l", "--logging_filename", type=str, default=LOG_FILENAME,
                        help="File in which you would like to store logs")
    parser.add_argument(
        "-f",
        "--checksum_file",
        type=str,
        default=None,
        help="List with stored checksums of files you want to download")
    parser.add_argument("-p", "--port", type=str, default=None,
                        help="Port to wait for coming requests")
    parser.add_argument(
        "-d",
        "--downloads_directory",
        type=str,
        default='Downloads',
        help="Directory to store downloads")
    return parser.parse_args()


def main():
    args = handle_input_args()
    port = args.port
    client = Client(args.directory, args.server_url, args.address,
                    port, args.downloads_directory)

    wanted_checksums = []
    if args.checksum:
        wanted_checksums.append(args.checksum)
    elif args.checksum_file:
        with open(args.checksum_file) as file_with_list_of_downloads:
            for line in file_with_list_of_downloads.readlines():
                wanted_checksums.append(line.strip())

    if args.quiet:
        pass
    else:
        logging.basicConfig(filename=args.logging_filename, level=logging.INFO)
    client.announce()
    client.serve(wanted_checksums)


if __name__ == '__main__':
    main()