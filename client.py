import socket
from hashlib import sha512
import os
import argparse
import json



class Client:
    CHECKSUM_STORAGE = '.checksums'
    def __init__(self, directory, server_url):
        self.directory = directory
        self.server_url = server_url
        self.check_sums = self.load_state()
        print(self.check_sums)

    def discover(self):
        def whole_path(base, filename):
            return base + "/" + filename

        return [whole_path(self.directory, filename)
                for filename in (os.listdir(self.directory))
                if os.path.isfile(whole_path(self.directory, filename))]


    def compute_check_sums(self, filenames):
        check_sums = {}
        for filename in filenames:
            with open(filename, 'r') as f:
                file_content = f.read()
                check_sums[str(sha512(file_content).hexdigest())] = filename

        return check_sums

    def load_state(self):
        try:
            with open(self.CHECKSUM_STORAGE, 'r') as f:
                check_sums = json.load(f)
        except IOError:
            check_sums = self.compute_check_sums(self.discover())
            with open(self.CHECKSUM_STORAGE, 'w') as f:
                json.dump(check_sums, f)
        return check_sums




def main(*args, **kwargs):
    parser = argparse.ArgumentParser(description="P2P file sharing client.")
    parser.add_argument("-q", "--quiet", action="store_true")

    parser.add_argument("directory", type=str, help="Directory to serve.")
    parser.add_argument("-s", "--server_url", type=str, default="atte.ro",
                        help="Server to announce files.")
    args = parser.parse_args()

    client = Client(args.directory, args.server_url)
    if args.quiet:
        print(client.discover())
    else:
        print("{} will be announced to {} equals".format(args.directory,
                                                         args.server_url))
        print(args.directory)
        print(client.discover())


if __name__ == '__main__':
    main()
