import serial
import logging


class PGSerial(object):
    def __init__(self, comPort, timeout=16):
        self.logger = logging.getLogger(self.__class__.__name__)
        self._ser = serial.Serial(comPort, 9600)
        self._ser.setTimeout(timeout)
        self._ser.flush()
        self.logger.debug("%s is open", self._ser.portstr)

    def recv(self, size):
        data = self._ser.read(size)
        self.logger.debug("received %s", data)
        if len(data) != size: # we got a timeout
            raise Exception("Timeout in recvpackage")
        return data
        
    def send(self, data):
        self.logger.debug("sending %s", data)
        self._ser.write(data)

    def cleanup(self):
        self._ser.flush()



