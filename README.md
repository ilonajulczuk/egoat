[![Build Status](https://drone.io/github.com/atteroTheGreatest/egoat/status.png)](https://drone.io/github.com/atteroTheGreatest/egoat/latest)

#EGOAT - your new p2p client

Amazingly fast p2p client and server.

Project includes:

 - tracker server is written in python and [flask](http://flask.pocoo.org/) using [redis](http://redis.io/)
 - python client
 - golang client

#Server API

 - `/hello`:
    - announce your existence and checksum and filenames you have
        - `address`
        - `checksum_files` mapping
 - `/file/wanted_checksum`
    - return json of `addresses` of peer which have `wanted_checksum`


#Client to client communication

 - client client negotiation runs over `UDP`
 - client client file streaming uses `TCP`


#Installation

##Python client and server

1. Make sure that you have python, pip and virtualenv installed

- python is installed by default on linux distros
- pip can be installed by `apt-get install python-pip`
- virtualenv can be installed by `apt-get install python-virtualenv`

2. Create env

`virtualenv env`

3. Activate env

`source env/bin/activate`

4. With pip installed and virtual environment activated you can install requirements

`pip install -r requirements.txt`

5. To run egoat server you need redis key-value store.

- `apt-get install redis-server`
- `redis-server &`

##Running

```
$ python egoat_client.py /home/att/Pictures 7878 -p 7871
```

or

```
$ python egoat_client.py -c 1d47390dd45c675f723e39cd1fd215ed883f6df17a1019ce6d7585db6c618f81bc9c779ec8f3b1eec09e2c4e02edc2fc9332734ae1e8b009ba5798da2a8a112b /home/att/Workouts 9999 -p 7899
```

Example output:

```
Downloaded: 1d47390dd45c675f723e39cd1fd215ed883f6df17a1019ce6d7585db6c618f81bc9c779ec8f3b1eec09e2c4e02edc2fc9332734ae1e8b009ba5798da2a8a112b 127.0.0.1:7381 True
```


#TODO:

- test with bad peers (not really having a file or whatever)
    - blacklisting?
- add gui interface
    - what now?> with commands
    - something more elaborate as for example
        - ncurses
        - python clik
    - must have colors
- better management of  socket addresses
    - it would be nice if it was configurable, etc


