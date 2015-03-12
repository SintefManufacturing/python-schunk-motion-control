import logging

from IPython import embed
from pg.pgcontroller import PGController

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    p = PGController()
    state = p.setup_tcp(("192.168.0.211", 10001), timeout=9999) #timeout is the max time it should take to close or open the gripper
    print(state)
    #p.setRef()
    #p.recvPacket()
    #p.recvPacket()
    #p.recvPacket()
    embed()
