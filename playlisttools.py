#!/usr/bin/env python

import os
import json
import re
import getpass # Not used directly in the provided snippet but good to keep
import requests
import random
import string
import sys
from hashlib import md5
from datetime import datetime

CONFIG_FILE = "config.json"

# --- API & CONFIGURATION FUNCTIONS ---

def send_api_request(base_url, username, password, endpoint, **kwargs):
    """Manually constructs and sends a Subsonic API request. Returns response dict on success, None on failure."""
    if not all([base_url, username, password]): return None
    url = base_url.strip()
    if not url.endswith('/'): url += '/'
    if not url.endswith('/rest/'): url += 'rest/'
    api_args = {'f': 'json', 'u': username, 'v': '1.16.1', 'c': 'PlaylistTool'}
    query = kwargs.pop('query', None)
    api_args.update(kwargs)
    salt = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(7))
    token = md5((password + salt).encode('utf-8')).hexdigest()
    api_args.update({'t': token, 's': salt})
    full_url = url + endpoint + ".view"
    params = api_args.copy()
    if query: params['query'] = query
    try:
        res = requests.get(full_url, params=params, timeout=20)
        res.raise_for_status()
        res_json = res.json()
        if 'subsonic-response' in res_json and res_json['subsonic-response'].get('status') == 'ok':
            return res_json['subsonic-response']
    except (requests.exceptions.RequestException, json.JSONDecodeError):
        # print(f"API request to {full_url} failed: {e}") # Uncomment for debugging
        return None
    return None

def verify_connection(config):
    """Verifies credentials by pinging and performing a test search."""
    if not config or not all(k in config for k in ['navidrome_url', 'navidrome_user', 'navidrome_password']): return False
    if not send_api_request(config['navidrome_url'], config['navidrome_user'], config['navidrome_password'], 'ping'):
        print("  - Ping test failed."); return False
    # A simple search for 'a' (or any common letter) is more robust than 'test' which might not exist.
    # We don't care about results, just that the API endpoint is reachable and authenticated.
    if send_api_request(config['navidrome_url'], config['navidrome_user'], config['navidrome_password'], 'search3', query='a', songCount=1) is None:
        print("  - Search test failed."); return False
    return True

def handle_config():
    """Loads, validates, and repairs the Navidrome configuration."""
    config = {}
    if os.path.exists(CONFIG_FILE):
        print(f"Loading configuration from {CONFIG_FILE}...")
        try:
            with open(CONFIG_FILE, 'r') as f: config = json.load(f)
        except json.JSONDecodeError:
            print("Warning: config.json is corrupted."); config = {}
    print("Verifying configuration...")
    if verify_connection(config):
        print("Credentials verified successfully.")
        return config
    else:
        if config: print("\nVerification failed. Let's repair the configuration.")
    print("\nPlease enter/confirm your Navidrome server details.")
    while True:
        default_url = config.get('navidrome_url', '')
        url = input(f"Enter Navidrome URL [{default_url}]: ") or default_url
        default_user = config.get('navidrome_user', '')
        user = input(f"Enter Navidrome username [{default_user}]: ") or default_user
        # Using getpass for password input for security
        pwd = getpass.getpass("Enter Navidrome password or API key: ")
        test_config = {'navidrome_url': url, 'navidrome_user': user, 'navidrome_password': pwd}
        print("\nTesting connection...")
        if verify_connection(test_config):
            print("✅ Connection successful!")
            with open(CONFIG_FILE, 'w') as f: json.dump(test_config, f, indent=4)
            print(f"Configuration saved to {CONFIG_FILE}.")
            return test_config
        else:
            print("\n--- LOGIN FAILED ---")
            if input("Try again? (y/n): ").lower() != 'y': sys.exit("Aborted.")
            # Clear password on retry to force re-entry
            config = {'navidrome_url': url, 'navidrome_user': user} 

# --- HELPER FUNCTIONS ---

