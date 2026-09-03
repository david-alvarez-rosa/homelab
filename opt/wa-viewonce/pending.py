import glob
import json
import re
import sqlite3
import sys

LOGS = "/srv/matrix.alvarezrosa.com/mautrix-whatsapp/logs/*.log"
STATE = "/opt/wa-viewonce/state.db"
PAT = re.compile(r'Unavailable message (\S+) from (\S+?)(?: in (\S+?))? \(type: "view_once"\)')


def seen():
    try:
        db = sqlite3.connect("file:%s?mode=ro" % STATE, uri=True)
        return {r[0]: r[1] for r in db.execute("select key_id, note from done")}
    except sqlite3.Error:
        return {}


def main():
    done = seen()
    found = {}
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
                if m:
                    found[m.group(1)] = (rec.get("time", "")[:19], m.group(3) or m.group(2))
    print("%-24s %-20s %-40s %s" % ("MESSAGE ID", "WHEN", "CHAT", "STATUS"))
    for kid, (when, chat) in sorted(found.items(), key=lambda kv: kv[1][0]):
        print("%-24s %-20s %-40s %s" % (kid, when, chat, done.get(kid, "PENDING")))
    print("\n%d view-once messages seen, %d recovered, %d pending" % (len(found), sum(1 for k in found if k in done), sum(1 for k in found if k not in done)))


if __name__ == "__main__":
    main()
