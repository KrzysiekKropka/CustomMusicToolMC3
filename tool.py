import os
import json
import subprocess
import re
import platform

BASE_FOLDER = os.getcwd()
TOOLS_FOLDER = os.path.join(BASE_FOLDER, "external_tools")
MUSIC_FOLDER = os.path.join(BASE_FOLDER, "STREAMS", "Music")
PLAY_FOLDER = os.path.join(BASE_FOLDER, "ASSETS", "tune", "audio", "playlist", "city", "sd", "music")
STRTBL_FOLDER = os.path.join(BASE_FOLDER, "ASSETS", "fonts")
SD_PLAY_FILE = os.path.join(PLAY_FOLDER, "sd.play")
STRTBL_FILE = os.path.join(STRTBL_FOLDER, "mcstrings02.strtbl")
STRTBL_JSON = os.path.join(STRTBL_FOLDER, "mcstrings02.json")

if platform.system() == "Windows":
    ffmpeg_bin = os.path.join(TOOLS_FOLDER, "ffmpeg.exe")
else:
    ffmpeg_bin = "ffmpeg"

genre_race_map = {
    "HipHop": "rap_race_music.play",
    "Rock": "pop_race_music.play",
    "Dancehall": "dance_hall_race_music.play",
    "Techno": "techno_race_music.play",
    "Drum_N_Bass": "drums_bass_race_music.play",
    "Instrumental": "garage.play"
}

LANGUAGES = [
    "Language 00", "Language 01", "Language 02",
    "Language 03", "Language 04", "Language 05"
]

LANGUAGE_TEXTS = ["by", "de", "par", "von", "di", "by"]

FONT_TEMPLATE = {"name": "smallspace", "scale32": [1.0, 1.0], "scale8": [0, 0], "size": 15}

RED = "\033[31m"
GREEN = "\033[32m"
BLUE = "\033[34m"
YELLOW = "\033[33m"
RESET = "\033[0m"

# === 1. Decompile existing DAT files ===
def decompile_dat_files():
    if os.path.exists(os.path.join(BASE_FOLDER, "ASSETS.DAT")):
        print(f"{YELLOW}Decompiling ASSETS.DAT...{RESET}")
        subprocess.run(["python", os.path.join(TOOLS_FOLDER, "dave.py"), "X", "ASSETS.DAT"], check=True)

    if os.path.exists(os.path.join(BASE_FOLDER, "STREAMS.DAT")):
        print(f"{YELLOW}Decompiling STREAMS.DAT...{RESET}")
        subprocess.run(["python", os.path.join(TOOLS_FOLDER, "hash_build.py"), "X", "STREAMS.DAT", "-nl", os.path.join(TOOLS_FOLDER, "STREAMS.LST"), "-a", "mclub", "-th", "45"], check=True)


# === 2. Convert STRTBL to JSON if needed ===
def convert_strtbl_to_json():
    if os.path.exists(STRTBL_FILE) and not os.path.exists(STRTBL_JSON):
        print(f"{YELLOW}Converting mcstrings02.strtbl → mcstrings02.json{RESET}")
        subprocess.run(["python", os.path.join(TOOLS_FOLDER, "strtbl.py"), "dec", STRTBL_FILE], check=True)
        os.remove(STRTBL_FILE)


