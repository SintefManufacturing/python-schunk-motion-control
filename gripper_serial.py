import logging

from IPython import embed
from pg.pgcontroller import PGController

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    p = PGController()
    state = p.setup_serial("/dev/ttyUSB0", timeout=5) #timeout is the max time it should take to close or open the gripper
    print(state)
    #p.setRef()
    #p.recvPacket()
    #p.recvPacket()
    #p.recvPacket()
    embed()
