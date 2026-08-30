import struct
import zlib
import os

def create_png(filepath, width, height, color):
    def chunk(chunk_type, data):
        return struct.pack('>I', len(data)) + chunk_type + data + struct.pack('>I', zlib.crc32(chunk_type + data) & 0xffffffff)
    signature = b'\x89PNG\r\n\x1a\n'
    ihdr = struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)
    raw = b''
    r, g, b = color
    for y in range(height):
        raw += b'\x00'
        for x in range(width):
            raw += bytes([r, g, b])
    idat = zlib.compress(raw)
    with open(filepath, 'wb') as f:
        f.write(signature)
        f.write(chunk(b'IHDR', ihdr))
        f.write(chunk(b'IDAT', idat))
        f.write(chunk(b'IEND', b''))

target = r"icon.png"
create_png(target, 256, 256, (70, 130, 180))
print(f"Created: {target}")
print(f"Size: {os.path.getsize(target)} bytes")
