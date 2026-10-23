import hashlib
import io
import json
import logging
import os
import re
import time
import urllib.parse

import requests
from faster_whisper import WhisperModel, decode_audio

BASE = os.environ.get("MATRIX_URL", "http://127.0.0.1:8008")
USER = os.environ.get("MATRIX_USER", "@david:matrix.alvarezrosa.com")
GHOSTS = re.compile(os.environ.get("MATRIX_GHOSTS", r"^@whatsapp_.+:matrix\.alvarezrosa\.com$"))
MODEL = os.environ.get("WHISPER_MODEL", "large-v3-turbo")
LANGUAGES = os.environ.get("WHISPER_LANGUAGES", "es,en").split(",")
THREADS = int(os.environ.get("WHISPER_THREADS", "8"))
MAX_SECONDS = int(os.environ.get("MAX_SECONDS", "1800"))
STATE = os.path.join(os.environ.get("STATE_DIRECTORY", "."), "since")
CACHE = os.environ.get("CACHE_DIRECTORY")
REGISTRATION = os.path.join(os.environ.get("CREDENTIALS_DIRECTORY", "."), "registration")
VOICE = "org.matrix.msc3245.voice"
DOUBLE_PUPPET = "fi.mau.double_puppet_source"
PREFIX = "🎙️ "
FILTER = json.dumps({
    "presence": {"types": []},
    "account_data": {"types": []},
    "room": {
        "state": {"types": []},
        "ephemeral": {"types": []},
        "account_data": {"types": []},
        "timeline": {"types": ["m.room.message"], "limit": 50},
    },
})

log = logging.getLogger("transcriber")


def read_token():
    with open(REGISTRATION) as f:
        m = re.search(r"^as_token:\s*[\"\x27]?([^\"\x27\s]+)", f.read(), re.M)
    return m.group(1)


class Matrix:
    def __init__(self, token):
        self.session = requests.Session()
        self.session.headers["Authorization"] = "Bearer " + token

    def sync(self, since, timeout):
        params = {"user_id": USER, "filter": FILTER, "set_presence": "offline", "timeout": str(timeout)}
        if since:
            params["since"] = since
        r = self.session.get(BASE + "/_matrix/client/v3/sync", params=params, timeout=timeout / 1000 + 60)
        r.raise_for_status()
        return r.json()

    def download(self, mxc):
        server, media = mxc.removeprefix("mxc://").split("/", 1)
        r = self.session.get(
            "%s/_matrix/client/v1/media/download/%s/%s" % (BASE, server, media),
            params={"user_id": USER},
            timeout=300,
        )
        r.raise_for_status()
        return r.content

    def send(self, room, sender, content, txn):
        r = self.session.put(
            "%s/_matrix/client/v3/rooms/%s/send/m.room.message/%s" % (BASE, urllib.parse.quote(room), txn),
            params={"user_id": sender},
            json=content,
            timeout=120,
        )
        r.raise_for_status()
        return r.json()["event_id"]


class Transcriber:
    def __init__(self):
        self.model = WhisperModel(MODEL, device="cpu", compute_type="int8", cpu_threads=THREADS, download_root=CACHE)

    def __call__(self, data):
        audio = decode_audio(io.BytesIO(data))
        _, _, probs = self.model.detect_language(audio, vad_filter=True)
        scores = {lang: p for lang, p in probs if lang in LANGUAGES}
        language = max(LANGUAGES, key=lambda lang: scores.get(lang, 0))
        segments, _ = self.model.transcribe(audio, language=language, vad_filter=True, beam_size=5)
        return language, " ".join(s.text.strip() for s in segments).strip()


def is_voice(event):
    c = event.get("content") or {}
    return (
        event.get("type") == "m.room.message"
        and c.get("msgtype") == "m.audio"
        and VOICE in c
        and "m.new_content" not in c
        and isinstance(c.get("url"), str)
        and (event.get("sender") == USER or GHOSTS.match(event.get("sender", "")))
    )


def handle(mx, transcribe, room, event):
    c = event["content"]
    duration = (c.get("info") or {}).get("duration") or 0
    if duration > MAX_SECONDS * 1000:
        log.info("skip %s in %s: %ds too long", event["event_id"], room, duration // 1000)
        return
    start = time.monotonic()
    language, text = transcribe(mx.download(c["url"]))
    if not text:
        log.info("skip %s in %s: no speech", event["event_id"], room)
        return
    content = {
        "msgtype": "m.notice",
        "body": PREFIX + text,
        "m.relates_to": {"m.in_reply_to": {"event_id": event["event_id"]}},
    }
    if event["sender"] == USER:
        content[DOUBLE_PUPPET] = "mautrix-whatsapp"
    txn = "transcribe-" + hashlib.sha256(event["event_id"].encode()).hexdigest()[:32]
    reply = mx.send(room, event["sender"], content, txn)
    log.info(
        "transcribed %s in %s: %ds %s in %.1fs -> %s",
        event["event_id"], room, duration // 1000, language, time.monotonic() - start, reply,
    )


def load_since():
    try:
        with open(STATE) as f:
            return f.read().strip() or None
    except FileNotFoundError:
        return None


def save_since(since):
    with open(STATE + ".tmp", "w") as f:
        f.write(since)
    os.replace(STATE + ".tmp", STATE)


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    mx = Matrix(read_token())
    transcribe = Transcriber()
    since = load_since()
    if since is None:
        since = mx.sync(None, 0)["next_batch"]
        save_since(since)
    log.info("ready: %s on %d threads, languages %s", MODEL, THREADS, ",".join(LANGUAGES))
    while True:
        try:
            data = mx.sync(since, 30000)
        except requests.RequestException as e:
            log.warning("sync failed: %s", e)
            time.sleep(10)
            continue
        for room, info in data.get("rooms", {}).get("join", {}).items():
            for event in info.get("timeline", {}).get("events", []):
                if not is_voice(event):
                    continue
                try:
                    handle(mx, transcribe, room, event)
                except Exception:
                    log.exception("failed %s in %s", event.get("event_id"), room)
        since = data["next_batch"]
        save_since(since)


if __name__ == "__main__":
    main()
