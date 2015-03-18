import time
import logging
import struct
from threading import Thread, Condition

import crcmod

from pg.pg_tcp import PGTCP
from pg.pg_serial import PGSerial


logger = logging.getLogger("PGController")

class CmdLock(object):#FIXME: bad name
    def __init__(self):
        self.cond = Condition()
        self.data = b''

class CmdConditions(object):#FIXME: bad name
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self._conds = {}

    def wait_for(self, cmd):
        self.logger.debug("waiting for %s", cmd)
        cmdlock = self._get_cond(cmd)
        with cmdlock.cond:
            cmdlock.cond.wait() 
            self.logger.debug("wait finished for %s, returning data", cmd)
            return cmdlock.data

    def notify(self, cmd, data):
        cmdlock = self._get_cond(cmd)
        with cmdlock.cond:
            self.logger.debug("received data for cmd %s, notify all listeners", cmd)
            cmdlock.data = data
            cmdlock.cond.notify_all() 

    def _get_cond(self, cmd):
        if type(cmd) == int:
            cmd = struct.pack("B", cmd)
        if not cmd in self._conds:
            self._conds[cmd] = CmdLock() 
        return self._conds[cmd]
    
    def wake_all(self):
        for cond in self._conds.values():
            with cond.cond:
                cond.cond.notify_all()


class PGController(Thread):
    def __init__(self):
        Thread.__init__(self)
        self._dev = None
        self.crc16 = crcmod.mkCrcFun(0x18005, 0x0000, True) 
        self._queue = b""
        self._cmdcond = CmdConditions()
        self._stopev = False

    def run(self):
        while not self._stopev:
            cmd, data = self._recv()
            ans = self.parse_answer(cmd, data)
            logger.debug("received answer: %s", ans)
            self._cmdcond.notify(cmd, ans)
        logger.debug("Receiving thread ended")

    def close(self):
        self._stopev = True
        self.stop_async()
        time.sleep(0.5)# let our dev send the message before we close
        self._dev.stop()
        #self._cmdcond.wake_all()

    def setup_serial(self, dev):
        self._dev = PGSerial(dev)
        self.start()

    def setup_tcp(self, ipport):
        self._dev = PGTCP(ipport)
        self.start()

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
        elif cmd == 0x91:
            return StopCmd(cmd, data)
        elif cmd == 0x88: # cmd error, ths must be acknowledge with quit_error 
            return CmdError(cmd, data)
        elif cmd == 0x8b: # acknoeldge error
            return CmdAck(cmd, data)
        elif cmd == 0xb7: 
            return GripCmd(cmd, data)
        elif cmd == 0x8a: 
            return CmdInfo(cmd, data)
        else:
            logger.warn("command %s not supported yet", cmd)
            return Answer(cmd, data)

    def ack(self):
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
        cmd = data[3]
        data = data[4:-2] 
        return cmd, data

    def _send(self, cmd, data=b""):
        string = self._format(cmd, data)
        self._dev.send(string)
        return self._cmdcond.wait_for(cmd)

    def _send_async(self, cmd, data=b""):
        string = self._format(cmd, data)
        self._dev.send(string)

    def get_config(self):
        return self._send(b'\x80', b'\xFE')
    
    def get_state(self):
        data = struct.pack('<fB', 0.0, 0x01 | 0x02 | 0x04)
        return self._send(b'\x95', data)

        
    def set_ref(self):
        return self._send(b'\x92')
                
    def move_pos(self, pos, vel=30.0, acc=50, current=1):
        """
        set position, return immediatly
        """
        data = struct.pack('<4f', pos, vel, acc, current)
        return self._send(b'\xB0', data)

    def move_pos_blocking(self, pos, vel=30.0, acc=50, current=1):
        """
        set position
        return when move has finished
        """
        data = struct.pack('<4f', pos, vel, acc, current)
        self._send_async(b'\xB0', data)
        return self._cmdcond.wait_for(b'\x94')

    def move_grip_blocking(self, current=-0.6, maxvel=30.0):
        """
        grip until current reached (sign of current is direction)
        return when move has finished
        """
        data = struct.pack('<2f', current, maxvel)
        self._send_async(b'\xB7', data)
        return self._cmdcond.wait_for(b'\x93')

    def move_grip(self, current=-0.6, maxvel=50.0):
        """
        grip until current reached (sign of current is direction)
        returns immediatly 
        """
        data = struct.pack('<2f', current, maxvel)
        return self._send(b'\xB7', data)
 


    def stop(self):
        return self._send(b'\x91')

    def estop(self):
        return self._send(b'\x90')


    def stop_async(self):
        self._send_async(b'\x91')




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
        self.pos, self.vel, self.current, self.status, self.error = struct.unpack("3fBB", self.data)
        if test_bit(self.status, 0):
            self.state["Referenced"] = 1
        if test_bit(self.status, 1):
            self.state["Moving"] = 1
        if test_bit(self.status, 2):
            self.state["ProgramMode"] = 1
        if test_bit(self.status, 3):
            self.state["Warning"] = 1
        if test_bit(self.status, 4):
            self.state["Error"] = 1
        if test_bit(self.status, 5):
            self.state["Brake"] = 1
        if test_bit(self.status, 6):
            self.state["MoveEnd"] = 1
        if test_bit(self.status, 7):
            self.state["PositionReached"] = 1
        self.errormsg = error_codes[self.error] 

    def __str__(self):
        return "State(pos:{}, vel:{}, current:{}, state:{}, errorcode:{}, errormsg:{})".format(self.pos, self.vel, self.current, self.state, self.error, self.errormsg)
    __repr__ = __str__

