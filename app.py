import os

import requests
from flask import Flask, redirect, render_template, request, session, url_for
from get_docker_secret import get_docker_secret

app = Flask(__name__)
app.secret_key = os.urandom(24)

CLIENT_ID = get_docker_secret(
    "spotify_client_id", autocast_name=True, getenv=True, safe=False
)
CLIENT_SECRET = get_docker_secret(
    "spotify_client_secret", autocast_name=True, getenv=True, safe=False
)

# hard  crash if REDIRECT_URI is not set
REDIRECT_URI = os.environ["SPOTIFY_REDIRECT_URI"]
SCOPE = "playlist-modify-public playlist-modify-private"
SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_URL = "https://api.spotify.com/v1"
RECOMMENDATIONS_URL = f"{SPOTIFY_API_URL}/recommendations"
CLIENT_AUTH_URL = f"{SPOTIFY_AUTH_URL}?response_type=code&client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&scope={SCOPE}"


@app.route("/")
def home():
    if "access_token" not in session:
        return render_template("login.html")
    return render_template("form.html")


@app.route("/login")
def login():
    return redirect(CLIENT_AUTH_URL)


@app.route("/callback")
def callback():
    code = request.args.get("code")
    response = requests.post(
        SPOTIFY_TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        },
        timeout=5,
    )

    response_data = response.json()
    session["access_token"] = response_data["access_token"]
    session["refresh_token"] = response_data["refresh_token"]

    return redirect(url_for("home"))


# do  some input validation and prepare the request params
def construct_recommendations_params(form):
    genres = form["genre"].replace(" ", "").lower()
    min_tempo = form.get("min_tempo", None)
    max_tempo = form.get("max_tempo", None)
    target_tempo = int(form["target_tempo"])
    max_num_songs = int(form["max_num_songs"])

    min_tempo = int(min_tempo) if min_tempo else None
    max_tempo = int(max_tempo) if max_tempo else None

    if min_tempo is not None and max_tempo is not None:
        if min_tempo == max_tempo:
            min_tempo = max_tempo - 1  # prevents empty responses by giving some leeway
        elif min_tempo > max_tempo:
            min_tempo, max_tempo = (
                max_tempo,
                min_tempo,
            )  # swap if min_tempo is greater than max_tempo

    params = {}
    params["seed_genres"] = genres
    if min_tempo:
        params["min_tempo"] = min_tempo
    if max_tempo:
        params["max_tempo"] = max_tempo

    params["target_tempo"] = target_tempo
    params["limit"] = max_num_songs

    return params


@app.route("/generate_playlist", methods=["POST"])
def generate_playlist():
    access_token = session.get("access_token")

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    # prepare the recommendations
    recommendations_params = construct_recommendations_params(request.form)
    response = requests.get(
        RECOMMENDATIONS_URL, headers=headers, params=recommendations_params, timeout=5
    )
    recommendations = response.json()
    track_uris = [track["uri"] for track in recommendations["tracks"]]

    # prepare the playlist
    playlist_data = {
        "name": f"Generated Playlist: {recommendations_params['seed_genres']} - Tempo {recommendations_params['target_tempo']} BPM",
        "description": f"A playlist with songs around {recommendations_params['target_tempo']} BPM",
        "public": False,
    }

    user_profile = requests.get(
        f"{SPOTIFY_API_URL}/me", headers=headers, timeout=5
    ).json()
    user_id = user_profile["id"]

    playlist_creation_response = requests.post(
        f"{SPOTIFY_API_URL}/users/{user_id}/playlists",
        headers=headers,
        json=playlist_data,
        timeout=5,
    )

    if playlist_creation_response.status_code != 201:
        return "Something went wrong. Please try again."

    playlist = playlist_creation_response.json()

    # fill the playlist with the recommendations
    add_tracks_url = f"{SPOTIFY_API_URL}/playlists/{playlist['id']}/tracks"

    _add_tracks_response = requests.post(
        add_tracks_url, headers=headers, json={"uris": track_uris}, timeout=5
    )

    return render_template(
        "success.html", playlist_url=playlist["external_urls"]["spotify"]
    )


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=8888)