def parse_m3u(file_path):
    """Parses an M3U file, cleaning track titles by removing track numbers.
       Returns a list of dicts: {'artist': ..., 'album': ..., 'title': ...}
    """
    tracks = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f: lines = f.readlines()
    except Exception as e:
        print(f"Could not read file {file_path}: {e}"); return []
    for line in lines:
        line = line.strip()
        if line and not line.startswith('#'):
            # Example path: Artist/Album/01 - Song Title.mp3
            # Group 1: Artist, Group 2: Album, Group 3: Song Title, Group 4: Extension
            match = re.match(r"([^/]+)/([^/]+)/(.+)\.(mp3|flac|m4a|ogg|wav)", line, re.IGNORECASE)
            if match:
                raw_title = match.group(3).strip()
                # Clean track number (e.g., "01 - Song" -> "Song", "1. Song" -> "Song")
                cleaned_title = re.sub(r'^\s*\d+\s*[-._]?\s*', '', raw_title)
                tracks.append({'artist': match.group(1).strip(), 'album': match.group(2).strip(), 'title': cleaned_title})
    return tracks

def normalize_for_comparison(text):
    """Prepares a string for comparison by making it lowercase and removing non-alphanumeric chars."""
    if not isinstance(text, str): return "" # Handle non-string inputs
    return re.sub(r'[^a-z0-9]', '', text.lower())

def sanitize_filename(name):
    """Removes characters that are invalid in Windows filenames."""
    if not isinstance(name, str): return "invalid_filename" # Handle non-string inputs
    return re.sub(r'[\\/*?:"<>|]', "", name)

# --- POST-CHECK MENU FUNCTIONS ---

def export_missing_tracks(missing_tracks_for_export, maybes_for_export):
    if not missing_tracks_for_export and not maybes_for_export: print("\nNothing to export! All tracks were found."); return
    filename = input("Enter filename for missing tracks [missing_tracks.txt]: ") or "missing_tracks.txt"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"Playlist Scan Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        if missing_tracks_for_export:
            f.write("\n--- DEFINITELY MISSING TRACKS ---\n")
            for track in sorted(missing_tracks_for_export, key=lambda x: (x['artist'], x['album'], x['title'])):
                f.write(f"Artist: {track['artist']}\n  Album: {track['album']}\n  Title: {track['title']}\n\n")
        if maybes_for_export:
            f.write("\n--- POTENTIAL MATCHES (MAYBE) ---\n")
            for track in sorted(maybes_for_export, key=lambda x: x['artist']):
                f.write(f"Original: {track['title']} by {track['artist']}\n   Found: {track['maybe_found']}\n\n")
    print(f"✅ Report successfully saved to '{filename}'")

def export_missing_albums(missing_tracks_for_export, maybes_for_export):
    if not missing_tracks_for_export and not maybes_for_export: print("\nNothing to export! No albums are missing tracks."); return
    all_missing_track_data = missing_tracks_for_export + maybes_for_export
    missing_albums = sorted(list(set((track['artist'], track['album']) for track in all_missing_track_data)))
    filename = input("Enter filename for missing albums [missing_albums.txt]: ") or "missing_albums.txt"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"Missing Albums Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        for artist, album in missing_albums: f.write(f"{artist} - {album}\n")
    print(f"✅ Report successfully saved to '{filename}'")

def show_statistics(total_tracks, found_tracks_count, missing_tracks_count, maybes_count):
    if total_tracks == 0: print("\nNo tracks were scanned."); return
    success_rate = (found_tracks_count + maybes_count) / total_tracks * 100 if total_tracks > 0 else 0
    print("\n--- SCAN STATISTICS ---")
    print(f"  Total Tracks Scanned: {total_tracks}\n  -----------------------\n  Found (Exact Match):  {found_tracks_count}\n  Found (Potential):    {maybes_count}\n  Missing:              {missing_tracks_count}\n  -----------------------\n  Overall Match Rate:   {success_rate:.2f}%\n-------------------------")

