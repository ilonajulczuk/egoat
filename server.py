from flask import Flask
import json
import redis
from flask import render_template, request

DEBUG = True
app = Flask(__name__)
app.config.from_object(__name__)

REDIS_LIST = 'egoat::sharers::'
TIMEOUT = 100


def load_data():
    rclient = redis.Redis()
    announcements = {}
    announcement_keys = rclient.keys(REDIS_LIST + "*")
    for key in announcement_keys:
        json_announcement = rclient.get(key)
        address = key.split("::")[-1]
        announcements[address] = json.loads(json_announcement)
    return announcements


def add_announcement(address, checksum_files):
    announcement = checksum_files
    json_announcement = json.dumps(announcement)
    rclient = redis.Redis()
    rclient.setex(REDIS_LIST + address, json_announcement, TIMEOUT)


@app.route('/')
def hello_world():
    data = load_data()
    print(data)
    return render_template('index.html', announcements=data)


@app.route('/file/', methods=['GET'])
@app.route('/file/<file_hash>', methods=['GET'])
def get_file(file_hash=None):
    print(file_hash)
    if file_hash:
        return json.dumps(["127.0.0.1"])
    else:
        return json.dumps(["121", "124", "132"])


@app.route('/hello/', methods=['POST'])
def announce_files():
    checksum_files = json.loads(request.args['checksum_files'])
    address = request.args['address']
    add_announcement(address, checksum_files)

    print("Got new data!")
    return "OK"


if __name__ == '__main__':
    app.run()
