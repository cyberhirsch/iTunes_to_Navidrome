#!/usr/bin/env python

# itunesPlaylistMigrator.py - Used in conjunction with itunestoND.py
# First run that script, then run this one while you have your Navidrome server running.
# It will parse the Itunes library XML file and use the Navidrome API to transfer your playlists.
# DEFINITIVE VERSION: Has pre-flight checks, config file, bulk import, and cleans up empty playlists.

from pathlib import Path
import sys, requests, urllib.parse, random, re, string, json, os
from bs4 import BeautifulSoup
import pyinputplus as pyip
from hashlib import md5

CONFIG_FILE = 'config.json'
CORRELATION_FILE = 'IT_file_correlations.py'

def pre_flight_check():
    """Checks for the existence of necessary configuration and correlation files."""
    print("\n--- Starting Pre-flight Check ---")
    
    checks = { "config_found": False, "correlation_file_found": False, "correlation_data_found": False }

    if os.path.exists(CONFIG_FILE):
        checks['config_found'] = True
        print(f"[OK]   Configuration file found: {CONFIG_FILE}")
    else:
        print(f"[FAIL] Configuration file '{CONFIG_FILE}' not found. Please run 'itunestoND.py' first.")
    
    if os.path.exists(CORRELATION_FILE):
        checks['correlation_file_found'] = True
        print(f"[OK]   Correlation file found: {CORRELATION_FILE}")
    else:
        print(f"[FAIL] Correlation file '{CORRELATION_FILE}' not found. Please run 'itunestoND.py' first.")
    
    if checks['correlation_file_found']:
        try:
            from IT_file_correlations import itunes_correlations
            if itunes_correlations:
                checks['correlation_data_found'] = True
                print(f"[OK]   Successfully imported {len(itunes_correlations)} song correlations.")
            else:
                print(f"[FAIL] Correlation file '{CORRELATION_FILE}' is empty. The main script could not match any songs.")
        except (ImportError, SyntaxError):
            print(f"[FAIL] Could not import data from '{CORRELATION_FILE}'. It may be corrupt.")
    
    if all(checks.values()):
        print("\n--- Pre-flight Check Passed ---\n")
        from IT_file_correlations import itunes_correlations
        return itunes_correlations
    else:
        print("\n--- PRE-FLIGHT CHECK FAILED ---")
        print("Please run the main 'itunestoND.py' script successfully before running this one.")
        sys.exit(1)

def get_full_configuration():
    with open(CONFIG_FILE, 'r') as f: config = json.load(f)

    if 'server_url' in config and 'username' in config and 'password' in config:
        print("Server details found in config.json.")
        return config
    else:
        print("\nNavidrome Server details are not in the config file. Let's add them.")
        server_url = input('Enter the address to your navidrome server (e.g., http://192.168.1.123:4533): ')
        username = input('Enter your Navidrome username: ')
        password = pyip.inputPassword(prompt='Enter the password to your Navidrome account: ')
        config.update({'server_url': server_url, 'username': username, 'password': password})
        with open(CONFIG_FILE, 'w') as f: json.dump(config, f, indent=4)
        print("\nServer details saved to config.json for future use.")
        return config

def send_api_request(endpoint, **kwargs):
    api_args = {'f': 'json', 'u': username, 'v': '1.16.1', 'c': 'python'}
    api_args.update(kwargs)
    pool = string.ascii_letters + string.digits
    salt = ''.join(random.choice(pool) for i in range(7))
    token = md5((password + salt).encode('utf-8')).hexdigest()
    api_args.update({'t': token, 's': salt})

    try:
        res = requests.get(server_url + endpoint, params=api_args)
        res.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"\nCould not reach Navidrome Server at {server_url.partition('rest/')[0]}")
        print(f"Error: {e}"); return None

    try:
        res_json = res.json()
        if 'subsonic-response' in res_json:
            subsonic_res = res_json['subsonic-response']
            if subsonic_res.get('status') == 'ok': return subsonic_res
            elif 'error' in subsonic_res: print(f"\nAPI Error: {subsonic_res['error']['message']} (Code: {subsonic_res['error']['code']})")
            else: print("\nAPI Error: Unexpected response from server.")
        else: print("\nAPI Error: The server's response was not in the expected format.")
        return None
    except json.JSONDecodeError:
        print("\nAPI Error: Could not decode the server's response."); return None

