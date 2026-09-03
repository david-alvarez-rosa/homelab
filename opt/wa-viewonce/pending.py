import datetime
import glob
import json
import re
import sqlite3

LOGS = "/srv/matrix.alvarezrosa.com/mautrix-whatsapp/logs/*.log"
STATE = "/opt/wa-viewonce/state.db"
PAT = re.compile(r'Unavailable message (\S+) from (\S+?)(?: in (\S+?))? \(type: "view_once"\)')
WINDOW_DAYS = 14


def seen():
    try:
        db = sqlite3.connect("file:%s?mode=ro" % STATE, uri=True)
        return {r[0]: r[1] for r in db.execute("select key_id, note from done")}
    except sqlite3.Error:
        return {}


def age_days(when):
    t = datetime.datetime.fromisoformat(when).replace(tzinfo=datetime.timezone.utc)
    return (datetime.datetime.now(datetime.timezone.utc) - t).days


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
    recovered = pending = expired = 0
    print("%-24s %-20s %-40s %s" % ("MESSAGE ID", "WHEN", "CHAT", "STATUS"))
    for kid, (when, chat) in sorted(found.items(), key=lambda kv: kv[1][0]):
        status = done.get(kid)
        if status is None:
            days = age_days(when)
            if days <= WINDOW_DAYS:
                status = "PENDING (back up before opening)"
                pending += 1
            else:
                status = "expired unrecovered (%dd old)" % days
                expired += 1
        elif status.startswith("ok"):
            recovered += 1
        print("%-24s %-20s %-40s %s" % (kid, when, chat, status))
    print("\n%d seen: %d recovered, %d pending, %d expired, %d unrecoverable"
          % (len(found), recovered, pending, expired, len(found) - recovered - pending - expired))


if __name__ == "__main__":
    main()
