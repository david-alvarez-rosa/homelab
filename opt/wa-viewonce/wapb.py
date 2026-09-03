def _varint(b, i):
    r = s = 0
    while True:
        x = b[i]
        i += 1
        r |= (x & 0x7F) << s
        if not x & 0x80:
            return r, i
        s += 7


def parse(b):
    out = {}
    i, n = 0, len(b)
    while i < n:
        key, i = _varint(b, i)
        field, wt = key >> 3, key & 7
        if wt == 0:
            v, i = _varint(b, i)
        elif wt == 1:
            v, i = b[i:i + 8], i + 8
        elif wt == 2:
            ln, i = _varint(b, i)
            v, i = b[i:i + ln], i + ln
        elif wt == 5:
            v, i = b[i:i + 4], i + 4
        else:
            raise ValueError("wiretype %d" % wt)
        out.setdefault(field, []).append(v)
    return out


def one(msg, field):
    v = msg.get(field)
    return v[0] if v else None


def sub(msg, field):
    v = one(msg, field)
    return parse(v) if isinstance(v, (bytes, bytearray)) else None


def text(msg, field):
    v = one(msg, field)
    return v.decode("utf-8", "replace") if isinstance(v, (bytes, bytearray)) else None
