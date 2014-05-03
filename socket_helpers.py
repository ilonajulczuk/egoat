import socket


def sock_send(payload, address, sock=None):
    if sock is None:
        sock = socket.socket(socket.AF_INET,  # Internet
                             socket.SOCK_DGRAM)  # UDP
    udp_ip, udp_port = convert_address(address)
    sock.sendto(payload, (udp_ip, udp_port))


def create_socket():
    return socket.socket(socket.AF_INET,  # Internet
                         socket.SOCK_DGRAM)  # UDP

def sock_bind(address):
    udp_ip, udp_port = convert_address(address)
    sock = create_socket()
    sock.bind((udp_ip, udp_port))
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
