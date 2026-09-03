import datetime
import glob
import json
import os
import re
import sqlite3

LOGS = "/srv/matrix.alvarezrosa.com/mautrix-whatsapp/logs/*.log"
STATE = "/opt/wa-viewonce/state.db"
WANT = "/var/lib/wa-viewonce/want"
PAT = re.compile(r'Unavailable message (\S+) from (\S+?)(?: in (\S+?))? \(type: "view_once"\)')
WINDOW_DAYS = 14


def done():
    try:
        db = sqlite3.connect("file:%s?mode=ro" % STATE, uri=True)
        return {r[0] for r in db.execute("select key_id from done")}
    except sqlite3.Error:
        return set()


def main():
    handled = done()
    now = datetime.datetime.now(datetime.timezone.utc)
    oldest = None
    for path in sorted(glob.glob(LOGS)):
        with open(path, errors="replace") as f:
            for line in f:
                if "view_once" not in line:
                    continue
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                m = PAT.search(rec.get("message", ""))
                if not m or m.group(1) in handled:
                    continue
                t = datetime.datetime.fromisoformat(rec["time"][:19]).replace(tzinfo=datetime.timezone.utc)
                if (now - t).days > WINDOW_DAYS:
                    continue
                if oldest is None or t < oldest:
                    oldest = t
    answer = "want %d" % int(oldest.timestamp()) if oldest else "idle"
    tmp = WANT + ".tmp"
    with open(tmp, "w") as f:
        f.write(answer + "\n")
    os.chmod(tmp, 0o644)
    os.replace(tmp, WANT)
    print(answer)


if __name__ == "__main__":
    main()
