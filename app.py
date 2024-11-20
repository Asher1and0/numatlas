import random
import phonenumbers
from phonenumbers import geocoder, parse, is_valid_number
import requests
import socket
from flask import Flask, render_template, request, session, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Ensure you have a secure secret key!

# Hardcoded credentials
USERNAME = 'shefa'
PASSWORD = '2882'

def generate_captcha():
    num1 = random.randint(1, 20)
    num2 = random.randint(1, 20)

    session['captcha_answer'] = num1 + num2
    return f"What is {num1} + {num2}?"

def get_phone_number_details(phone_number):
    try:
        parsed_number = parse(phone_number, None)
        if not is_valid_number(parsed_number):
            return {"error": "Invalid phone number"}
        region = geocoder.description_for_number(parsed_number, "en")
        formatted_number = phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
        return {"valid": True, "region": region, "formatted_number": formatted_number}
    except Exception as e:
        return {"error": str(e)}

def geocode_region_with_osm(region):
    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": region,
            "format": "json",
            "addressdetails": 1,
            "limit": 1
        }
        headers = {"User-Agent": "YourAppName/1.0 (your_email@example.com)"}
        response = requests.get(url, params=params, headers=headers)

        if response.status_code == 200:
            data = response.json()
            if data:
                osm_data = data[0]
                lat = osm_data.get('lat')
                lon = osm_data.get('lon')
                return osm_data, lat, lon
            else:
                return {"error": "No results found for the region"}, None, None
        else:
            return {"error": f"API error: {response.status_code}"}, None, None
    except Exception as e:
        return {"error": str(e)}, None, None

def get_ip_info(query):
    API_TOKEN = "25649308c3ff54"  
    BASE_URL = "https://ipinfo.io/"

    try:
        if not query.replace(".", "").isdigit():  
            query = socket.gethostbyname(query)
    except Exception as e:
        return f"Error resolving domain: {e}"

    try:
        response = requests.get(f"{BASE_URL}{query}", headers={"Authorization": f"Bearer {API_TOKEN}"}).json()
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        return f"Error fetching data from ipinfo.io: {e}"

    info = {
        "IP Address": query,
        "Country": response.get("country", "N/A"),
        "Region/State": response.get("region", "N/A"),
        "City": response.get("city", "N/A"),
        "ZIP/Postal Code": response.get("postal", "N/A"),
        "Time Zone": response.get("timezone", "N/A"),
        "Local Time": response.get("localtime", "N/A"),
        "IP Range": response.get("cidr", "N/A"),
        "Organization": response.get("org", "N/A"),
        "ISP": response.get("asn", {}).get("name", "N/A"),
    }

    loc = response.get('loc', '').split(',')
    lat, lon = loc[0] if loc else None, loc[1] if loc else None

    result = "\n".join([f"{key}: {value}" for key, value in info.items()])
    return result, lat, lon

@app.route('/', methods=['GET', 'POST'])
def index():
    if 'logged_in' in session:
        if request.method == 'POST':
            captcha_input = request.form.get('captcha')
            if captcha_input != str(session.get('captcha_answer')):
                return render_template('index.html', error="Incorrect CAPTCHA. Please try again.", captcha_question=generate_captcha())

            if 'phone_number' in request.form:
                phone_number = request.form['phone_number']
                phone_details = get_phone_number_details(phone_number)
                if "error" not in phone_details:
                    region = phone_details["region"]
                    osm_data, lat, lon = geocode_region_with_osm(region)
                    phone_details_str = format_output_as_list(phone_details)
                    osm_data_str = format_output_as_list(osm_data)
                    return render_template('index.html', phone_details=phone_details_str, osm_data=osm_data_str, lat=lat, lon=lon, captcha_question=generate_captcha())
                else:
                    return render_template('index.html', error=phone_details["error"], captcha_question=generate_captcha())

            if 'ip_query' in request.form:
                ip_query = request.form['ip_query']
                ip_info, lat, lon = get_ip_info(ip_query)
                return render_template('index.html', ip_info=ip_info, lat=lat, lon=lon, captcha_question=generate_captcha())

        captcha_question = generate_captcha()
        return render_template('index.html', captcha_question=captcha_question)
    
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username == USERNAME and password == PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password!', 'error')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

def format_output_as_list(data):
    output = []
    for key, value in data.items():
        if isinstance(value, dict):  
            output.append(f"{key}:")
            for sub_key, sub_value in value.items():
                output.append(f"  {sub_key}: {sub_value}")
        elif isinstance(value, list):  
            output.append(f"{key}: {', '.join(value)}")
        else:
            output.append(f"{key}: {value}")
    return "\n".join(output)

if __name__ == '__main__':
    app.run(debug=False, port=5001)

