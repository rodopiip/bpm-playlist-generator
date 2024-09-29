import os

import requests
from flask import Flask, redirect, render_template, request, session, url_for

app = Flask(__name__)
app.secret_key = os.urandom(24)

CLIENT_ID = os.environ.get("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.environ.get("SPOTIFY_CLIENT_SECRET")
REDIRECT_URI = os.environ.get("SPOTIFY_REDIRECT_URI")
SCOPE = "playlist-modify-public playlist-modify-private"
SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_URL = "https://api.spotify.com/v1"


@app.route("/")
def home():
    if "access_token" not in session:
        return render_template("login.html")
    return render_template("form.html")


@app.route("/login")
def login():
    auth_url = f"{SPOTIFY_AUTH_URL}?response_type=code&client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&scope={SCOPE}"
    return redirect(auth_url)


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
    )

    response_data = response.json()
    session["access_token"] = response_data["access_token"]
    session["refresh_token"] = response_data["refresh_token"]

    return redirect(url_for("home"))


@app.route("/generate_playlist", methods=["POST"])
def generate_playlist():
    access_token = session.get("access_token")

    genre = request.form["genre"].replace(" ", "").lower()
    min_tempo = int(request.form["min_tempo"])
    max_tempo = int(request.form["max_tempo"])
    target_tempo = int(request.form["target_tempo"])
    max_num_songs = int(request.form["max_num_songs"])

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    recommendations_url = f"{SPOTIFY_API_URL}/recommendations"
    if min_tempo == max_tempo:
        min_tempo = target_tempo - 1  # prevents empty responses by giving some leeway

    params = {
        "seed_genres": genre,
        "min_tempo": min_tempo,
        "max_tempo": max_tempo,
        "target_tempo": target_tempo,
        "limit": max_num_songs,  # Fetch 10 recommended tracks
    }

    response = requests.get(recommendations_url, headers=headers, params=params)
    recommendations = response.json()
    track_uris = [track["uri"] for track in recommendations["tracks"]]

    user_profile = requests.get(f"{SPOTIFY_API_URL}/me", headers=headers).json()
    user_id = user_profile["id"]

    playlist_data = {
        "name": f"Generated Playlist: {genre} - Tempo {target_tempo} BPM",
        "description": f"A playlist with songs between {min_tempo} and {max_tempo} BPM",
        "public": False,
    }

    playlist_response = requests.post(
        f"{SPOTIFY_API_URL}/users/{user_id}/playlists",
        headers=headers,
        json=playlist_data,
    )
    playlist = playlist_response.json()

    add_tracks_url = f"{SPOTIFY_API_URL}/playlists/{playlist['id']}/tracks"

    _add_tracks_response = requests.post(
        add_tracks_url, headers=headers, json={"uris": track_uris}
    )

    return render_template("success.html")


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=8888)
