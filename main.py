from flask import Flask, render_template
import requests

app = Flask(__name__)

@app.route("/")
def home():
    lat, lon = 58.69, 9.17  # координаты твоего фьорда
    url = f"https://marine-api.open-meteo.com/v1/marine?latitude={lat}&longitude={lon}&daily=sea_surface_temperature_mean&timezone=auto"
    data = requests.get(url).json()

    if "daily" in data:
        temp_water = data["daily"]["sea_surface_temperature_mean"][0]
    else:
        temp_water = "нет данных"

    return render_template("index.html", temp_water=temp_water, lat=lat, lon=lon)

if __name__ == "__main__":
    app.run(debug=True)
