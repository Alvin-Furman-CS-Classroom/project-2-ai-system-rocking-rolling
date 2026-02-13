import requests
import json
import time

music_pieces = ["Bohemian Rhapsody",
    "Stairway to Heaven",
    "Imagine",
    "Hotel California",
    "Hey Jude",
    "Smells Like Teen Spirit",
    "Billie Jean",]

music_to_mbid = {"Bohemian Rhapsody" : "95ebc842-9926-4658-8012-12c358247946", 
                 "Stairway to Heaven" : "1726a15c-9841-4f83-8558-906be08cb283",
                 "Imagine" : "96d7d94f-cfa7-4f12-a184-de8f750a4e4d",
                 "Hotel California" : "6afe8845-7cb6-41fd-b13c-3e2492308956",
                 "Hey Jude" : "3c4d5e6f-7g8h-9i0j-1k2l-3m4n5o6p7q8",
                 "Smells Like Teen Spirit" : "ce731de4-ed4e-44f2-bf07-18e5e66d2bcc",
                 }

def get_song_json(song_name: str):
    # 1. Be VERY specific with your User-Agent.
    # MusicBrainz uses this to decide whether to block you.
    headers = {
        "User-Agent": "AcousticDataApp/1.0 (contact: your-github-username@users.noreply.github.com)",
        "Accept": "application/json"
    }

    print(f"Searching MusicBrainz for: {song_name}")

    mb_url = "https://musicbrainz.org/ws/2/recording"
    mb_params = {"query": song_name, "fmt": "json"}

    try:
        # 2. Add a tiny delay before the request to respect their 1-sec rule
        time.sleep(1.1)

        response = requests.get(mb_url, params=mb_params, headers=headers, timeout=15)
        response.raise_for_status()
        mb_data = response.json()

        if not mb_data.get("recordings"):
            print("No recordings found.")
            return None

        recording_id = mb_data["recordings"][0]["id"]
        print(f"Found MBID: {recording_id}")

        # 3. AcousticBrainz Fetch
        time.sleep(1.1) # Respect the rate limit again
        ab_url = f"https://acousticbrainz.org/api/v1/low-level"
        ab_params = {"recording_ids": recording_id}

        ab_response = requests.get(ab_url, params=ab_params, headers=headers, timeout=15)
        return ab_response.json()

    except requests.exceptions.ConnectionError as e:
        return f"Connection reset. MusicBrainz is likely blocking this Codespace IP. Error: {e}"
    except Exception as e:
        return f"An error occurred: {e}"

if __name__ == "__main__":
    for piece in music_pieces:
        result = get_song_json(piece)
        print(json.dumps(result, indent=2)[:500])
        print("\n\n")