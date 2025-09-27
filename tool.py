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
STRTBL2_FILE = os.path.join(STRTBL_FOLDER, "mcstrings02.strtbl")
STRTBL2_JSON = os.path.join(STRTBL_FOLDER, "mcstrings02.json")
STRTBL8_FILE = os.path.join(STRTBL_FOLDER, "mcstrings08.strtbl")
STRTBL8_JSON = os.path.join(STRTBL_FOLDER, "mcstrings08.json")

RED = "\033[31m"
GREEN = "\033[32m"
BLUE = "\033[34m"
YELLOW = "\033[33m"
RESET = "\033[0m"

if platform.system() == "Windows":
    ffmpeg_bin = os.path.join(TOOLS_FOLDER, "ffmpeg.exe")
else:
    if os.geteuid() != 0: input(f"{RED}It's recommended to run this tool as root, otherwise building rstm files might end with a crash due to a permission error.\n{RESET}Do you want to continue regardless? Press enter to continue: ")
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

# === 1. Decompile existing DAT files ===
def decompile_dat_files():
    if os.path.exists(os.path.join(BASE_FOLDER, "ASSETS.DAT")):
        print(f"{YELLOW}Decompiling ASSETS.DAT...{RESET}")
        subprocess.run(["python", os.path.join(TOOLS_FOLDER, "dave.py"), "X", "ASSETS.DAT"], check=True)

    if os.path.exists(os.path.join(BASE_FOLDER, "STREAMS.DAT")):
        print(f"{YELLOW}Decompiling STREAMS.DAT...{RESET}")
        subprocess.run(["python", os.path.join(TOOLS_FOLDER, "hash_build.py"), "X", "STREAMS.DAT", "-nl", os.path.join(TOOLS_FOLDER, "STREAMS.LST"), "-a", "mclub", "-th", "45"], check=True)


# === 2. Convert STRTBL to JSON ===
def convert_strtbl_to_json():
    if os.path.exists(STRTBL2_FILE) and not os.path.exists(STRTBL2_JSON):
        print(f"{YELLOW}Converting mcstrings02.strtbl → mcstrings02.json{RESET}")
        subprocess.run(["python", os.path.join(TOOLS_FOLDER, "strtbl.py"), "dec", STRTBL2_FILE], check=True)
        os.remove(STRTBL2_FILE)

    if os.path.exists(STRTBL8_FILE) and not os.path.exists(STRTBL8_JSON):
        print(f"{YELLOW}Converting mcstrings08.strtbl → mcstrings08.json{RESET}")
        subprocess.run(["python", os.path.join(TOOLS_FOLDER, "strtbl.py"), "dec", STRTBL8_FILE], check=True)
        os.remove(STRTBL8_FILE)


# === 3. Load existing JSON (songs text entries) <- no the fuck they ain't just that but okay ===
def load_song_dicts():
    song_dict2, song_dict8 = {}, {}

    if os.path.exists(STRTBL2_JSON):
        with open(STRTBL2_JSON, "r", encoding="utf-8") as f:
            song_dict2 = json.load(f)

    if os.path.exists(STRTBL8_JSON):
        with open(STRTBL8_JSON, "r", encoding="utf-8") as f:
            song_dict8 = json.load(f)

    return song_dict2, song_dict8

# === A name splitting helper function, also takes (feat.) from song titles and adds it to artist ===
def name_splitting(name):
    artist, song = name.split(' - ', 1)

    clean_artist = artist

    feat_match = re.search(r"\((feat\.|ft\.)\s*([^)]+)\)", song, flags=re.IGNORECASE)

    if feat_match:
        featured = feat_match.group(2).strip()
        artist = f"{artist} feat. {featured}"
        # Remove the (feat. ...) from the song title
        song = re.sub(r"\((feat\.|ft\.)\s*[^)]+\)", "", song, flags=re.IGNORECASE).strip()

    return artist, song, clean_artist

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
                print(f"{GREEN}Found a song in {genre}: {filename}", end=". ")
                artist, song, clean_artist = name_splitting(name)
                print(f"{RESET}Will be {song} by {artist}")
                number += 1
            else:
                continue

    return(number)