def migrate_playlist(plist, itunes_correlations):
    """Handles the migration of a single playlist."""
    playlist_name = plist.find('key', text='Name').find_next('string').text
    try: playlist_tracks = plist.array.find_all('dict')
    except AttributeError: return
    if not playlist_tracks: return

    print(f'\nMigrating playlist "{playlist_name}" ({len(playlist_tracks)} tracks)...')
    
    create_playlist_reply = send_api_request('createPlaylist', name=playlist_name)
    if not create_playlist_reply:
        print(f'  - ERROR: Failed to create playlist in Navidrome.'); return

    ND_playlist_id = create_playlist_reply['playlist']['id']
    it_track_ids = [int(track.integer.text) for track in playlist_tracks]
    
    ND_track_ids = []
    missing_songs_count = 0
    for it_id in it_track_ids:
        if it_id in itunes_correlations: ND_track_ids.append(itunes_correlations[it_id])
        else: missing_songs_count += 1
            
    if missing_songs_count > 0:
        print(f"  - Warning: {missing_songs_count} song(s) will be skipped (not found in Navidrome library).")

    if not ND_track_ids:
        # --- NEW: Self-cleaning logic ---
        print("  - No valid songs found for this playlist. Deleting empty playlist from Navidrome and skipping.")
        send_api_request('deletePlaylist', id=ND_playlist_id)
        return

    print(f'  - Adding {len(ND_track_ids)} tracks...')
    add_tracks_reply = send_api_request('updatePlaylist', playlistId=ND_playlist_id, songIdToAdd=ND_track_ids)

    if add_tracks_reply: print(f'  - SUCCESS: Playlist "{playlist_name}" migrated.')
    else: print(f'  - ERROR: Failed to add tracks to playlist.')

# --- Main script starts here ---

itunes_correlations = pre_flight_check()
config = get_full_configuration()

server_url, username, password = config['server_url'], config['username'], config['password']
if not server_url.startswith('http'): server_url = 'http://' + server_url
if not server_url.endswith('/'): server_url += '/'
if not server_url.endswith('/rest/'): server_url += 'rest/'

print("\nAttempting to connect to the server...")
if not send_api_request('ping'):
    print("Connection to server failed. Please check the server address in config.json and ensure Navidrome is running. Exiting.")
    sys.exit(1)
print('Connection to server successful.')

it_db_path = Path(config['itunes_xml'])
if not it_db_path.is_file():
    print(f"ERROR: Could not find iTunes XML at path in config.json: {it_db_path}"); sys.exit(1)

print(f'\nUsing "{it_db_path}" for the iTunes library.')
print("Parsing the XML file... this may take a moment for large libraries.")
with open(it_db_path, 'r', encoding="utf-8") as f:
    soup = BeautifulSoup(f, 'lxml-xml')
all_playlists_in_xml = soup.array.find_all('dict', recursive=False)
print("Parsing complete.")

playlists_to_skip = ('Library', 'Downloaded', 'Music', 'Movies', 'TV Shows', 'Podcasts', 'Audiobooks', 'Tagged', 'Genius')
valid_playlists = []
for plist in all_playlists_in_xml:
    if plist.find('key', text='Distinguished Kind'): continue
    if plist.find('key', text='Smart Info'): continue
    playlist_name = plist.find('key', text='Name').find_next('string').text
    if playlist_name in playlists_to_skip: continue
    valid_playlists.append(plist)

print(f"\nFound {len(valid_playlists)} user-created playlists in your library.")
if not valid_playlists:
    print("No playlists to migrate. Exiting."); sys.exit(0)

migrate_all = pyip.inputYesNo(prompt='Do you want to migrate ALL of them automatically? (y/n) ')

if migrate_all == 'yes':
    for plist in valid_playlists:
        migrate_playlist(plist, itunes_correlations)
else:
    print("\nOkay, I will ask you about each playlist individually.")
    for plist in valid_playlists:
        playlist_name = plist.find('key', text='Name').find_next('string').text
        track_count = len(plist.array.find_all('dict'))
        should_migrate = pyip.inputYesNo(prompt=f'\nDo you want to migrate "{playlist_name}" ({track_count} tracks)? (y/n) ')
        if should_migrate == 'yes':
            migrate_playlist(plist, itunes_correlations)

print("\nPlaylist migration finished.")