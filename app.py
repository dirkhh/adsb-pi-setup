from flask import Flask, render_template, request, url_for, flash, redirect
import subprocess
from os import urandom


def restart():
    subprocess.call("/usr/bin/systemctl restart adsb-docker", shell=True)


browser_timezone: str = 'Europe/Berlin'

app = Flask(__name__)
app.secret_key = urandom(16).hex()

@app.route('/propagateTZ')
def get_tz():
    brower_timezone = request.args.get("tz")
    print(f'get_tz called with {browser_timezone}')
    return render_template('index.html', browser_timezone=browser_timezone)

@app.route('/', methods=('GET', 'POST'))
def setup():
    if request.method == 'POST':
        lat = request.form['lat']
        lng = request.form['lng']
        alt = request.form['alt']
        form_timezone = request.form['form_timezone']

        if lat and lng and alt:
            # write local config file
            with open('/opt/adsb/.web-setup.env', 'w') as env_file:
                env_file.write('# adsb-pi feeder environment, written by the web config\n')
                env_file.write(f"FEEDER_LAT={lat}\n")
                env_file.write(f"FEEDER_LONG={lng}\n")
                env_file.write(f"FEEDER_ALT_M={alt}\n")
                env_file.write(f"FEEDER_TZ={form_timezone}\n")
            restart()

    return render_template('index.html', browser_timezone=browser_timezone)
