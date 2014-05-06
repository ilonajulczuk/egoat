import socket


SOCK_CONFIG = {
    'tcp': (socket.AF_INET, socket.SOCK_STREAM),
    'udp': (socket.AF_INET, socket.SOCK_DGRAM),
}


def sock_send(payload, address, sock=None, socktype="udp"):
    if sock is None:
        sock = create_socket(socktype)
    udp_ip, udp_port = convert_address(address)
    sock.sendto(payload, (udp_ip, udp_port))


def create_socket(socktype='udp'):
    return socket.socket(*SOCK_CONFIG[socktype])


def sock_connect(address):
    server_ip, server_port = convert_address(address)
    sock = create_socket("tcp")
    sock.connect((server_ip, server_port))
    return sock


def sock_bind(address):
    waiting_ip, waiting_port = convert_address(address)
    sock = create_socket()
    sock.bind((waiting_ip, waiting_port))
    return sock


def convert_address(address):
    if isinstance(address, (unicode, str)):
        udp_ip, udp_port = address.split(":")
    elif len(address) == 2:
        udp_ip, udp_port = address
    else:
        raise ValueError("Wrong address for a socket!")
    udp_port = int(udp_port)
    return udp_ip, udp_port
