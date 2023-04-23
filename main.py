import requests
import json
from os import environ as env
from urllib.parse import quote_plus, urlencode

from authlib.integrations.flask_client import OAuth
from dotenv import find_dotenv, load_dotenv
from flask import Flask, redirect, render_template, session, url_for, request

ENV_FILE = find_dotenv()
if ENV_FILE:
    load_dotenv(ENV_FILE)

app = Flask(__name__)
app.secret_key = env.get("APP_SECRET_KEY")

oauth = OAuth(app)

oauth.register(
    "auth0",
    client_id=env.get("AUTH0_CLIENT_ID"),
    client_secret=env.get("AUTH0_CLIENT_SECRET"),
    client_kwargs={
        "scope": "openid profile email",
    },
    server_metadata_url=f'https://{env.get("AUTH0_DOMAIN")}/.well-known/openid-configuration',
)


# Controllers API
@app.route("/")
def home():
    return render_template(
        "index.html",
        current_user=session.get("user")
    )


@app.route("/callback", methods=["GET", "POST"])
def callback():
    token = oauth.auth0.authorize_access_token()
    session["user"] = token
    return redirect("/")


@app.route("/login")
def login():
    return oauth.auth0.authorize_redirect(
        redirect_uri=url_for("callback", _external=True)
    )


@app.route("/logout")
def logout():
    session.clear()
    return redirect(
        "https://"
        + env.get("AUTH0_DOMAIN")
        + "/v2/logout?"
        + urlencode(
            {
                "returnTo": url_for("home", _external=True),
                "client_id": env.get("AUTH0_CLIENT_ID"),
            },
            quote_via=quote_plus,
        )
    )


@app.route("/feed_me", methods=['GET', 'POST'])
def feed_me():
    current_user = session.get('user')
    if current_user:

        if request.method == 'POST':
            loc = request.form['location']
            if "$" in loc:
                lat = loc.split("$")[0]
                lon = loc.split("$")[1]
                response = requests.get(
                    f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={env.get('OW_API_KEY')}"
                )
                weather_data = response.json()
            else:
                # Fetching latitude and logitude from geocoding api
                geo_response = requests.get(
                    f"http://api.openweathermap.org/geo/1.0/direct?q={loc}&limit=1&appid={env.get('OW_API_KEY')}"
                )
                data = geo_response.json()
                lat = data[0]["lat"]
                lon = data[0]["lon"]
                response = requests.get(
                    f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={env.get('OW_API_KEY')}"
                )
                weather_data = response.json()
            # extracting relevant data from the openweather api response
            temperature = weather_data["main"]["temp"]
            description = weather_data["weather"][0]["description"]

            # Suggest ingredients based on the current weather conditions
            if temperature < 10:
                suggested_ingredients = ["potatoes", "carrots", "onions", "beef"]
            elif temperature < 20:
                suggested_ingredients = ["chicken", "rice", "beans", "tomatoes", 'salads']
            else:
                suggested_ingredients = ["lettuce", "spinach", "cucumber", "avocado"]

            # print(suggested_ingredients, "\n", description, "\n\n\n", weather_data)
            # print(",".join(suggested_ingredients))

            recipe_response = requests.get(
                'https://api.edamam.com/api/recipes/v2',
                params={
                    'type': "public",
                    'q': ",".join(suggested_ingredients),
                    'app_id': env.get('RECIPE_APP_ID'),
                    'app_key': env.get('RECIPE_APP_KEY'),
                    'random': "true"
                }
            )
            recipe_data = recipe_response.json()
            print("\n\n", recipe_data["hits"][0])
            uri = recipe_data["hits"][0]['recipe']['uri']
            img = recipe_data["hits"][0]['recipe']['image']
            label = recipe_data["hits"][0]['recipe']['label']
            ingredients = recipe_data["hits"][0]['recipe']['ingredientLines']

            return render_template('recipe.html', ingredients=ingredients, img=img, label=label)
        else:
            return render_template(
                "feed_me.html",
                current_user=session.get('user')
            )
    else:
        return redirect("/login")


@app.route('/recipe')
def recipe():
    current_user = session.get('user')
    if current_user:
        return render_template("recipe.html", uri=uri, )
    else:
        return redirect("/login")


@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=env.get("PORT", 3000), debug=True)
