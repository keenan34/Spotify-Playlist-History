from dotenv import load_dotenv
import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from datetime import datetime

# Load environment variables from .env file
load_dotenv()

client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")
redirect_uri = "http://localhost:8888/callback"

scope = "user-read-recently-played playlist-modify-public playlist-modify-private"

sp = spotipy.Spotify(
    auth_manager=SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope=scope,
    )
)


def get_user_listening_history(max_tracks=100):
    listening_history = []
    seen_tracks = set()
    results = sp.current_user_recently_played(limit=50)

    while results and len(listening_history) < max_tracks:
        for item in results["items"]:
            if len(listening_history) >= max_tracks:
                break

            track = item["track"]
            tid = track["id"]
            if tid not in seen_tracks:
                seen_tracks.add(tid)
                listening_history.append(
                    {
                        "name": track["name"],
                        "artist": track["artists"][0]["name"],
                        "album": track["album"]["name"],
                        "played_at": item["played_at"],
                        "url": track["external_urls"]["spotify"],
                    }
                )

        if len(listening_history) < max_tracks and results.get("next"):
            results = sp.next(results)
        else:
            break

    return listening_history


def create_playlist_from_history(file_path, user_id, playlist_name=None):
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    track_urls = [l.split("Listen: ")[1].strip() for l in lines if "Listen: " in l]
    if not track_urls:
        print("No track URLs found in the text file.")
        return

    name = playlist_name or "Listening History Playlist"
    playlist = sp.user_playlist_create(user=user_id, name=name, public=False)
    sp.playlist_add_items(playlist["id"], track_urls)
    print(f"Playlist '{playlist['name']}' created and tracks added successfully.")


if __name__ == "__main__":
    try:
        user = sp.current_user()
        user_id = user["id"]
        print(f"Authenticated as: {user['display_name']}")
    except Exception as e:
        print(f"Error during authentication: {e}")
        exit(1)

    history = get_user_listening_history(100)

    if history:
        file_path = "listening_history.txt"
        date_counts = {}

        with open(file_path, "w", encoding="utf-8") as f:
            for track in history:
                dt = datetime.fromisoformat(track["played_at"].replace("Z", "+00:00"))
                date_str = f"{dt.month}-{dt.day}-{dt.year % 100}"
                cnt = date_counts.get(date_str, 0) + 1
                date_counts[date_str] = cnt
                label = date_str if cnt == 1 else f"{date_str} #{cnt}"

                # write to file
                f.write(
                    f"{label}. {track['name']} by {track['artist']} (Album: {track['album']})\n"
                )
                f.write(f"Played at: {track['played_at']}\n")
                f.write(f"Listen: {track['url']}\n\n")

        # build playlist name with today’s date
        now = datetime.now()
        today_label = f"{now.month}-{now.day}-{now.year % 100}"
        playlist_name = f"Listening History {today_label}"

        print(f"Writing history and creating playlist named: '{playlist_name}'")
        create_playlist_from_history(file_path, user_id, playlist_name=playlist_name)
    else:
        print("No listening history found.")
