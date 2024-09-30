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


class SpotifyAPIError(Exception):
    def __init__(self, message, status_code):
        super().__init__(message)
        self.status_code = status_code


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


def get_recommended_tracks(headers, recommendations_params):
    response = requests.get(
        RECOMMENDATIONS_URL, headers=headers, params=recommendations_params, timeout=5
    )

    if response.status_code != 200:
        raise SpotifyAPIError(
            f"Something went wrong on Spotify's side:\nCode: {response.status_code}\nMessage: {response.text}",
            response.status_code,
        )

    recommendations = response.json()
    recommended_track_uris = [track["uri"] for track in recommendations["tracks"]]
    return recommended_track_uris


def create_playlist(headers, genres_metadata, tempo_metadata):
    playlist_data = {
        "name": f"Generated Playlist: {genres_metadata} - Tempo {tempo_metadata} BPM",
        "description": f"A playlist with songs around {tempo_metadata} BPM",
        "public": False,
    }

    user_profile_response = requests.get(
        f"{SPOTIFY_API_URL}/me", headers=headers, timeout=5
    )

    if user_profile_response.status_code != 200:
        raise SpotifyAPIError(
            f"Something went wrong on Spotify's side:\nCode: {user_profile_response.status_code}\nMessage: {user_profile_response.text}",
            user_profile_response.status_code,
        )

    user_profile = user_profile_response.json()
    user_id = user_profile["id"]

    playlist_creation_response = requests.post(
        f"{SPOTIFY_API_URL}/users/{user_id}/playlists",
        headers=headers,
        json=playlist_data,
        timeout=5,
    )

    if playlist_creation_response.status_code != 201:
        raise SpotifyAPIError(
            f"Something went wrong on Spotify's side:\nCode: {playlist_creation_response.status_code}\nMessage: {playlist_creation_response.text}",
            playlist_creation_response.status_code,
        )

    playlist = playlist_creation_response.json()
    return playlist


def add_tracks(headers, track_uris, playlist):
    add_tracks_url = f"{SPOTIFY_API_URL}/playlists/{playlist['id']}/tracks"
    add_tracks_response = requests.post(
        add_tracks_url, headers=headers, json={"uris": track_uris}, timeout=5
    )
    if add_tracks_response.status_code != 201:
        raise SpotifyAPIError(
            f"Something went wrong on Spotify's side:\nCode: {add_tracks_response.status_code}\nMessage: {add_tracks_response.text}",
            add_tracks_response.status_code,
        )


@app.route("/generate_playlist", methods=["POST"])
def generate_playlist():
    access_token = session.get("access_token")

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    recommendations_params = construct_recommendations_params(request.form)

    try:
        track_uris = get_recommended_tracks(headers, recommendations_params)

        playlist = create_playlist(
            headers,
            genres_metadata=recommendations_params["seed_genres"],
            tempo_metadata=recommendations_params["target_tempo"],
        )
        add_tracks(headers, track_uris, playlist)
    except SpotifyAPIError as e:
        return str(e), e.status_code

    return render_template(
        "success.html", playlist_url=playlist["external_urls"]["spotify"]
    )


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=8888)
