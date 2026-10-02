"""Bounded native-pixel mailboxes; metadata and pixels are copied under one lock."""
import json
import numpy as np


class SharedFrame:
    def __init__(self, ctx, max_bytes=3840*2160*3):
        self.pixels = ctx.RawArray('B', max_bytes)
        self.header = ctx.RawArray('B', 4096)
        self.header_size = ctx.RawValue('i', 0)
        self.lock = ctx.Lock()
        self.max_bytes = max_bytes

    def publish(self, metadata, frame):
        header = json.dumps(metadata).encode()
        if frame.nbytes > self.max_bytes or len(header) > len(self.header):
            raise ValueError('Frame exceeds configured shared-memory capacity')
        if not self.lock.acquire(timeout=.1):
            return False
        try:
            np.frombuffer(self.pixels, dtype=np.uint8, count=frame.size)[:] = frame.ravel()
            self.header[:len(header)] = header
            self.header_size.value = len(header)
        finally:
            self.lock.release()
        return True

    def read(self, previous=None):
        if not self.lock.acquire(timeout=.05):
            return None
        try:
            if not self.header_size.value:
                return None
            metadata = json.loads(bytes(self.header[:self.header_size.value]))
            identity = (metadata['session'], metadata['sequence'])
            if identity == previous:
                return None
            shape = (metadata['height'], metadata['width'], 3)
            count = int(np.prod(shape))
            if count > self.max_bytes:
                raise ValueError('Invalid frame size')
            return metadata, np.frombuffer(self.pixels, dtype=np.uint8, count=count).reshape(shape).copy()
        finally:
            self.lock.release()
