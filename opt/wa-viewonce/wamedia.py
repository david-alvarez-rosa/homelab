import base64
import hashlib
import hmac

import requests
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

HOSTS = ("mmg.whatsapp.net",)
HEADERS = {"Origin": "https://web.whatsapp.com", "Referer": "https://web.whatsapp.com/"}
KINDS = {
    "image": (b"WhatsApp Image Keys", "image"),
    "video": (b"WhatsApp Video Keys", "video"),
    "audio": (b"WhatsApp Audio Keys", "audio"),
    "document": (b"WhatsApp Document Keys", "document"),
}


def expand(media_key, kind):
    info = KINDS[kind][0]
    return HKDF(algorithm=hashes.SHA256(), length=112, salt=None, info=info).derive(media_key)


def decrypt(blob, media_key, kind):
    k = expand(media_key, kind)
    iv, cipher_key, mac_key = k[:16], k[16:48], k[48:80]
    body, mac = blob[:-10], blob[-10:]
    if not hmac.compare_digest(mac, hmac.new(mac_key, iv + body, hashlib.sha256).digest()[:10]):
        raise ValueError("media mac mismatch")
    d = Cipher(algorithms.AES(cipher_key), modes.CBC(iv)).decryptor()
    out = d.update(body) + d.finalize()
    pad = out[-1]
    return out[:-pad] if 1 <= pad <= 16 else out


def url_for(direct_path, enc_sha256, kind, host):
    h = base64.urlsafe_b64encode(enc_sha256).decode()
    return "https://%s%s&hash=%s&mms-type=%s&__wa-mms=" % (host, direct_path, h, KINDS[kind][1])


def fetch(direct_path, enc_sha256, kind):
    last = None
    for host in HOSTS:
        r = requests.get(url_for(direct_path, enc_sha256, kind, host), headers=HEADERS, timeout=120)
        if r.status_code == 200:
            return r.content
        last = "%s %d" % (host, r.status_code)
    raise RuntimeError("download failed: %s" % last)


def get(direct_path, enc_sha256, media_key, kind, sha256=None):
    plain = decrypt(fetch(direct_path, enc_sha256, kind), media_key, kind)
    if sha256 and hashlib.sha256(plain).digest() != sha256:
        raise ValueError("plaintext hash mismatch")
    return plain