# === 5. Process songs in STREAMS/Music ===
def process_music_files(song_dict2, song_dict8):
    new_sdplay_songs = [] # "music\\HipHop\\Artist1_Song1", "music\\Rock\\Artist2_Song2", etc.
    genre_songs = {} # "Rock": ["music\\Rock\\Artist2_Song2", "music\\Rock\\Artist3_Song3"], "HipHop": [music\\HipHop\\Artist1_Song1, music\\HipHop\\Artist4_Song4]
    existing_sdplay_songs = set()

    if os.path.exists(SD_PLAY_FILE):
        with open(SD_PLAY_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if not line.startswith("num_songs:"):
                    existing_sdplay_songs.add(line.strip())

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

            artist, song, clean_artist = name_splitting(name)

            # Names with no spaces
            artist_nospace = re.sub(r"[^\w]", "", clean_artist) 
            song_nospace = re.sub(r"[^\w]", "", song)
            
            json_key = f"music_{genre}_{artist_nospace}_{song_nospace}"

            # For some dumb fucking reason, instrumentals use mcstrings08 instead of 02 like other songs
            target_dict = song_dict8 if genre.lower() == "instrumental" else song_dict2

            # ChatGPT is a pussy
            if "data" not in target_dict:
                target_dict["data"] = {}

            # Adds that song to either mcstrings02 or 08
            if json_key not in target_dict["data"]:
                target_dict["data"][json_key] = {}
                for lang, text_prefix in zip(LANGUAGES, LANGUAGE_TEXTS):
                    target_dict["data"][json_key][lang] = {
                        "text": f"\"{song}\"\n{text_prefix} {artist}",
                        "font": FONT_TEMPLATE
                    }

            # Playlist format of songs, for some reason they use backslashes
            sdplay_song = f"music\\{genre}\\{artist_nospace}_{song_nospace}"

            # Only add to sd.play if NOT instrumental
            if genre.lower() != "instrumental":
                if sdplay_song not in existing_sdplay_songs:
                    new_sdplay_songs.append(sdplay_song)
                    existing_sdplay_songs.add(sdplay_song)

            genre_songs.setdefault(genre, []).append(sdplay_song)

    return song_dict2, song_dict8, new_sdplay_songs, genre_songs

# === 6. Update sd.play and per-genre race files ===
def update_playlists(new_sdplay_songs, genre_songs, song_dict2, song_dict8):
    # sd.play
    sd_play_lines = []
    if os.path.exists(SD_PLAY_FILE):
        with open(SD_PLAY_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("num_songs:"):
                    sd_play_lines.append(line)

    for line in new_sdplay_songs:
        if line not in sd_play_lines:
            sd_play_lines.append(line)

    with open(SD_PLAY_FILE, "w", encoding="utf-8") as f:
        f.write(f"num_songs: {len(sd_play_lines)}\n")
        for line in sd_play_lines:
            f.write(line + "\n")

    # genre race files
    for genre, songs in genre_songs.items():
        targets = []

        # instrumentals are fucking stupid, every city has a different mandatory garage.play file 
        if genre.lower() == "instrumental":
            targets = [
                os.path.join(PLAY_FOLDER, "garage.play"),
                os.path.join(PLAY_FOLDER, "..", "..", "tokyo", "music", "garage.play"),
                os.path.join(PLAY_FOLDER, "..", "..", "detroit", "music", "garage.play"),
                os.path.join(PLAY_FOLDER, "..", "..", "atlanta", "music", "garage.play")
            ]
        else:
            targets = [
                os.path.join(
                    PLAY_FOLDER,
                    genre_race_map.get(genre, f"{genre.lower()}_race_music.play")
                )
            ]

        for race_file_name in targets:
            os.makedirs(os.path.dirname(race_file_name), exist_ok=True)

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
    with open(STRTBL2_JSON, "w", encoding="utf-8") as f:
        json.dump(song_dict2, f, ensure_ascii=False, indent=4)
        
    with open(STRTBL8_JSON, "w", encoding="utf-8") as f:
        json.dump(song_dict8, f, ensure_ascii=False, indent=4)


# === 7. Convert json to strtbl ===
def convert_json_to_strtbl():
    if os.path.exists(STRTBL2_JSON):
        print(f"{YELLOW}Converting mcstrings02.json → mcstrings02.strtbl{RESET}")
        subprocess.run(["python", os.path.join(TOOLS_FOLDER, "strtbl.py"), "enc", STRTBL2_JSON], check=True)
        os.remove(STRTBL2_JSON)

    if os.path.exists(STRTBL8_JSON):
        print(f"{YELLOW}Converting mcstrings08.json → mcstrings08.strtbl{RESET}")
        subprocess.run(["python", os.path.join(TOOLS_FOLDER, "strtbl.py"), "enc", STRTBL8_JSON], check=True)
        os.remove(STRTBL8_JSON)

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

            if " - " in name:
                artist, song, clean_artist = name_splitting(name)
                artist_nospace = re.sub(r"[^\w]", "", clean_artist)
                song_nospace = re.sub(r"[^\w]", "", song)
                artist_song = f"{artist_nospace}_{song_nospace}"
            else:
                artist_song = name

            wav_path = os.path.join(genre_path, f"{artist_song}.wav")
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
            else:
                # If it’s already a wav, rename to artist_song
                if name != artist_song:
                    wav_path = os.path.join(genre_path, f"{artist_song}.wav")
                    os.rename(file_path, wav_path)

            # Build RSTM
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

# === 10. Final step ===
def finalStep(song_dict2, song_dict8):
    song_dict2, song_dict8, new_sdplay_songs, genre_songs = process_music_files(song_dict2, song_dict8)
    update_playlists(new_sdplay_songs, genre_songs, song_dict2, song_dict8)
    convert_json_to_strtbl()
    build_rstm_files()

    answer = input(f"\n{BLUE}Do you want to encode back into STREAMS.DAT and ASSETS.DAT?{RESET}\nOnly do it if the ASSETS and STREAMS folders aren't missing any files (Y/N): ").strip().lower()
    if answer == "y":
        compile_back()

def main():
    if os.path.exists(os.path.join(BASE_FOLDER, "ASSETS.DAT")) or os.path.exists(os.path.join(BASE_FOLDER, "STREAMS.DAT")):
        answer = input(f"{BLUE}Do you want to decode STREAMS.DAT or ASSETS.DAT?{RESET} (Y/N): ").strip().lower()
        if answer == "y": 
            decompile_dat_files()
            answer = input(f"{BLUE}The DAT files were decoded.{RESET} Do you want to continue? (Y/N): ").strip().lower()
            if answer != "y":
                return
    if not os.path.exists(MUSIC_FOLDER) or not os.path.exists(PLAY_FOLDER) or not os.path.exists(STRTBL_FOLDER):
        print(f"\n{RED}Ain't shit to change! I need STREAMS and ASSETS. Either add them already decoded or in .DAT format.")
        return
    convert_strtbl_to_json()
    song_dict2, song_dict8 = load_song_dicts()
    answer = input(f"\n{BLUE}Now is the time to add new songs to STREAMS/Music/[genre].{RESET}\nThe file format must be [Artist] - [Name].[ext]. Write REAL BIG once you're ready: ").strip().lower()
    if answer == "real big": 
        if list_new_songs() != 0:
            answer = input(f"\n{BLUE}Is the list of all new songs complete?{RESET}\nWrite DICK REAL BIG once you're ready: ").strip().lower()
            if answer == "dick real big": 
                finalStep(song_dict2, song_dict8)
        else:
            answer = input(f"\n{BLUE}The script didn't find any new songs with format [artist] - [song].[ext].{RESET}\nDo you still want to continue? Write DICK REAL SMALL once you're ready: ").strip().lower()
            if answer == "dick real small": 
                finalStep(song_dict2, song_dict8)


if __name__ == "__main__":
    main()
