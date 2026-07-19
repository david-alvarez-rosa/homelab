import os
from uptime_kuma_api import UptimeKumaApi, MonitorType

URL = "http://127.0.0.1:3011"
USER = os.environ["KUMA_USER"]
PW = os.environ["KUMA_PASS"]
TITLE = "Homelab Status"
SLUG = "main"

api = UptimeKumaApi(URL)
api.login(USER, PW)
existing = {m["name"]: m["id"] for m in api.get_monitors()}

def ensure(name, **kw):
    if name in existing:
        return existing[name]
    kw.setdefault("interval", 1800)
    existing[name] = api.add_monitor(name=name, **kw)["monitorID"]
    return existing[name]

g_sites = ensure("Sites", type=MonitorType.GROUP)
g_api = ensure("APIs", type=MonitorType.GROUP)
g_mail = ensure("Mail", type=MonitorType.GROUP)
g_infra = ensure("Infrastructure", type=MonitorType.GROUP)

OK = ["200-299"]
API = ["200-299", "400-499"]

sites = [
    ensure("unwall.app", type=MonitorType.HTTP, url="https://unwall.app", parent=g_sites, accepted_statuscodes=OK),
    ensure("live.unwall.app", type=MonitorType.HTTP, url="https://live.unwall.app", parent=g_sites, accepted_statuscodes=OK),
    ensure("david.alvarezrosa.com", type=MonitorType.HTTP, url="https://david.alvarezrosa.com", parent=g_sites, accepted_statuscodes=OK),
    ensure("dhevt6e4rtgbtr3jh53xrpwmgtilkah6nyjujocsspssrsexc7omxhid.onion", type=MonitorType.HTTP, url="http://host.docker.internal:8080", parent=g_sites, accepted_statuscodes=OK, headers='{"Host": "dhevt6e4rtgbtr3jh53xrpwmgtilkah6nyjujocsspssrsexc7omxhid.onion"}'),
    ensure("david.alvarezrosa.com/tres-en-raya", type=MonitorType.HTTP, url="https://david.alvarezrosa.com/tres-en-raya/", parent=g_sites, accepted_statuscodes=OK),
    ensure("david.alvarezrosa.com/pasatiempos-dn", type=MonitorType.HTTP, url="https://david.alvarezrosa.com/pasatiempos-dn/", parent=g_sites, accepted_statuscodes=OK),
    ensure("analytics.alvarezrosa.com", type=MonitorType.HTTP, url="https://analytics.alvarezrosa.com", parent=g_sites, accepted_statuscodes=OK),
    ensure("chat.alvarezrosa.com", type=MonitorType.KEYWORD, url="https://chat.alvarezrosa.com/", keyword="<title>Element</title>", parent=g_sites, accepted_statuscodes=OK),
    ensure("matrix.alvarezrosa.com", type=MonitorType.KEYWORD, url="https://matrix.alvarezrosa.com/_matrix/client/versions", keyword='"versions"', parent=g_sites, accepted_statuscodes=OK),
    ensure("cloud.alvarezrosa.com", type=MonitorType.KEYWORD, url="https://cloud.alvarezrosa.com/status.php", keyword='"installed":true', parent=g_sites, accepted_statuscodes=OK),
    ensure("cloud.alvarezmagan.com", type=MonitorType.KEYWORD, url="https://cloud.alvarezmagan.com/status.php", keyword='"installed":true', parent=g_sites, accepted_statuscodes=OK),
    ensure("mail.alvarezrosa.com", type=MonitorType.HTTP, url="https://mail.alvarezrosa.com", parent=g_sites, maxredirects=0, accepted_statuscodes=["301"]),
    ensure("meet.alvarezrosa.com", type=MonitorType.HTTP, url="https://meet.alvarezrosa.com", parent=g_sites, maxredirects=0, accepted_statuscodes=["301"]),
    ensure("share.alvarezrosa.com", type=MonitorType.HTTP, url="https://share.alvarezrosa.com", parent=g_sites, maxredirects=0, accepted_statuscodes=["301"]),
    ensure("mail.alvarezmagan.com", type=MonitorType.HTTP, url="https://mail.alvarezmagan.com", parent=g_sites, maxredirects=0, accepted_statuscodes=["301"]),
    ensure("meet.alvarezmagan.com", type=MonitorType.HTTP, url="https://meet.alvarezmagan.com", parent=g_sites, maxredirects=0, accepted_statuscodes=["301"]),
    ensure("share.alvarezmagan.com", type=MonitorType.HTTP, url="https://share.alvarezmagan.com", parent=g_sites, maxredirects=0, accepted_statuscodes=["301"]),
    ensure("beta.alvarezrosa.com", type=MonitorType.HTTP, url="https://beta.alvarezrosa.com", parent=g_sites, accepted_statuscodes=["200-299", "401"]),
    ensure("recomprehension.com", type=MonitorType.HTTP, url="https://recomprehension.com", parent=g_sites, accepted_statuscodes=OK),
]
apis = [
    ensure("api.alvarezrosa.com", type=MonitorType.HTTP, url="https://api.alvarezrosa.com", parent=g_api, accepted_statuscodes=API),
    ensure("api.unwall.app", type=MonitorType.HTTP, url="https://api.unwall.app", parent=g_api, accepted_statuscodes=API),
]
mail = [
    ensure("Mail — Inbound (SMTP)", type=MonitorType.PORT, hostname="host.docker.internal", port=25, parent=g_mail),
    ensure("Mail — Submission", type=MonitorType.PORT, hostname="host.docker.internal", port=465, parent=g_mail),
    ensure("Mail — IMAP", type=MonitorType.PORT, hostname="host.docker.internal", port=993, parent=g_mail),
    ensure("Mail — rspamd", type=MonitorType.PUSH, parent=g_mail),
]
infra = [ensure("SSH", type=MonitorType.PORT, hostname="host.docker.internal", port=22, parent=g_infra)]
infra.append(ensure("ssh.alvarezrosa.com", type=MonitorType.PORT, hostname="ssh.alvarezrosa.com", port=22, parent=g_infra, url="ssh://ssh.alvarezrosa.com"))
api.edit_monitor(existing["ssh.alvarezrosa.com"], url="ssh://ssh.alvarezrosa.com")
infra.append(ensure("tunnel.alvarezrosa.com", type=MonitorType.HTTP, url="https://tunnel.alvarezrosa.com", parent=g_infra, accepted_statuscodes=["200-299", "404"]))
infra.append(ensure("Talk TURN (coturn)", type=MonitorType.PORT, hostname="host.docker.internal", port=3478, parent=g_infra))
infra.append(ensure("talk.alvarezrosa.com (TURN)", type=MonitorType.PORT, hostname="talk.alvarezrosa.com", port=3478, parent=g_infra))
infra.append(ensure("GitHub runner", type=MonitorType.PUSH, parent=g_infra))
infra.append(ensure("fail2ban", type=MonitorType.PUSH, parent=g_infra))
infra.append(ensure("Network — internet", type=MonitorType.PING, hostname="1.1.1.1", parent=g_infra))
infra.append(ensure("Backup — restic", type=MonitorType.PUSH, parent=g_infra, interval=93600))

host = [ensure(label, type=MonitorType.PUSH, parent=g_infra) for label in ("CPU (% used)", "RAM (% used)", "Disk (% used)", "Ethernet (GB)")]

def entries(ids):
    return [{"id": i, "sendUrl": True} for i in ids]

if SLUG not in {p["slug"] for p in api.get_status_pages()}:
    api.add_status_page(SLUG, TITLE)

api.save_status_page(
    SLUG,
    title=TITLE,
    description="System and service status",
    theme="auto",
    published=True,
    showTags=False,
    showPoweredBy=False,
    footerText="Free as in freedom",
    customCSS="body {\n  \n}\n",
    publicGroupList=[
        {"name": "Sites", "monitorList": entries(sites)},
        {"name": "APIs", "monitorList": entries(apis)},
        {"name": "Mail", "monitorList": entries(mail)},
        {"name": "Infrastructure", "monitorList": entries(infra + host)},
    ],
)
print("done:", TITLE)
api.disconnect()
