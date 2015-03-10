import logging
import socket
import threading
import struct
import time

import crcmod

class PGTCP(object):
    """
    Serial connection over TCP bridge (tested with landtronix)
    """
    def __init__(self, ipport, timeout):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.crc16 = crcmod.mkCrcFun(0x18005, 0x0000, True) 
        self._lock = threading.Lock()
        self._sock = socket.create_connection(ipport, timeout=2)
        #self._sock.setblocking(False)
        self.logger.info(' %s is open', self._sock.getsockname())
        self._queue = b""
        self.timeout = timeout

    def recv_packet(self):
        """
        block until a package is received from gripper
        raise a timeout depending on socket setup(class argument)
        """
        with self._lock:
            start = time.time()
            while True:
                if time.time() - start > self.timeout:
                    raise socket.timeout("timed out")# reraise the timeout which should have happend
                try:
                    data = self._sock.recv(1024) #this may raise an exception (timeout for eks)
                except socket.timeout as ex:
                    data = b""
                self._queue += data
                #self.logger.info("length of queue is: ", len(self._queue))
                #now check if we have a good packet in that data
                if not self._queue:
                    continue
                pack = self._find_packet(self._queue[:])
                if pack:
                    self._queue = pack[2]
                    return pack[0], pack[1]

    def _find_packet(self, data):
        self.logger.debug("Looking for packet in %s", data)
        while len(data) >= 6: # must at leat be ID, len , cmd and CRC
            self.logger.debug("ID is %s", data[2:])
            print(data[2], type(data[2]))
            #dLen = struct.unpack('<B', data[2])[0]
            expectedLength = 2 + 1 + data[2] + 2
            self.logger.info("expected Length: %s", expectedLength)
            if len(data) >= expectedLength:
                packet = data[:expectedLength]
                rest = data[expectedLength:] 
                chcSum = int(self.crc16(packet[:-2]))
                if  chcSum == struct.unpack('H', packet[-2:])[0]:
                    #this is a good packet
                    #cmd = struct.unpack('<B', packet[3])[0]
                    cmd = packet[3]
                    data = packet[4:-2] 
                    return (cmd, data, rest)
            #self.logger.info( "No packet here, trying to remove first byte")
            data = data[1:]
        return None
 


    def send_raw(self, data):
        with self._lock:
            self.logger.debug("Sending: %s", data)
            self._sock.send(data)

    def send_packet(self, cmd, data=""):
        """format packet and send it"""
        self.send_raw(self._format(cmd, data))

    def cleanup(self):
        if self._sock:
            self._sock.close()


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


