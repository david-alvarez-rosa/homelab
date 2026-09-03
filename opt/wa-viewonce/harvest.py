import base64
import json
import os
import sqlite3
import sys
import time

sys.path.insert(0, "/opt/wa-viewonce")
import mx
import wamedia

CONF = os.environ.get("WA_VIEWONCE_CONF", "/etc/wa-viewonce.conf")
STATE = "/opt/wa-viewonce/state.db"
KINDS = {"image": "image", "video": "video", "audio": "audio", "application": "document", "text": "document"}

QUERY = """
select m._id, m.key_id, m.timestamp, m.from_me,
       coalesce(cj.raw_string, cj.user || '@' || cj.server) as chat_jid,
       coalesce(sj.raw_string, sj.user || '@' || sj.server) as sender_jid,
       mm.media_key, mm.direct_path, mm.enc_file_hash, mm.file_hash,
       mm.mime_type, mm.file_length, mm.file_size, mm.width, mm.height, mm.media_name,
       v.state
from message m
join message_view_once_media v on v.message_row_id = m._id
join message_media mm on mm.message_row_id = m._id
join chat c on c._id = m.chat_row_id
join jid cj on cj._id = c.jid_row_id
left join jid sj on sj._id = m.sender_jid_row_id
where m.from_me = 0
order by m.timestamp
"""


def conf():
    with open(CONF) as f:
        return json.load(f)


def state():
    db = sqlite3.connect(STATE)
    db.execute("create table if not exists done (key_id text primary key, chat_jid text, mxid text, ts int, note text)")
    db.commit()
    return db


def bridge_lookup(bridge_db, chat_jid, sender_jid):
    c = sqlite3.connect("file:%s?mode=ro" % bridge_db, uri=True)
    row = c.execute("select mxid from portal where id = ? and mxid is not null limit 1", (chat_jid,)).fetchone()
    room = row[0] if row else None
    sender = sender_jid or chat_jid
    user = sender.split("@")[0].split(":")[0]
    if sender.endswith("@lid"):
        r = c.execute("select pn from whatsmeow_lid_map where lid like ? limit 1", (user + "%",)).fetchone()
        if r:
            user = r[0].split("@")[0].split(":")[0]
    c.close()
    return room, user


def kind_of(mime):
    return KINDS.get((mime or "image/jpeg").split("/")[0], "document")


def b64(v):
    if v is None:
        return None
    if isinstance(v, (bytes, bytearray)):
        return bytes(v)
    return base64.b64decode(v)


def run(msgstore, dry=False):
    cf = conf()
    m = mx.Matrix(cf["homeserver"], cf["as_token"], cf["domain"])
    st = state()
    done = {r[0] for r in st.execute("select key_id from done")}
    db = sqlite3.connect("file:%s?mode=ro" % msgstore, uri=True)
    db.row_factory = sqlite3.Row
    rows = db.execute(QUERY).fetchall()
    print("view-once rows in backup: %d (already handled: %d)" % (len(rows), len(done)))
    for r in rows:
        kid = r["key_id"]
        tag = "%s %s state=%s" % (kid, r["chat_jid"], r["state"])
        if kid in done:
            continue
        if not r["media_key"] or not r["direct_path"]:
            print("SKIP %s no media key/path (state=%s)" % (tag, r["state"]))
            continue
        room, user = bridge_lookup(cf["bridge_db"], r["chat_jid"], r["sender_jid"])
        if not room:
            print("SKIP %s no matrix portal" % tag)
            continue
        kind = kind_of(r["mime_type"])
        try:
            plain = wamedia.get(
                r["direct_path"], b64(r["enc_file_hash"]), bytes(r["media_key"]), kind, b64(r["file_hash"])
            )
        except Exception as e:
            print("FAIL %s download: %s" % (tag, e))
            continue
        name = r["media_name"] or ("viewonce-%s.%s" % (kid[:8], (r["mime_type"] or "image/jpeg").split("/")[-1]))
        if dry:
            print("DRY  %s -> %s %s %d bytes" % (tag, room, name, len(plain)))
            continue
        ghost = m.ghost(user)
        mxc = m.upload(plain, r["mime_type"] or "image/jpeg", name, ghost)
        info = {"mimetype": r["mime_type"] or "image/jpeg", "size": len(plain)}
        if r["width"]:
            info["w"] = r["width"]
        if r["height"]:
            info["h"] = r["height"]
        msgtype = {"image": "m.image", "video": "m.video", "audio": "m.audio"}.get(kind, "m.file")
        content = {
            "msgtype": msgtype,
            "body": name,
            "filename": name,
            "url": mxc,
            "info": info,
            "fi.mau.whatsapp.view_once": True,
        }
        ev = m.send(room, content, ghost, ts=r["timestamp"])
        note = "ok"
        if cf.get("redact_placeholder", True):
            try:
                ph = m.find_placeholder(room, ghost, r["timestamp"])
                if ph:
                    m.redact(room, ph, ghost)
                    note = "ok+redacted"
            except Exception as e:
                note = "ok (redact failed: %s)" % e
        st.execute(
            "insert or replace into done values (?,?,?,?,?)",
            (kid, r["chat_jid"], ev, int(time.time()), note),
        )
        st.commit()
        print("SENT %s -> %s %s %d bytes (%s)" % (tag, room, ev, len(plain), note))


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    run(args[0], dry="--dry" in sys.argv)
