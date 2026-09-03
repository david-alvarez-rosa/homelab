import sqlite3
import sys

sys.path.insert(0, "/opt/wa-viewonce")
import wamedia
import wapb

DB = sys.argv[1] if len(sys.argv) > 1 else "/tmp/wa.db"
MEDIA_FIELDS = {3: "image", 9: "video"}


def extract(blob):
    wmi = wapb.sub(wapb.parse(blob), 1)
    if wmi is None:
        return None
    msg = wapb.sub(wmi, 2)
    if msg is None:
        return None
    for wrapper in (37, 55, 59):
        fp = wapb.sub(msg, wrapper)
        if fp:
            inner = wapb.sub(fp, 1)
            if inner:
                msg = inner
                break
    for field, kind in MEDIA_FIELDS.items():
        m = wapb.sub(msg, field)
        if m and wapb.one(m, 8) and wapb.text(m, 11):
            return {
                "kind": kind,
                "mime": wapb.text(m, 2),
                "sha256": wapb.one(m, 4),
                "length": wapb.one(m, 5),
                "media_key": wapb.one(m, 8),
                "enc_sha256": wapb.one(m, 9),
                "direct_path": wapb.text(m, 11),
                "view_once": bool(wapb.one(m, 25)),
            }
    return None


c = sqlite3.connect("file:%s?mode=ro" % DB, uri=True)
rows = c.execute("select message_id, timestamp, chat_jid, data from whatsapp_history_sync_message order by timestamp desc").fetchall()
print("history rows: %d" % len(rows))
tried = 0
for mid, ts, chat, blob in rows:
    info = extract(blob)
    if not info or not info["enc_sha256"]:
        continue
    tried += 1
    print("\ntrying %s %s %s %s vo=%s len=%s" % (mid, chat, info["kind"], info["mime"], info["view_once"], info["length"]))
    try:
        plain = wamedia.get(info["direct_path"], info["enc_sha256"], info["media_key"], info["kind"], info["sha256"])
    except Exception as e:
        print("  FAIL %s" % e)
    else:
        print("  OK decrypted %d bytes, sha256 verified, magic=%s" % (len(plain), plain[:4].hex()))
        break
    if tried >= 5:
        break
