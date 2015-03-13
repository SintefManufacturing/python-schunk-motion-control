import logging

from IPython import embed
from pg.pgcontroller import PGController

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    p = PGController()
    p.setup_tcp(("192.168.0.211", 10001))
    try:
        p.get_state()
        #p.setRef()
        #p.recvPacket()
        #p.recvPacket()
        #p.recvPacket()
        embed()
    finally:
        p.close()
