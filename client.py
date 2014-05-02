import requests
from hashlib import sha512
import os
import argparse
import time
import json



class Client:
    CHECKSUM_STORAGE = '.checksums'
    def __init__(self, directory, server_url, address):
        self.directory = directory
        self.server_url = server_url
        self.address = address
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
            storage_filename = self.CHECKSUM_STORAGE + str(sha512(self.directory).hexdigest())
            with open(storage_filename, 'r') as f:
                check_sums = json.load(f)
        except IOError:
            check_sums = self.compute_check_sums(self.discover())
            with open(storage_filename, 'w') as f:
                json.dump(check_sums, f)
        return check_sums

    def announce(self):
        requests.post(self.server_url,
                      params={'checksum_files': json.dumps(self.check_sums),
                     'address': self.address})




def main(*args, **kwargs):
    parser = argparse.ArgumentParser(description="P2P file sharing client.")
    parser.add_argument("-q", "--quiet", action="store_true")

    parser.add_argument("directory", type=str, help="Directory to serve.")
    parser.add_argument("address", type=str, help="Addres to serve on.")
    parser.add_argument("-s", "--server_url", type=str, default="atte.ro",
                        help="Server to announce files.")
    args = parser.parse_args()

    client = Client(args.directory, args.server_url, args.address)
    if args.quiet:
        print(client.discover())
    else:
        print("{} will be announced to {} equals".format(args.directory,
                                                         args.server_url))
        print(args.directory)
        print(client.discover())
    while True:
        time.sleep(2)
        print("announcing!")
        client.announce()


if __name__ == '__main__':
    main()