class PosCompleted(Answer):
    def __init__(self, cmd, data):
        Answer.__init__(self, cmd, data)
        self.pos = struct.unpack("<f", data)[0]

    def __str__(self):
        return "PosCompleted: {}mm".format(self.pos)
    __repr__ = __str__

class PosObstructed(Answer):
    def __init__(self, cmd, data):
        Answer.__init__(self, cmd, data)
        self.data = data
        self.pos = struct.unpack("<f", data)[0]
    def __str__(self):
        return "PosObstructed: {}mm".format(self.pos)
    __repr__ = __str__

class PosCmd(Answer):
    def __init__(self, cmd, data):
        Answer.__init__(self, cmd, data)
        self.time = struct.unpack("<f", data)[0]
    def __str__(self):
        return "PosCmd: completed in {}s".format(self.time)
    __repr__ = __str__



class RefCmd(Answer):
    pass

class CmdAck(Answer):
    pass

class StopCmd(Answer):
    pass

class Config(Answer):
    pass

class GripCmd(Answer):
    pass

class CmdError(Answer):
    def __init__(self, cmd, data):
        Answer.__init__(self, cmd, data)
        self.errorcode = data
        i = struct.unpack("B", data)[0]
        if i in error_codes:
            self.errormsg = error_codes[struct.unpack("B", data)[0]]
        else:
            self.errormsg = "Unknown"
    def __str__(self):
        return "CmdError: {}, {}".format(self.errorcode, self.errormsg)
    __repr__ = __str__


class CmdInfo(Answer):
    pass



# from https://pypi.python.org/pypi/SchunkMotionProtocol/
error_codes = {
    0x00: "NO ERROR",  # not in Schunk manual; added for convenience
    0x01: "INFO BOOT",
    0x02: "INFO NO FREE SPACE",
    0x03: "INFO NO RIGHTS",
    0x04: "INFO UNKNOWN COMMAND",
    0x05: "INFO FAILED",
    0x06: "NOT REFERENCED",
    0x07: "INFO SEARCH SINE VECTOR",
    0x08: "INFO NO ERROR",
    0x09: "INFO COMMUNICATION ERROR",
    0x10: "INFO TIMEOUT",
    0x16: "INFO WRONG BAUDRATE",
    0x19: "INFO CHECKSUM",
    0x1D: "INFO MESSAGE LENGTH",
    0x1E: "INFO WRONG PARAMETER",
    0x1F: "INFO PROGRAM END",
    0x40: "INFO TRIGGER",
    0x41: "INFO READY",
    0x42: "INFO GUI CONNECTED",
    0x43: "INFO GUI DISCONNECTED",
    0x44: "INFO PROGRAM CHANGED",
    0xC8: "ERROR WRONG RAMP TYPE",
    0xD2: "ERROR CONFIG MEMORY",
    0xD3: "ERROR PROGRAM MEMORY",
    0xD4: "ERROR INVALID PHRASE",
    0xD5: "ERROR SOFT LOW",
    0xD6: "ERROR SOFT HIGH",
    0xD7: "ERROR PRESSURE",
    0xD8: "ERROR SERVICE",
    0xD9: "ERROR EMERGENCY STOP",
    0xDA: "ERROR TOW",
    0xE4: "ERROR TOO FAST",
    0xEC: "ERROR MATH",
    0xDB: "ERROR VPC3",
    0xDC: "ERROR FRAGMENTATION",
    0xDD: "ERROR COMMUTATION",
    0xDE: "ERROR CURRENT",
    0xDF: "ERROR I2T",
    0xE0: "ERROR INITIALIZE",
    0xE1: "ERROR INTERNAL",
    0xE2: "ERROR HARD LOW",
    0xE3: "ERROR HARD HIGH",
    0x70: "ERROR TEMP LOW",
    0x71: "ERROR TEMP HIGH",
    0x72: "ERROR LOGIC LOW",
    0x73: "ERROR LOGIC HIGH",
    0x74: "ERROR MOTOR VOLTAGE LOW",
    0x75: "ERROR MOTOR VOLTAGE HIGH",
    0x76: "ERROR CABLE BREAK",
    0x78: "ERROR MOTOR TEMP",
}

