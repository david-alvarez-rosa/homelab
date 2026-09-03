import json
import os
import subprocess
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

CONF = os.environ.get("WA_VIEWONCE_CONF", "/etc/wa-viewonce.conf")
INBOX = "/var/lib/wa-viewonce/inbox"
MAX = 2 * 1024 * 1024 * 1024


def conf():
    with open(CONF) as f:
        return json.load(f)


class Handler(BaseHTTPRequestHandler):
    server_version = "wavo"

    def log_message(self, fmt, *args):
        print("%s %s" % (self.client_address[0], fmt % args), flush=True)

    def reply(self, code, body):
        data = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        cf = conf()
        if self.headers.get("X-Upload-Token") != cf["upload_token"]:
            return self.reply(403, "forbidden\n")
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0 or length > MAX:
            return self.reply(413, "bad length\n")
        os.makedirs(INBOX, exist_ok=True)
        path = os.path.join(INBOX, "msgstore-%d.crypt15" % int(time.time()))
        remaining = length
        with open(path, "wb") as f:
            while remaining > 0:
                chunk = self.rfile.read(min(1 << 20, remaining))
                if not chunk:
                    break
                f.write(chunk)
                remaining -= len(chunk)
        print("received %s (%d bytes)" % (path, os.path.getsize(path)), flush=True)
        p = subprocess.run(["/opt/wa-viewonce/ingest.sh", path], capture_output=True, text=True, timeout=1800)
        out = (p.stdout or "") + (p.stderr or "")
        print(out, flush=True)
        keep = cf.get("keep_backups", 2)
        files = sorted(os.path.join(INBOX, f) for f in os.listdir(INBOX))
        for old in (files[:-keep] if keep else files):
            os.unlink(old)
        return self.reply(200 if p.returncode == 0 else 500, out or "done\n")


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", 8971), Handler).serve_forever()
