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
MSGTYPES = {"image": "m.image", "video": "m.video", "audio": "m.audio"}

QUERY = """
select m._id, m.key_id, m.timestamp, m.from_me,
       coalesce(cj.raw_string, cj.user || '@' || cj.server) as chat_jid,
       coalesce(sj.raw_string, sj.user || '@' || sj.server) as sender_jid,
       mm.media_key, mm.direct_path, mm.enc_file_hash, mm.file_hash,
       mm.mime_type, mm.file_length, mm.width, mm.height, mm.media_name,
       v.state
from message m
join message_view_once_media v on v.message_row_id = m._id
left join message_media mm on mm.message_row_id = m._id
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


def b64(v):
    if v is None:
        return None
    return bytes(v) if isinstance(v, (bytes, bytearray)) else base64.b64decode(v)


def run(msgstore, dry=False):
    cf = conf()
    m = mx.Matrix(cf["homeserver"], cf["as_token"], cf["domain"])
    st = state()
    done = {r[0] for r in st.execute("select key_id from done")}
    db = sqlite3.connect("file:%s?mode=ro" % msgstore, uri=True)
    db.row_factory = sqlite3.Row
    rows = db.execute(QUERY).fetchall()
    fresh = [r for r in rows if r["key_id"] not in done]
    scrubbed = [r for r in fresh if not r["media_key"] or not r["direct_path"]]
    live = [r for r in fresh if r["media_key"] and r["direct_path"]]
    print("view-once in backup: %d total, %d new, %d recoverable" % (len(rows), len(fresh), len(live)))
    if scrubbed and not dry:
        st.executemany(
            "insert or replace into done values (?,?,?,?,?)",
            [(r["key_id"], r["chat_jid"], None, int(time.time()), "unrecoverable (state=%s, key scrubbed)" % r["state"]) for r in scrubbed],
        )
        st.commit()
        print("marked %d already-viewed messages as unrecoverable" % len(scrubbed))
    for r in live:
        tag = "%s %s state=%s" % (r["key_id"], r["chat_jid"], r["state"])
        room, user = bridge_lookup(cf["bridge_db"], r["chat_jid"], r["sender_jid"])
        if not room:
            print("SKIP %s no matrix portal" % tag)
            continue
        kind = KINDS.get((r["mime_type"] or "image/jpeg").split("/")[0], "document")
        try:
            plain = wamedia.get(
                r["direct_path"], b64(r["enc_file_hash"]), bytes(r["media_key"]), kind, b64(r["file_hash"])
            )
        except Exception as e:
            print("FAIL %s download: %s" % (tag, e))
            continue
        name = r["media_name"] or ("viewonce-%s.%s" % (r["key_id"][:8], (r["mime_type"] or "image/jpeg").split("/")[-1]))
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
        content = {
            "msgtype": MSGTYPES.get(kind, "m.file"),
            "body": name,
            "filename": name,
            "url": mxc,
            "info": info,
            "fi.mau.whatsapp.view_once": True,
        }
        note = "ok"
        if cf.get("reply_to_placeholder", True):
            try:
                ph = m.find_placeholder(room, ghost, r["timestamp"])
                if ph:
                    content["m.relates_to"] = {"m.in_reply_to": {"event_id": ph}}
                    note = "ok+linked"
            except Exception as e:
                note = "ok (placeholder lookup failed: %s)" % e
        ev = m.send(room, content, ghost, ts=r["timestamp"])
        st.execute("insert or replace into done values (?,?,?,?,?)", (r["key_id"], r["chat_jid"], ev, int(time.time()), note))
        st.commit()
        print("SENT %s -> %s %s %d bytes (%s)" % (tag, room, ev, len(plain), note))


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    run(args[0], dry="--dry" in sys.argv)
