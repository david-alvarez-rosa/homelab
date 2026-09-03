import time
import urllib.parse

import requests


class Matrix:
    def __init__(self, base, token, domain):
        self.base = base.rstrip("/")
        self.token = token
        self.domain = domain

    def ghost(self, phone):
        return "@whatsapp_%s:%s" % (phone, self.domain)

    def _headers(self, mime=None):
        h = {"Authorization": "Bearer %s" % self.token}
        if mime:
            h["Content-Type"] = mime
        return h

    def upload(self, data, mime, filename, user):
        r = requests.post(
            self.base + "/_matrix/media/v3/upload",
            params={"filename": filename, "user_id": user},
            headers=self._headers(mime),
            data=data,
            timeout=300,
        )
        r.raise_for_status()
        return r.json()["content_uri"]

    def send(self, room, content, user, ts=None):
        txn = "wavo-%d" % int(time.time() * 1000000)
        params = {"user_id": user}
        if ts:
            params["ts"] = str(int(ts))
        r = requests.put(
            "%s/_matrix/client/v3/rooms/%s/send/m.room.message/%s"
            % (self.base, urllib.parse.quote(room), txn),
            params=params,
            headers=self._headers("application/json"),
            json=content,
            timeout=120,
        )
        r.raise_for_status()
        return r.json()["event_id"]

    def messages(self, room, user, limit=300):
        r = requests.get(
            "%s/_matrix/client/v3/rooms/%s/messages" % (self.base, urllib.parse.quote(room)),
            params={"user_id": user, "dir": "b", "limit": str(limit)},
            headers=self._headers(),
            timeout=120,
        )
        r.raise_for_status()
        return r.json().get("chunk", [])

    def redact(self, room, event_id, user, reason="replaced by recovered view-once media"):
        txn = "wavor-%d" % int(time.time() * 1000000)
        r = requests.put(
            "%s/_matrix/client/v3/rooms/%s/redact/%s/%s"
            % (self.base, urllib.parse.quote(room), urllib.parse.quote(event_id), txn),
            params={"user_id": user},
            headers=self._headers("application/json"),
            json={"reason": reason},
            timeout=60,
        )
        r.raise_for_status()
        return r.json().get("event_id")

    def find_placeholder(self, room, user, ts, window=600000):
        for ev in self.messages(room, user):
            if ev.get("type") != "m.room.message":
                continue
            c = ev.get("content") or {}
            if not c.get("fi.mau.whatsapp.undecryptable"):
                continue
            if abs(int(ev.get("origin_server_ts", 0)) - int(ts)) <= window:
                return ev["event_id"]
        return None
