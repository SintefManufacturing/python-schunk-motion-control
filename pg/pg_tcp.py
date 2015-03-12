import logging
import socket
import struct
import time


class PGTCP(object):
    """
    Serial connection over TCP bridge (tested with landtronix)
    """
    def __init__(self, ipport, timeout):
        self.logger = logging.getLogger(self.__class__.__name__)
        self._sock = socket.create_connection(ipport, timeout=2)
        #self._sock.setblocking(False)
        self.logger.info(' %s is open', self._sock.getsockname())
        self.timeout = timeout

    def recv(self, size):
        """
        Receive up to size bytes from socket
        """
        data = b''
        while size > 0:
            chunk = self._sock.recv(size)
            if not chunk:
                break
            data += chunk
            size -= len(chunk)
        return data

    def send(self, data):
        self.logger.debug("Sending: %s", data)
        self._sock.send(data)

    def cleanup(self):
        if self._sock:
            self._sock.close()