def run_post_check_menu(total_scanned_tracks_all_playlists, all_found_for_stats, all_missing_for_stats, all_maybes_for_stats):
    while True:
        print("\n--- Post-Scan Menu ---\n1. Show Statistics\n2. Export missing tracks\n3. Export missing albums\n4. Exit to Main Menu")
        choice = input("> ")
        if choice == '1': 
            show_statistics(total_scanned_tracks_all_playlists, 
                            len(all_found_for_stats), 
                            len(all_missing_for_stats), 
                            len(all_maybes_for_stats))
        elif choice == '2': export_missing_tracks(all_missing_for_stats, all_maybes_for_stats)
        elif choice == '3': export_missing_albums(all_missing_for_stats, all_maybes_for_stats)
        elif choice == '4': break
        else: print("Invalid choice.")

# --- MODE 1: CHECK PLAYLISTS ---

def run_checker_mode(config, scan_results):
    url, user, pwd = config['navidrome_url'], config['navidrome_user'], config['navidrome_password']
    folder_path = input("\nEnter path to FOLDER with local M3U playlists: ").strip()
    if not os.path.isdir(folder_path): print(f"Error: Not a valid folder."); return
    m3u_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.m3u')]
    if not m3u_files: print(f"No '.m3u' files found in folder."); return
    
    print(f"\nFound {len(m3u_files)} playlists: {', '.join(m3u_files)}")
    scan_results.clear() # Clear previous scan results
    
    total_scanned_tracks_all_playlists = 0
    all_found_for_stats = [] # For statistics and exports
    all_missing_for_stats = []
    all_maybes_for_stats = []

    for filename in m3u_files:
        print(f"\n\n--- Checking Playlist: {filename} ---")
        playlist_tracks_original_order = parse_m3u(os.path.join(folder_path, filename))
        
        if not playlist_tracks_original_order: print("No valid tracks found. Skipping."); continue
        
        total_scanned_tracks_all_playlists += len(playlist_tracks_original_order)
        
        # New structure: a list of track items, preserving original order
        # Each item will be updated with its scan status and Navidrome match
        playlist_scan_items = []
        
        print(f"Found {len(playlist_tracks_original_order)} tracks. PASS 1: Strong matches...")
        
        # Pass 1: Initial search and populate playlist_scan_items
        for i, track_data in enumerate(playlist_tracks_original_order):
            simple_query = f"{track_data['artist']} {track_data['title']}"
            res = send_api_request(url, user, pwd, 'search3', query=simple_query, songCount=5)
            
            found_match_navidrome_song = None
            if res and res.get('searchResult3', {}).get('song'):
                normalized_m3u_title = normalize_for_comparison(track_data['title'])
                for found_song in res['searchResult3']['song']:
                    # Strong match condition: artist must be in found artist AND normalized title must match
                    if (track_data['artist'].lower() in found_song['artist'].lower() or
                        normalize_for_comparison(track_data['artist']) == normalize_for_comparison(found_song['artist'])) and \
                       normalized_m3u_title == normalize_for_comparison(found_song['title']):
                        found_match_navidrome_song = found_song
                        break
            
            if found_match_navidrome_song:
                playlist_scan_items.append({
                    'original_track': track_data,
                    'navidrome_song': found_match_navidrome_song,
                    'status': 'found'
                })
            else:
                # Add a placeholder for tracks not found in pass 1, to be processed in pass 2
                playlist_scan_items.append({
                    'original_track': track_data,
                    'navidrome_song': None, # No direct match yet
                    'status': 'unprocessed_pass2'
                })
        
        # Pass 2: Partial search for 'unprocessed_pass2' tracks
        tracks_for_pass2_count = sum(1 for item in playlist_scan_items if item['status'] == 'unprocessed_pass2')
        if tracks_for_pass2_count > 0:
            print(f"\nPASS 2: Partial search for {tracks_for_pass2_count} track(s)...")
            for item in playlist_scan_items:
                if item['status'] == 'unprocessed_pass2':
                    original_track = item['original_track']
                    # Try a partial title search
                    title_words = original_track['title'].split()
                    partial_title = ' '.join(title_words[:min(len(title_words), 3)]) # Use 1-3 words
                    
                    simple_partial_query = f"{original_track['artist']} {partial_title}"
                    res = send_api_request(url, user, pwd, 'search3', query=simple_partial_query, songCount=5)
                    
                    found_maybe = False
                    if res and res.get('searchResult3', {}).get('song'):
                        normalized_partial_title = normalize_for_comparison(partial_title)
                        for found_song in res['searchResult3']['song']:
                            # Heuristic for "maybe": original artist likely in found artist and found title starts with partial title
                            if (original_track['artist'].lower() in found_song['artist'].lower() or
                                normalize_for_comparison(original_track['artist']) == normalize_for_comparison(found_song['artist'])) and \
                               normalize_for_comparison(found_song['title']).startswith(normalized_partial_title):
                                item['status'] = 'maybe'
                                item['navidrome_song'] = found_song # Store the found song for potential future use
                                item['maybe_found_details'] = f"{found_song['title']} by {found_song['artist']}"
                                found_maybe = True
                                break
                    if not found_maybe:
                        item['status'] = 'missing'
        
        # Store the complete scan results for this playlist
        scan_results[filename] = playlist_scan_items

        # Aggregate for global statistics and exports
        for item in playlist_scan_items:
            if item['status'] == 'found':
                all_found_for_stats.append(item['navidrome_song'])
            elif item['status'] == 'missing':
                all_missing_for_stats.append(item['original_track'])
            elif item['status'] == 'maybe':
                # For 'maybes', the export expects the original track with a 'maybe_found' field
                track_for_export = item['original_track'].copy()
                track_for_export['maybe_found'] = item['maybe_found_details']
                all_maybes_for_stats.append(track_for_export)

    print("\n\n--- ALL PLAYLISTS CHECKED ---")
    run_post_check_menu(total_scanned_tracks_all_playlists, 
                        all_found_for_stats, 
                        all_missing_for_stats, 
                        all_maybes_for_stats)

