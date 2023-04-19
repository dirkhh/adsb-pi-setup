from flask import Flask, render_template, request, url_for, flash, redirect

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/adsb-setup', methods=('GET', 'POST'))
def setup():
    if request.method == 'POST':
        lat = request.form['lat']
        lng = request.form['lng']
        alt = request.form['alt']

        if not lat:
            flash('Latitude is required!')
        if not lng:
            flash('Longitude is required!')
        if not alt:
            flash('Altitude is required!')

        if lat and lng and alt:
            # write local config file
            with open('/opt/adsb/.env', 'w') as env_file:
                env_file.write('# adsb-pi feeder environment, written by the web config')
                env_file.write(f"FEEDER_LAT={lat}")
                env_file.write(f"FEEDER_LONG={lng}")
                env_file.write(f"FEEDER_ALT_M={alt}")
            return render_template('alldone.html')

    return render_template('setup.html')
