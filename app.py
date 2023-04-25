import re
import subprocess
import threading
from os import path, urandom, getenv
from typing import Dict

from flask import Flask, g, redirect, render_template, request


env_file: str = "/opt/adsb/.env"

class EnvFile:
    def __init__(self, env_file_path: str):
        self.env_file_path = env_file_path

    def _setup(self):
        # if file does not exist, create it
        if not path.isfile(self.env_file_path):
            open(self.env_file_path, "w").close()

    @property
    def envs(self):
        env_values = {}

        with open(self.env_file_path) as f:
            for line in f:
                if line.strip().startswith("#"):
                    continue
                key, var = line.partition("=")[::2]
                env_values[key.strip()] = var.strip()

        env_values.setdefault("FEEDER_TAR1090_USEROUTEAPI", "")
        env_values.setdefault("FEEDER_ULTRAFEEDER_CONFIG", "")
        env_values.setdefault("route", "")

        adv_visibility = (
            "visible"
            if all(
                key in env_values and float(env_values[key]) != 0
                for key in ["FEEDER_LAT", "FEEDER_LONG", "FEEDER_ALT"]
            )
            else "invisible"
        )
        env_values["adv_visible"] = adv_visibility

        return env_values

    def modify_env(self, values: Dict[str, str]):
        if not path.isfile(self.env_file_path):
            open(self.env_file_path, "w").close()

        with open(self.env_file_path, "r") as ef:
            lines = ef.readlines()

    with open(env_file, "r") as ef:
        lines = ef.readlines()
        for idx in range(len(lines)):
            line = lines[idx]
            for key in values.keys():
                match = re.search(f"(^[^#]*{key}[^#]*=)[^#]*", line)
                if match:
                    lines[idx] = f"{match.group(1)} {values[key]}\n"
                    values[key] = ''  # so we don't write it a second time at the end
    for key in values:
        if values[key]:
            lines.append(f"{key} = {values[key]}\n")
    with open(env_file, "w") as ef:
        ef.writelines(lines)


class Restart:
    def __init__(self):
        self.lock = threading.Lock()

    def restart_systemd(self):
        # if locked, return immediately
        if not self.lock.acquire(False):
            return False
        with self.lock:
            subprocess.call("/usr/bin/systemctl restart adsb-docker", shell=True)


app = Flask(__name__)
app.secret_key = urandom(16).hex()
g.env_file = EnvFile(getenv("ADSB_PI_SETUP_ENVFILE", ".env"))
g.env_file._setup()
g.restart = Restart()


@app.route("/propagateTZ")
def get_tz():
    browser_timezone = request.args.get("tz")
    env_values = g.env_file.envs
    env_values["FEEDER_TZ"] = browser_timezone
    return render_template("index.html", env_values=env_values)


@app.route("/restarting", methods=("GET", "POST"))
def restarting():
    if request.method == "POST":
        restart = get_restart().restart_systemd()
        if not restart:
            return "restarting"
        return "done"
    return render_template("restarting.html", env_values=g.env_file.envs)


@app.route("/advanced", methods=("GET", "POST"))
def advanced():
    if request.method == "POST":
        return handle_advanced_post_request()
    env_values = g.env_file.envs
    set_checked_flags(env_values)
    return render_template("advanced.html", env_values=env_values)


def handle_advanced_post_request():
    if request.form.get("tar1090") == "go":
        host, port = request.server
        tar1090 = request.url_root.replace(str(port), "8080")
        return redirect(tar1090)

    net_configs = []
    for key, net_config in NET_CONFIGS.items():
        if request.form.get(key):
            net_configs.append(net_config)
    net = ";".join(net_configs) or DEFAULT_NET_CONFIG

    g.env_file.modify_env(
        {
            "FEEDER_TAR1090_USEROUTEAPI": "1" if request.form.get("route") else "0",
            "FEEDER_ULTRAFEEDER_CONFIG": net,
        }
    )
    return redirect("/restarting")


NET_CONFIGS = {
    "adsblol": "adsb,in.adsb.lol,30004,beast_reduce_plus_out;mlat,in.adsb.lol,31090,39001",
    "adsbx": "adsb,feed1.adsbexchange.com,30004,beast_reduce_plus_out;mlat,feed.adsbexchange.com,31090,39005",
    "tat": "adsb,feed.theairtraffic.com,30004,beast_reduce_plus_out;mlat,feed.theairtraffic.com,31090,39004",
    "ps": "adsb,feed.planespotters.net,30004,beast_reduce_plus_out;mlat,mlat.planespotters.net,31090,39003",
    "adsbone": "adsb,feed.adsb.one,64004,beast_reduce_plus_out;mlat,feed.adsb.one,64006,39002",
    "adsbfi": "adsb,feed.adsb.fi,30004,beast_reduce_plus_out;mlat,feed.adsb.fi,31090,39000",
}

DEFAULT_NET_CONFIG = (
    "adsb,in.adsb.lol,30004,beast_reduce_plus_out;mlat,in.adsb.lol,31090,39001"
)


def set_checked_flags(env_values):
    for key in NET_CONFIGS.keys():
        env_values[key] = (
            "checked" if key in env_values["FEEDER_ULTRAFEEDER_CONFIG"] else ""
        )


@app.route("/", methods=("GET", "POST"))
def setup():
    if request.args.get("success"):
        return redirect("/advanced")

    if request.method == "POST":
        lat, lng, alt, form_timezone = (
            request.form[key] for key in ["lat", "lng", "alt", "form_timezone"]
        )

        if all([lat, lng, alt, form_timezone]):
            g.env_file.modify_env(
                {
                    "FEEDER_LAT": lat,
                    "FEEDER_LONG": lng,
                    "FEEDER_ALT": alt,
                    "FEEDER_TZ": form_timezone,
                }
            )
            return redirect("/restarting")

    return render_template("index.html", env_values=g.env_file.envs)
