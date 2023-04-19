from flask import Flask, render_template, request, url_for, flash, redirect
import subprocess
from os import urandom,path


system_file: str = "/opt/adsb/.env"
web_file: str = "/opt/adsb/.web-setup.env"

def parse_env_files():
    _env_values = {}
    for env_file in [ system_file, web_file ]:
        if not path.isfile(env_file):
            continue
        with open(env_file) as f:
            for line in f:
                if line.strip().startswith('#'):
                    continue
                key, var = line.partition("=")[::2]
                _env_values[key.strip()] = var.strip()
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
    env_values['FEEDER_TZ'] = browser_timezone
    return render_template('index.html', env_values=env_values)

@app.route('/restarting', methods=('GET', 'POST'))
def restarting():
    if request.method == 'POST':
        restart()
        return "done"
    if request.method == 'GET':
        return render_template('restarting.html')

@app.route('/', methods=('GET', 'POST'))
def setup():
    message = ""
    if request.args.get("success"):
        message = "Restarting the ADSB app completed"
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
                env_file.write(f"FEEDER_LAT={lat}\n")
                env_file.write(f"FEEDER_LONG={lng}\n")
                env_file.write(f"FEEDER_ALT_M={alt}\n")
                env_file.write(f"FEEDER_TZ={form_timezone}\n")
            return redirect('/restarting')

    return render_template('index.html', env_values=env_values, message=message)
