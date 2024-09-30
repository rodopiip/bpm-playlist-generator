# Spotify BPM playlist generator

A simple Flask App that generates you a Spotify playlist based on prefered BPM (min-max-target) and a [genre seed](https://gist.github.com/drumnation/91a789da6f17f2ee20db8f55382b6653#file-genre-seeds-json)

![image](https://github.com/user-attachments/assets/a2296fb4-5910-4d3d-9b2d-643903e4a5d0)

## Dependencies

All necessary dependencies can be installed with:

```bash
pip3 install -r requirements.txt
```

## Deployment

## Secrets

You need to export the following environment variables before running the app:

- SPOTIFY_CLIENT_ID
- SPOTIFY_CLIENT_SECRET
- SPOTIFY_REDIRECT_URI

All of these can be configured/found in your Spotify App dashboard.

### Docker secrets

The client id and secret can alternatively be provided via a docker secret. The app will check for the existence of:

- /run/secrets/spotify_client_id
- /run/secrets/spotify_client_secret

Which is the path naming scheme used for docker secrets. If those files are not found, it will fall back to the environment variables described above.

## Running in debug mode

To run in debug mode, set SPOTIFY_REDIRECT_URI to "http://localhost:8888" and run:

```bash
python3 app.py
```

## Running in production via gunicorn

```bash
gunicorn app:app
```

## Running in production via the pre-built docker image

This repository provides pre-built docker images from the main branch. You can use those to run the app directy

```bash
docker run -p 8888:8888 \
-e SPOTIFY_CLIENT_ID="<CLIENT_ID>" \
-e SPOTIFY_CLIENT_SECRET="<CLIENT_SECRET>" \
-e SPOTIFY_REDIRECT_URI="<CALLBACK_URI>" \
-it ghcr.io/vasilvas99/bpm-playlist-generator/bpm-playlist-generator:latest
```

## Contributors

- [@rodopiip](https://github.com/rodopiip) -> Idea, Testing

- [@DimitarIVnov](https://github.com/DimitarIVnov) -> Front End

- [@vasilvas99](https://github.com/vasilvas99) -> Whatever is left
