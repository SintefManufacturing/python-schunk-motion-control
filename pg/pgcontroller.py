import logging
import struct

import crcmod

from pg.pg_tcp import PGTCP
from pg.pg_serial import PGSerial


logger = logging.getLogger("PGController")

class PGController(object):
    def __init__(self):
        self._dev = None
        self.crc16 = crcmod.mkCrcFun(0x18005, 0x0000, True) 
        self._queue = b""

    def setup_serial(self, dev, timeout):
        self._dev = PGSerial(dev, timeout)

    def setup_tcp(self, ipport, timeout):
        self._dev = PGTCP(ipport, timeout)
        #state = self.get_state()
        #if state.state["Error"] != 0:
            #self.quit_error()

    def parse_answer(self, cmd, data):
        if cmd == 0x95: #this is state packet
            return State(cmd, data)
        elif cmd == 0x93: # 
            return PosObstructed(cmd, data)
        elif cmd == 0x94:
            return PosCompleted(cmd, data)
        elif cmd == 0x80: # config data
            return Config(cmd, data)
        elif cmd == 0xB0: 
            return PosCmd(cmd, data)
        elif cmd == 0x92:
            return RefCmd(cmd, data)
        elif cmd == 0x88: # cmd error, ths must be acknowledge with quit_error 
            return CmdError(cmd, data)
        elif cmd == 0x8b: # acknoeldge error
            return CmdAck(cmd, data)
        else:
            logger.warn("command %s not supported yet", cmd)
            return Answer(cmd, data)

    def cleanup(self):
        if self._dev:
            self._dev.cleanup()
    
    def recv_packet(self):
        cmd, data = self._recv()
        ans = self.parse_answer(cmd, data)
        logger.debug("received answer: %s", ans)
        return ans


    def quit_error(self):
        """
        This is necessary if a cmd error has occured
        """
        ans = self._send(b'\x8b')
        if type(ans) is CmdAck: 
            logger.info("Slave acknowleged error")
            return True
        else:
            logger.warn("Slave did not acknowleged error")
            return False

    def _format(self, cmd, data=b""):
        b = [] 
        b.append(b'\x05\x0C')
        dlen = struct.pack('B', len(data) + len(cmd))
        b.append(dlen)
        b.append(cmd)
        b.append(data)
        b = b"".join(b)
        chcSum = int(self.crc16(b))
        return b + struct.pack('H', chcSum) + b"\n"

    def _recv(self):
        logger.debug("reading 3 bytes")
        data = self._dev.recv(3)
        logger.debug("reading %s bytes", data[2])
        data += self._dev.recv(data[2] + 2)
        chcSum = int(self.crc16(data[:-2]))
        if  chcSum != struct.unpack('H', data[-2:])[0]:
            raise Exception("Wrong crc16")
        #this is a good packet
        #cmd = struct.unpack('<B', packet[3])[0]
        cmd = data[3]
        data = data[4:-2] 
        return cmd, data

    def _send(self, cmd, data=b""):
        string = self._format(cmd, data)
        self._dev.send(string)
        while True:
            ans = self.recv_packet()
            if ans.cmd == ord(cmd):
                return ans

    def get_config(self):
        return self._send(b'\x80', b'\xFE')
    
    def get_state(self):
        return self._send(b'\x95', b'\x00\x00\x00\x00\x00')

        
    def set_ref(self):
        return self._send(b'\x92')
                
    def set_pos(self, pos, vel=50.0, acc=50, current=1):
        """
        set position
        another package will be send when the position is reached
        """
        data = struct.pack('<4f', pos, vel, acc, current)
        return self._send(b'\xB0', data)
        
    def estop(self):
        return self._send(b'\x90')




def test_bit(int_type, offset):
    mask = 1 << offset
    return int_type & mask



class Answer(object):
    def __init__(self, cmd, data):
        self.cmd = cmd
        #self.cmdint = struct.unpack('<B', cmd)
        self.data = data


class State(Answer):
    def __init__(self, cmd, data):
        Answer.__init__(self, cmd, data)
        self.state = dict(Referenced=0, Moving=0, ProgramMode=0, Warning=0, Error=0, Brake=0, MoveEnd=0, PositionReached=0, ErrorCode=0)
        if len(data) != 2:
            logger.warn("Error, a state packet should be of length 2")
        else:
            #val = struct.unpack("<B", data[0])[0]
            val = data[0]
            if test_bit(val, 0):
                self.state["Referenced"] = 1
            if test_bit(val, 1):
                self.state["Moving"] = 1
            if test_bit(val, 2):
                self.state["ProgramMode"] = 1
            if test_bit(val, 3):
                self.state["Warning"] = 1
            if test_bit(val, 4):
                self.state["Error"] = 1
            if test_bit(val, 5):
                self.state["Brake"] = 1
            if test_bit(val, 6):
                self.state["MoveEnd"] = 1
            if test_bit(val, 7):
                self.state["PositionReached"] = 1
            self.state["ErrorCode"] = data[1] 

    def __str__(self):
        return self.__class__.__name__ + str(self.state)

class PosCompleted(Answer):
    def __init__(self, cmd, data):
        Answer.__init__(self, cmd, data)
        self.pos = struct.unpack("<f", data)[0]

class PosObstructed(Answer):
    def __init__(self, cmd, data):
        Answer.__init__(self, cmd, data)
        self.data = data
        self.pos = struct.unpack("<f", data)[0]

class PosCmd(Answer):
    def __init__(self, cmd, data):
        Answer.__init__(self, cmd, data)


class RefCmd(Answer):
    def __init__(self, cmd, data):
        Answer.__init__(self, cmd, data)

class CmdAck(Answer):
    def __init__(self, cmd, data):
        Answer.__init__(self, cmd, data)

class Config(Answer):
    def __init__(self, cmd, data):
        Answer.__init__(self, cmd, data)
        # PG getConfig not  implemented yet"

class CmdError(Answer):
    def __init__(self, cmd, data):
        Answer.__init__(self, cmd, data)
        self.errorcode = data

 
