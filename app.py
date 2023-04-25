from typing import Dict

from flask import Flask, render_template, request, redirect
import subprocess
from os import urandom, path
import re


env_file: str = ".env"


def parse_env_file():
    _env_values = {}
    if path.isfile(env_file):
        with open(env_file) as f:
            for line in f:
                if line.strip().startswith('#'):
                    continue
                key, var = line.partition("=")[::2]
                _env_values[key.strip()] = var.strip()
    if 'FEEDER_TAR1090_USEROUTEAPI' not in _env_values: _env_values['FEEDER_TAR1090_USEROUTEAPI'] = ''
    if 'FEEDER_READSB_NET_CONNECTOR' not in _env_values: _env_values['FEEDER_READSB_NET_CONNECTOR'] = ''
    if 'FEEDER_MLAT_CONFIG' not in _env_values: _env_values['FEEDER_MLAT_CONFIG'] = ''
    if 'route' not in _env_values: _env_values['route'] = ''
    if 'FEEDER_LAT' in _env_values and float(_env_values['FEEDER_LAT']) != 0.0 and \
            'FEEDER_LONG' in _env_values and float(_env_values['FEEDER_LONG']) != 0.0 and \
            'FEEDER_ALT' in _env_values and int(_env_values['FEEDER_ALT']) != 0:
        _env_values['adv_visible'] = 'visible'
    else:
        _env_values['adv_visible'] = 'invisible'

    return _env_values


# read the .env file and update those mentioned in the Dict passed in (and add those entries that are new)
def modify_env(values: Dict[str, str]):
    if not path.isfile(env_file):
        # that's not a good sign, but at least let's not throw an error
        ef = open(env_file, 'w')
        ef.close()
    with open(env_file, 'r') as ef:
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
            lines.append(f"{key} = {values[key]}")
    with open(env_file, "w") as ef:
        ef.writelines(lines)


def restart():
    # this really needs to check if we are still waiting for the previous restart
    subprocess.call("/usr/bin/systemctl restart adsb-docker", shell=True)


app = Flask(__name__)
app.secret_key = urandom(16).hex()


@app.route('/propagateTZ')
def get_tz():
    browser_timezone = request.args.get("tz")
    env_values = parse_env_file()
    env_values['FEEDER_TZ'] = browser_timezone
    return render_template('index.html', env_values=env_values)


@app.route('/restarting', methods=('GET', 'POST'))
def restarting():
    if request.method == 'POST':
        restart()
        return "done"
    if request.method == 'GET':
        return render_template('restarting.html', env_values=parse_env_file())


@app.route('/advanced', methods=('GET', 'POST'))
def advanced():
    if request.method == 'POST':
        if request.form.get('tar1090') == "go":
            host, port = request.server
            tar1090 = request.url_root.replace(str(port), "8080")
            return redirect(tar1090)

        # explicitly make these empty
        route = 0
        mlat = net = ''
        if request.form.get('route'):
            route = '1'
        if request.form.get('adsblol'):
            if net: net += ';'
            if mlat: mlat += ';'
            net += 'in.adsb.lol,30004,beast_reduce_plus_out'
            mlat += 'in.adsb.lol,31090,39001'
        if request.form.get('adsbone'):
            if net: net += ';'
            if mlat: mlat += ';'
            net += 'feed.adsb.one,64004,beast_reduce_plus_out'
            mlat += 'feed.adsb.one,64006,39002'
        if request.form.get('adsbfi'):
            if net: net += ';'
            if mlat: mlat += ';'
            net += 'feed.adsb.fi,30004,beast_reduce_plus_out'
            mlat += 'feed.adsb.fi,31090,39000'
        if request.form.get('adsbx'):
            if net: net += ';'
            if mlat: mlat += ';'
            net += 'feed1.adsbexchange.com,30004,beast_reduce_plus_out'
            mlat += 'feed.adsbexchange.com,31090,39005'
        if request.form.get('tat'):
            if net: net += ';'
            if mlat: mlat += ';'
            net += 'feed.theairtraffic.com,30004,beast_reduce_plus_out'
            mlat += 'feed.theairtraffic.com,31090,39004'
        if request.form.get('ps'):
            if net: net += ';'
            if mlat: mlat += ';'
            net += 'feed.planespotters.net,30004,beast_reduce_plus_out'
            mlat += 'mlat.planespotters.net,31090,39003'
        if mlat == '':   # things fail if those variables are empty
            net = 'in.adsb.lol,30004,beast_reduce_plus_out'
            mlat = 'in.adsb.lol,31090,39001'

        modify_env({'FEEDER_TAR1090_USEROUTEAPI': route,
                    'FEEDER_READSB_NET_CONNECTOR': net,
                    'FEEDER_MLAT_CONFIG': mlat})
        return redirect('/restarting')
    env_values = parse_env_file()
    env_values['route'] = 'checked' if env_values['FEEDER_TAR1090_USEROUTEAPI'] == '1' else ''
    env_values['adsblol'] = 'checked' if 'adsb.lol' in env_values['FEEDER_READSB_NET_CONNECTOR'] else ''
    env_values['adsbone'] = 'checked' if 'adsb.one' in env_values['FEEDER_READSB_NET_CONNECTOR'] else ''
    env_values['adsbfi'] = 'checked' if 'adsb.fi' in env_values['FEEDER_READSB_NET_CONNECTOR'] else ''
    env_values['adsbx'] = 'checked' if 'adsbexchange' in env_values['FEEDER_READSB_NET_CONNECTOR'] else ''
    env_values['tat'] = 'checked' if 'theairtraffic' in env_values['FEEDER_READSB_NET_CONNECTOR'] else ''
    env_values['ps'] = 'checked' if 'planespotters' in env_values['FEEDER_READSB_NET_CONNECTOR'] else ''
    return render_template('advanced.html', env_values=env_values)
            

@app.route('/', methods=('GET', 'POST'))
def setup():
    message = ''
    if request.args.get("success"):
        return redirect("/advanced")
    env_values = parse_env_file()
    if request.method == 'POST':
        lat = request.form['lat']
        lng = request.form['lng']
        alt = request.form['alt']
        form_timezone = request.form['form_timezone']

        if lat and lng and alt and form_timezone:
            # write local config file
            modify_env({'FEEDER_LAT': lat,
                        'FEEDER_LONG': lng,
                        'FEEDER_ALT': alt,
                        'FEEDER_TZ': form_timezone})
            return redirect('/restarting')

    return render_template('index.html', env_values=env_values, message=message)
