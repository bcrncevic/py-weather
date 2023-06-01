from flask import Flask, render_template, request, session, redirect
from datetime import datetime
import os
import pandas as pd
import requests
import sqlite3

app = Flask(__name__)
app.secret_key = 'tajni_kljuc'
app.config["TEMPLATES_AUTO_RELOAD"] = True

os.makedirs('static/img', exist_ok=True)

conn = sqlite3.connect('users.db')
cursor = conn.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        password TEXT NOT NULL
    )
""")

cursor.execute("""
    INSERT INTO users (username, password)
    VALUES ('admin', 'password')
""")

conn.commit()
conn.close()

def dohvati_vrijeme(api_kljuc, grad, dani):
    url = f'http://api.weatherapi.com/v1/forecast.json?key={api_kljuc}&q={grad}&days={dani}'
    odgovor = requests.get(url)
    podaci = odgovor.json()
    return podaci

@app.route('/', methods=['GET', 'POST'])
def vrijeme():
    api_kljuc = '7804b2a270004982821182131230106'
    grad = request.form.get('grad') or 'Split'

    # Dohvaćanje podataka za vremensku prognozu za danas
    try:
        trenutni_podaci = dohvati_vrijeme(api_kljuc, grad, 8)
    except requests.exceptions.RequestException:
        return render_template('index.html', greska='Došlo je do pogreške prilikom dohvata podataka. Molimo pokušajte ponovno.')

    if 'error' in trenutni_podaci:
        return render_template('index.html', greska='Nema podataka za navedeni grad. Molimo provjerite unos i pokušajte ponovno.')
    
    trenutna_temperatura = trenutni_podaci['current']['temp_c']
    trenutni_uvjeti = trenutni_podaci['current']['condition']['text']
    grad = trenutni_podaci['location']['name']

    # Dohvaćanje podataka za vremensku prognozu za sljedeća tri dana
    prognoza_podaci = dohvati_vrijeme(api_kljuc, grad, 4)['forecast']['forecastday'][1:]
    prognoza = []
    for dan in prognoza_podaci:
        datum_objekt = datetime.strptime(dan['date'], '%Y-%m-%d')
        datum = datum_objekt.strftime('%d.%m')
        prosjecna_temperatura = dan['day']['avgtemp_c']
        ukupne_oborine = dan['day']['totalprecip_mm']
        prosjecni_tlak = dan['day']['avgtemp_c']
        brzina_vjetra = dan['day']['maxwind_kph']
        smjer_vjetra = dan['day']['wind_dir'] if 'wind_dir' in dan['day'] else 'N/A'
        uvjeti = dan['day']['condition']['text']
        ikona = dan['day']['condition']['icon']
        prognoza.append({
            'datum': datum,
            'prosjecna_temperatura': prosjecna_temperatura,
            'ukupne_oborine': ukupne_oborine,
            'prosjecni_tlak': prosjecni_tlak,
            'brzina_vjetra': brzina_vjetra,
            'smjer_vjetra': smjer_vjetra,
            'uvjeti': uvjeti,
            'ikona': ikona
        })

    # Dohvaćanje podataka za vremensku prognozu za sljedećih 7 dana
    tjedni_podaci = dohvati_vrijeme(api_kljuc, grad, 8)['forecast']['forecastday'][1:]
    tjedna_prognoza = []
    for dan in tjedni_podaci:
        datum_objekt = datetime.strptime(dan['date'], '%Y-%m-%d')
        datum = datum_objekt.strftime('%d.%m')
        prosjecna_temperatura = dan['day']['avgtemp_c']
        ikona = dan['day']['condition']['icon']
        tjedna_prognoza.append({
            'datum': datum,
            'prosjecna_temperatura': prosjecna_temperatura,
            'ikona': ikona
        })

    prognoza_df = pd.DataFrame(prognoza)
    tjedna_prognoza_df = pd.DataFrame(tjedna_prognoza)

    prognoza_chart = prognoza_df.plot(x='datum', y='prosjecna_temperatura', kind='line', legend=False)
    prognoza_chart.set_xlabel('Datum')
    prognoza_chart.set_ylabel('Prosjek temperature (°C)')
    prognoza_chart.set_title('Prognoza za sljedeća tri dana')

    tjedna_prognoza_chart = tjedna_prognoza_df.plot(x='datum', y='prosjecna_temperatura', kind='line', legend=False)
    tjedna_prognoza_chart.set_xlabel('Datum')
    tjedna_prognoza_chart.set_ylabel('Prosjek temperature (°C)')
    tjedna_prognoza_chart.set_title('Prognoza za sljedećih sedam dana')

    prognoza_slika = prognoza_chart.get_figure()
    prognoza_slika_path = 'static/img/prognoza.png'
    prognoza_slika.savefig(prognoza_slika_path)
    tjedna_prognoza_slika = tjedna_prognoza_chart.get_figure()
    tjedna_prognoza_slika_path = 'static/img/tjedna_prognoza.png'
    tjedna_prognoza_slika.savefig(tjedna_prognoza_slika_path)

    return render_template('index.html', grad=grad, trenutna_temperatura=trenutna_temperatura,
                           trenutni_uvjeti=trenutni_uvjeti, prognoza=prognoza,
                           tjedna_prognoza=tjedna_prognoza, prognoza_slika_path=prognoza_slika_path,
                           tjedna_prognoza_slika_path=tjedna_prognoza_slika_path)

    try:
        response = requests.get(url)
        data = response.json()

        # Provjera uspješnosti odgovora API-ja
        if 'error' in data:
            error_message = data['error']['message']
            return {'error': error_message}

        # Dohvaćanje relevantnih podataka o vremenskoj prognozi
        current_weather = data['current']
        temperature = current_weather['temp_c']
        wind = current_weather['wind_kph']
        humidity = current_weather['humidity']

        weather_data = {
            'city': 'Split',
            'temperature': temperature,
            'wind': wind,
            'humidity': humidity
        }

        return weather_data

    except requests.exceptions.RequestException as e:
        return {'error': str(e)}

@app.route('/')
def index():
    return vrijeme()

@app.route('/prijava', methods=['GET', 'POST'])
def prijava():
    if request.method == 'POST':
        # Logika za provjeru korisničkih podataka i prijavu
        username = request.form['username']
        lozinka = request.form['password']
        
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users WHERE username=?", (username,))
        korisnik = cursor.fetchone()
        
        if korisnik and korisnik[2] == lozinka:
            session['prijavljen'] = True
            return redirect('/')
        else:
            greska = 'Neispravno korisničko ime ili lozinka'
            return render_template('prijava.html', greska=greska)
    
    return render_template('prijava.html')

@app.route('/odjava')
def odjava():
    session.pop('prijavljen', None)
    return redirect('/')

if __name__ == '__main__':
    app.run()