import json
import socket
import time
import uuid

MAX_PACKET = 8192

def encode(obj):
    return json.dumps(obj, separators=(',', ':')).encode()

def decode(data):
    obj = json.loads(data)
    if not isinstance(obj, dict) or obj.get('v') != 1:
        raise ValueError('expected version 1 object')
    return obj

def request(sock, target, obj, timeout=0.4, retries=3):
    obj = dict(obj, v=1, xid=uuid.uuid4().hex)
    for _ in range(retries):
        sock.sendto(encode(obj), target)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            sock.settimeout(max(0.001, deadline - time.monotonic()))
            try:
                data, peer = sock.recvfrom(MAX_PACKET)
                reply = decode(data)
                if peer == target and reply.get('xid') == obj['xid']:
                    return reply
            except (socket.timeout, ValueError, UnicodeError):
                pass
    raise TimeoutError('no matching UDP response')