# === 3. Load existing JSON (songs text entries) ===
def load_song_dict():
    if os.path.exists(STRTBL_JSON):
        with open(STRTBL_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

# === Helper for 4 and 5
def name_splitting(name):
    artist, song = name.split(' - ', 1)

    feat_match = re.search(r"\((feat\.|ft\.)\s*([^)]+)\)", song, flags=re.IGNORECASE)
    if feat_match:
        featured = feat_match.group(2).strip()
        # Append feat. to artist name
        artist = f"{artist} feat. {featured}"
        # Remove the (feat. ...) from the song title
        song = re.sub(r"\((feat\.|ft\.)\s*[^)]+\)", "", song, flags=re.IGNORECASE).strip()

    return artist, song

# === 4. List new songs in STREAMS/Music ===
def list_new_songs():
    number = 0
    print("")
    for genre in os.listdir(MUSIC_FOLDER):
        genre_path = os.path.join(MUSIC_FOLDER, genre)
        if not os.path.isdir(genre_path):
            continue

        for filename in os.listdir(genre_path):
            file_path = os.path.join(genre_path, filename)
            if not os.path.isfile(file_path) or filename.startswith('.'):
                continue

            name, ext = os.path.splitext(filename)
            if ' - ' in name:
                print(f"{GREEN}Found a song: {filename}", end=". ")
                number+=1
                artist, song = name_splitting(name)
            else:
                continue

            print(f"{RESET}Will be {song} by {artist}")
    return(number)
            

# === 5. Process songs in STREAMS/Music ===
def process_music_files(song_dict):
    new_playlist_songs = []
    genre_songs = {}

    existing_playlist_songs = set()
    if os.path.exists(SD_PLAY_FILE):
        with open(SD_PLAY_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if not line.startswith("num_songs:"):
                    existing_playlist_songs.add(line.strip())

    for genre in os.listdir(MUSIC_FOLDER):
        genre_path = os.path.join(MUSIC_FOLDER, genre)
        if not os.path.isdir(genre_path):
            continue

        for filename in os.listdir(genre_path):
            file_path = os.path.join(genre_path, filename)
            if not os.path.isfile(file_path) or filename.startswith('.'):
                continue

            name, ext = os.path.splitext(filename)
            if ' - ' not in name:
                continue

            artist, song = name_splitting(name)

            # Rename files to not have whitespaces or special symbols
            artist_nospace = re.sub(r"[^\w]", "", artist) 
            song_nospace = re.sub(r"[^\w]", "", song)

            new_name_safe = f"{artist_nospace}_{song_nospace}{ext}"
            new_path = os.path.join(genre_path, new_name_safe)
            os.rename(file_path, new_path)

            json_key = f"music_{genre}_{artist_nospace}_{song_nospace}"

            if json_key not in song_dict["data"]:
                song_dict["data"][json_key] = {}
                for lang, text_prefix in zip(LANGUAGES, LANGUAGE_TEXTS):
                    song_dict["data"][json_key][lang] = {
                        "text": f"\"{song}\"\n{text_prefix} {artist}",
                        "font": FONT_TEMPLATE
                    }

            playlist_song = f"music\\{genre}\\{artist_nospace}_{song_nospace}"
            if playlist_song not in existing_playlist_songs:
                new_playlist_songs.append(playlist_song)
                existing_playlist_songs.add(playlist_song)

            genre_songs.setdefault(genre, []).append(playlist_song)

    return song_dict, new_playlist_songs, genre_songs


# === 6. Update sd.play and per-genre race files ===
def update_playlists(new_playlist_songs, genre_songs, song_dict):
    # sd.play
    sd_play_lines = []
    if os.path.exists(SD_PLAY_FILE):
        with open(SD_PLAY_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("num_songs:"):
                    sd_play_lines.append(line)

    for line in new_playlist_songs:
        if line not in sd_play_lines:
            sd_play_lines.append(line)

    with open(SD_PLAY_FILE, "w", encoding="utf-8") as f:
        f.write(f"num_songs: {len(sd_play_lines)}\n")
        for line in sd_play_lines:
            f.write(line + "\n")

    # genre race files
    for genre, songs in genre_songs.items():
        race_file_name = os.path.join(
            PLAY_FOLDER,
            genre_race_map.get(genre, f"{genre.lower()}_race_music.play")
        )

        existing_lines = []
        if os.path.exists(race_file_name):
            with open(race_file_name, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("num_songs:"):
                        existing_lines.append(line)

        for song in songs:
            if song not in existing_lines:
                existing_lines.append(song)

        with open(race_file_name, "w", encoding="utf-8") as f:
            f.write(f"num_songs: {len(existing_lines)}\n")
            for line in existing_lines:
                f.write(line + "\n")

    # update JSON
    with open(STRTBL_JSON, "w", encoding="utf-8") as f:
        json.dump(song_dict, f, ensure_ascii=False, indent=4)


# === 7. Convert json to strtbl ===
def convert_json_to_strtbl():
    print(f"{YELLOW}Converting mcstrings02.json → mcstrings02.strtbl{RESET}")
    subprocess.run(["python", os.path.join(TOOLS_FOLDER, "strtbl.py"), "enc", STRTBL_JSON], check=True)
    os.remove(STRTBL_JSON)

# === 8. Build RSTM files from audio ===
def build_rstm_files():
    for genre in os.listdir(MUSIC_FOLDER):
        genre_path = os.path.join(MUSIC_FOLDER, genre)
        if not os.path.isdir(genre_path):
            continue

        for filename in os.listdir(genre_path):
            file_path = os.path.join(genre_path, filename)
            name, ext = os.path.splitext(filename)

            if filename.startswith('.') or not os.path.isfile(file_path) or ext.lower() == '.rsm':
                continue

            artist_song = name
            wav_path = file_path
            original_file = None

            # Convert to WAV
            if ext.lower() != '.wav':
                wav_path = os.path.join(genre_path, f"{artist_song}.wav")
                if not os.path.exists(wav_path):
                    print(f"{YELLOW}Converting {filename} → {artist_song}.wav")
                    subprocess.run([
                        ffmpeg_bin, '-y', '-i', file_path,
                        '-ac', '2', '-ar', '44100', '-acodec', 'pcm_s16le',
                        wav_path
                    ], check=True)
                original_file = file_path

            # Build RSTM
            rsm_path = os.path.join(genre_path, f"{artist_song}.rsm")
            print(f"{YELLOW}Building RSTM for {artist_song}.wav")
            subprocess.run(['python', os.path.join(TOOLS_FOLDER, "rstm_build.py"), wav_path], check=True)

            # Cleanup
            if original_file and os.path.exists(original_file):
                os.remove(original_file)
            if os.path.exists(wav_path):
                os.remove(wav_path)


# === 9. Compile back into DATs ===
def compile_back():
    print(f"{YELLOW}Compiling ASSETS.DAT...{RESET}")
    subprocess.run(["python", os.path.join(TOOLS_FOLDER, "dave.py"), "B", "-ca", "-cn", "-cf", "-fc", "1", "ASSETS", "ASSETS.DAT"], check=True)

    print(f"{YELLOW}Compiling STREAMS.DAT...{RESET}")
    subprocess.run(["python", os.path.join(TOOLS_FOLDER, "hash_build.py"), "B", "STREAMS", "STREAMS.DAT", "-a", "MClub"], check=True)


def main():
    if os.path.exists(os.path.join(BASE_FOLDER, "ASSETS.DAT")) or os.path.exists(os.path.join(BASE_FOLDER, "STREAMS.DAT")):
        answer = input(f"{BLUE}Do you want to decode STREAMS.DAT and ASSETS.DAT?{RESET} (Y/N): ").strip().lower()
        if answer == "y": 
            decompile_dat_files()
    if not os.path.exists(MUSIC_FOLDER) or not os.path.exists(PLAY_FOLDER) or not os.path.exists(STRTBL_FOLDER):
        print(f"\n{RED}Ain't shit to change! I need STREAMS and ASSETS. Either add them already decoded or in .DAT format.")
        return
    convert_strtbl_to_json()
    song_dict = load_song_dict()
    answer = input(f"\n{BLUE}Now is the time to add new songs to STREAMS/Music/[genre].{RESET}\nThe file format must be [Artist] - [Name].[ext]. Write REAL BIG once you're ready: ").strip().lower()
    if answer == "real big": 
        if list_new_songs() != 0:
            answer = input(f"\n{BLUE}Is the list of all new songs complete?{RESET}\nWrite DICK REAL BIG once you're ready: ").strip().lower()
            if answer == "dick real big": 
                song_dict, new_playlist_songs, genre_songs = process_music_files(song_dict)
                update_playlists(new_playlist_songs, genre_songs, song_dict)
                convert_json_to_strtbl()
                build_rstm_files()

                answer = input(f"\n{BLUE}Do you want to encode back into STREAMS.DAT and ASSETS.DAT?{RESET}\nOnly do it if the ASSETS and STREAMS folders aren't missing any files (Y/N): ").strip().lower()
                if answer == "y":
                    compile_back()
        else:
            answer = input(f"\n{BLUE}The script didn't find any new songs with format [artist] - [song].[ext].{RESET}\nDo you still want to continue? Write DICK REAL SMALL once you're ready: ").strip().lower()
            if answer == "dick real small": 
                song_dict, new_playlist_songs, genre_songs = process_music_files(song_dict)
                update_playlists(new_playlist_songs, genre_songs, song_dict)
                convert_json_to_strtbl()
                build_rstm_files()

                answer = input(f"\n{BLUE}Do you want to encode back into STREAMS.DAT and ASSETS.DAT?{RESET}\nOnly do it if the ASSETS and STREAMS folders aren't missing any files (Y/N): ").strip().lower()
                if answer == "y":
                    compile_back()


if __name__ == "__main__":
    main()
