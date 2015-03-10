import struct
import threading


class PGSerial(object):
    """
    BROKEN!!!!!!!!!!!!!!!!
    """
    def __init__(self, comPort, timeout=16):
        self._lock = threading.Lock()
        self._ser = serial.Serial(comPort, 9600)
        self._ser.setTimeout(timeout)
        self._ser.flush()
        self.log( self._ser.portstr , ' is open')

    def recvPackage(self):
        with self._lock:
            try:
                data = self._ser.read(4)
            except serial.SerialException as ex:
                self.log("Serial error: ", ex)
                return None, None
            if len(data) != 4: # we got a timeout
                self.log("Timeout in recvpackage")
                return None, None
            # Read response length
            data = data[2:] # skip 2 first bytes
            dLen = struct.unpack('<B', data[0])[0]
            cmd = struct.unpack('<B', data[1])[0]
            #cmd = data[1]
            data = self._ser.read(dLen[0]-1 + 2)
            if len(data) != (dLen[0]-1 + 2):
                self.log("Timeout getting data for cmd", cmd)
                return None, None
            return cmd, data[:-2]
        
    def sendPackage(self, outMsg):
        with self._lock:
            self._ser.flushInput()
            self._ser.write(outMsg)
            return self.recvPackage()



