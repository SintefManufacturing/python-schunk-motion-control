import logging

from IPython import embed
from pg.pgcontroller import PGController

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    p = PGController()
    state = p.setup_serial("/dev/ttyUSB0")
    try:
        print(state)
        #p.setRef()
        #p.recvPacket()
        #p.recvPacket()
        #p.recvPacket()
        embed()
    finally:
        p.close()
