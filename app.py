from flask import Flask, render_template, request, url_for, flash, redirect
import subprocess
from os import urandom,path
import re


system_file: str = "/opt/adsb/.env"
web_file: str = "/opt/adsb/.web-setup.env"
adv_file: str = "/opt/adsb/.adv-setup.env"


def parse_env_files():
    _env_values = {}
    for env_file in [ system_file, web_file, adv_file ]:
        if not path.isfile(env_file):
            continue
        with open(env_file) as f:
            for line in f:
                if line.strip().startswith('#'):
                    continue
                key, var = line.partition("=")[::2]
                _env_values[key.strip()] = var.strip()
    if 'READSB_NET_CONNECTOR' not in _env_values: _env_values['READSB_NET_CONNECTOR'] = ''
    if 'MLAT_CONFIG' not in _env_values: _env_values['MLAT_CONFIG'] = ''
    if 'route' not in _env_values: _env_values['route'] = ''
    if 'READSB_LAT' in _env_values and float(_env_values['READSB_LAT']) != 0.0 and \
            'READSB_LONG' in _env_values and float(_env_values['READSB_LONG']) != 0.0 and \
            'READSB_ALT' in _env_values and int(_env_values['READSB_ALT']) != 0:
        _env_values['adv_visible'] = 'visible'
    else:
        _env_values['adv_visible'] = 'invisible'

    return _env_values


def restart():
    subprocess.call("/usr/bin/systemctl restart adsb-docker", shell=True)


browser_timezone: str = 'Europe/Berlin'

app = Flask(__name__)
app.secret_key = urandom(16).hex()

@app.route('/propagateTZ')
def get_tz():
    brower_timezone = request.args.get("tz")
    print(f'get_tz called with {browser_timezone}')
    env_values = parse_env_files()
    env_values['TZ'] = browser_timezone
    return render_template('index.html', env_values=env_values)

@app.route('/restarting', methods=('GET', 'POST'))
def restarting():
    if request.method == 'POST':
        restart()
        return "done"
    if request.method == 'GET':
        return render_template('restarting.html')

@app.route('/advanced', methods=('GET', 'POST'))
def advanced():
    if request.method == 'POST':
        # explicitly make these empty
        route = mlat = net = ''
        if request.form.get('route', True):
            route = '1'
        if request.form.get('adsblol', True):
            if net: net += ';'
            if mlat: mlat += ';'
            net += 'in.adsb.lol,30004,beast_reduce_plus_out'
            mlat += 'in.adsb.lol,31090,39001'
        if request.form.get('adsbone', False):
            if net: net += ';'
            if mlat: mlat += ';'
            net += 'feed.adsb.one,64004,beast_reduce_plus_out'
            mlat += 'feed.adsb.one,64006,39002'
        if request.form.get('adsbfi', False):
            if net: net += ';'
            if mlat: mlat += ';'
            net += 'feed.adsb.fi,30004,beast_reduce_plus_out'
            mlat += 'feed.adsb.fi,31090,39000'
        if request.form.get('adsbx', False):
            if net: net += ';'
            if mlat: mlat += ';'
            net += 'feed1.adsbexchange.com,30004,beast_reduce_plus_out'
            mlat += 'feed.adsbexchange.com,31090,39005'
        if request.form.get('tat', True):
            if net: net += ';'
            if mlat: mlat += ';'
            net += 'feed.theairtraffic.com,30004,beast_reduce_plus_out'
            mlat += 'feed.theairtraffic.com,31090,39004'
        if request.form.get('ps', True):
            if net: net += ';'
            if mlat: mlat += ';'
            net += 'feed.planespotters.net,30004,beast_reduce_plus_out'
            mlat += 'mlat.planespotters.net,31090,39003'
        if mlat == '':   # things fail if those variables are empty
            net = 'in.adsb.lol,30004,beast_reduce_plus_out'
            mlat = 'in.adsb.lol,31090,39001'

        updated = []
        with open(adv_file, 'r') as afile:
            for line in afile:
                match = re.search('^[^#]*TAR1090_USEROUTEAPI[ \t]*=', line)
                if match:
                    continue
                match = re.search('^[^#]*READSB_NET_CONNECTOR[ \t]*=', line)
                if match:
                    continue
                match = re.search('^[^#]*MLAT_CONFIG[ \t]*=', line)
                if match:
                    continue
                updated.append(line)
        updated.append(f"TAR1090_USEROUTEAPI = {route}")
        updated.append(f"READSB_NET_CONNECTOR = {net}")
        updated.append(f"MLAT_CONFIG = {mlat}")
        with open(adv_file, 'w') as env_file:
            for line in updated:
                env_file.write(f"{line}\n")
        return redirect('/restarting')
    env_values = parse_env_files()
    env_values['route'] = 'checked' if env_values['TAR1090_USEROUTEAPI'] != '' else ''
    env_values['adsblol'] = 'checked' if 'adsb.lol' in env_values['READSB_NET_CONNECTOR'] else ''
    env_values['adsbone'] = 'checked' if 'adsb.one' in env_values['READSB_NET_CONNECTOR'] else ''
    env_values['adsbfi'] = 'checked' if 'adsb.fi' in env_values['READSB_NET_CONNECTOR'] else ''
    env_values['adsbx'] = 'checked' if 'adsbexchange' in env_values['READSB_NET_CONNECTOR'] else ''
    env_values['tat'] = 'checked' if 'theairtraffic' in env_values['READSB_NET_CONNECTOR'] else ''
    env_values['ps'] = 'checked' if 'planespotters' in env_values['READSB_NET_CONNECTOR'] else ''
    return render_template('advanced.html', env_values=env_values)
            

@app.route('/', methods=('GET', 'POST'))
def setup():
    message = ''
    if request.args.get("success"):
        # the message most likely will never be seen, because we immediately
        # redirect the user to the tar1090 website
        message = "Restarting the ADSB app completed"
        host, port = request.server
        tar1090 = request.url_root.replace(str(port), "8080")
        return redirect(tar1090)
    env_values = parse_env_files()
    if request.method == 'POST':
        lat = request.form['lat']
        lng = request.form['lng']
        alt = request.form['alt']
        form_timezone = request.form['form_timezone']

        if lat and lng and alt and form_timezone:
            # write local config file
            with open(web_file, 'w') as env_file:
                env_file.write('# adsb-pi feeder environment, written by the web config\n')
                env_file.write(f"READSB_LAT={lat}\n")
                env_file.write(f"READSB_LONG={lng}\n")
                env_file.write(f"READSB_ALT={alt}\n")
                env_file.write(f"TZ={form_timezone}\n")
            return redirect('/restarting')

    return render_template('index.html', env_values=env_values, message=message)