# --- MODE 2: FIX PLAYLISTS ---

def create_fixed_playlist(playlist_scan_items, original_filename, output_dir):
    # 'playlist_scan_items' now comes in the original order
    found_count = sum(1 for item in playlist_scan_items if item['status'] == 'found')
    
    if found_count == 0:
        print(f"\nNo successful matches found for '{original_filename}', cannot create a fixed playlist.")
        return

    base_name = os.path.splitext(original_filename)[0]
    new_filename = f"{base_name}_fixed.m3u"
    output_path = os.path.join(output_dir, new_filename)
    os.makedirs(output_dir, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("#EXTM3U\n")
        # Iterate through the items in their original order
        for item in playlist_scan_items:
            if item['status'] == 'found' and item['navidrome_song'] and 'path' in item['navidrome_song']:
                f.write(item['navidrome_song']['path'] + "\n")
    print(f"\n✅ Successfully created fixed playlist: '{output_path}' with {found_count} tracks.")

def run_fixer_mode(scan_results):
    print("\n--- Fix Local M3U Playlists ---")
    if not scan_results:
        print("No scan has been run yet. Please run Option 1 first."); return
    
    scanned_files = list(scan_results.keys())
    print("The following playlists were scanned:")
    for i, filename in enumerate(scanned_files):
        # Calculate found count for display from the new structure
        found_count = sum(1 for item in scan_results[filename] if item['status'] in ['found', 'maybe'])
        print(f"  {i+1}. {filename} ({found_count} matches found)")
    
    try:
        choice = input("\nEnter the number of the playlist to fix (or 0 to fix all): ")
        
        output_dir = "fixed_playlists_" + datetime.now().strftime('%Y-%m-%d_%H%M%S')
        
        if choice == '0':
            print("\nFixing all scanned playlists...")
            for filename, items in scan_results.items():
                create_fixed_playlist(items, filename, output_dir)
        else:
            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(scanned_files):
                filename = scanned_files[choice_idx]
                items = scan_results[filename]
                create_fixed_playlist(items, filename, output_dir)
            else:
                print("Invalid number.")
    except ValueError:
        print("Invalid input. Please enter a number.")

# --- MODE 3: MANAGE SERVER PLAYLISTS ---

def download_playlist(config, playlist_id, playlist_name, output_dir):
    print(f"  Downloading '{playlist_name}'...")
    res = send_api_request(config['navidrome_url'], config['navidrome_user'], config['navidrome_password'], 'getPlaylist', id=playlist_id)
    if not res or 'playlist' not in res or 'entry' not in res['playlist']:
        print(f"    ERROR: Could not retrieve tracks for '{playlist_name}'."); return False
    safe_filename = sanitize_filename(playlist_name) + ".m3u"
    filepath = os.path.join(output_dir, safe_filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write("#EXTM3U\n")
        # Tracks from getPlaylist are already in the order they are on the server
        for track in res['playlist']['entry']: f.write(track['path'] + "\n")
    print(f"    ✅ Saved to '{filepath}'"); return True

def run_manager_mode(config):
    print("\nFetching playlists from Navidrome server...")
    res = send_api_request(config['navidrome_url'], config['navidrome_user'], config['navidrome_password'], 'getPlaylists')
    if not res or 'playlists' not in res or 'playlist' not in res['playlists']:
        print("Could not fetch playlists. Make sure your user has permission to view playlists."); return
    playlists = res['playlists']['playlist']
    
    while True:
        print("\n--- Navidrome Playlist Manager ---\n1. List Playlists\n2. Download a Specific Playlist\n3. Download ALL Playlists\n4. Back to Main Menu")
        choice = input("> ")
        if choice == '1':
            if not playlists: print("No playlists found on the server."); continue
            print("\n--- Playlists on Navidrome ---")
            for i, p in enumerate(playlists): print(f"  {i+1:2d}. {p['name']} ({p['songCount']} tracks)")
        elif choice == '2':
            if not playlists: print("No playlists found to download."); continue
            for i, p in enumerate(playlists): print(f"  {i+1:2d}. {p['name']}")
            try:
                p_choice = int(input("Enter number of playlist to download: ")) - 1
                if 0 <= p_choice < len(playlists):
                    selected = playlists[p_choice]
                    output_dir = "navidrome_playlists_" + datetime.now().strftime('%Y-%m-%d_%H%M%S')
                    os.makedirs(output_dir, exist_ok=True)
                    download_playlist(config, selected['id'], selected['name'], output_dir)
                else: print("Invalid number.")
            except ValueError: print("Invalid input.")
        elif choice == '3':
            if not playlists: print("No playlists found to download."); continue
            output_dir = "navidrome_playlists_" + datetime.now().strftime('%Y-%m-%d_%H%M%S')
            os.makedirs(output_dir, exist_ok=True)
            print(f"\nDownloading all {len(playlists)} playlists to '{output_dir}'...")
            for i, p in enumerate(playlists): download_playlist(config, p['id'], p['name'], output_dir)
            print("\nAll playlists downloaded.")
        elif choice == '4': break
        else: print("Invalid choice.")

# --- MAIN MENU ---

def main_menu():
    print("--- Navidrome Playlist Tool ---")
    config = handle_config()
    scan_results = {} # This dictionary will hold the results of the last scan for each playlist
    while True:
        print("\n--- Main Menu ---")
        print("1. Check Local M3U Playlists Against Navidrome")
        print("2. Fix Local M3U Playlists (requires a recent check)")
        print("3. Manage/Download Playlists from Navidrome")
        print("4. Exit")
        choice = input("> ")
        
        if choice == '1':
            run_checker_mode(config, scan_results)
        elif choice == '2':
            run_fixer_mode(scan_results)
        elif choice == '3':
            run_manager_mode(config)
        elif choice == '4':
            print("Goodbye!"); break
        else:
            print("Invalid choice.")

if __name__ == "__main__":
    main_menu()