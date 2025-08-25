#!/usr/bin/env python

# itunestoND.py - Transfers song ratings, playcounts, play dates, and all timestamps (song and album)
# from an iTunes library to the Navidrome database.
# FINAL, DEFINITIVE VERSION 17 - Includes Album Timestamp Synchronization.

import sys, sqlite3, datetime, re, string, pprint, random, json, os
from pathlib import Path
from urllib.parse import unquote
from urllib.request import pathname2url
from bs4 import BeautifulSoup

CONFIG_FILE = 'config.json'

def get_configuration():
    if os.path.exists(CONFIG_FILE):
        print(f"Reading configuration from {CONFIG_FILE}...")
        with open(CONFIG_FILE, 'r') as f: config = json.load(f)
        if 'navidrome_db' in config and 'itunes_xml' in config: return config
        else:
            print("Config file is incomplete. Deleting and recreating.")
            os.remove(CONFIG_FILE)
    
    print("First time setup: Let's create a config.json file.")
    config = {}
    while True:
        path = input('Enter the full path to your Navidrome database file (navidrome.db): ')
        if os.path.isfile(path): config['navidrome_db'] = path; break
        else: print("File not found. Please try again.")
    while True:
        path = input('Enter the full path to your iTunes Library XML file (Library.xml): ')
        if os.path.isfile(path): config['itunes_xml'] = path; break
        else: print("File not found. Please try again.")
    with open(CONFIG_FILE, 'w') as f: json.dump(config, f, indent=4)
    print(f"\nConfiguration saved to {CONFIG_FILE}.")
    return config

def pre_flight_check(config, soup):
    print("\n--- Starting Pre-flight Check ---")
    
    checks = { "navidrome_db_found": False, "itunes_xml_found": False, "music_folder_key_found": False, "sample_song_found_in_xml": False, "song_found_in_navidrome_db": False }
    itunes_music_folder_url = None
    
    if os.path.isfile(config['navidrome_db']): checks['navidrome_db_found'] = True; print(f"[OK]   Navidrome DB found at: {config['navidrome_db']}")
    else: print(f"[FAIL] Navidrome DB not found.")
    if os.path.isfile(config['itunes_xml']): checks['itunes_xml_found'] = True; print(f"[OK]   iTunes XML found at: {config['itunes_xml']}")
    else: print(f"[FAIL] iTunes XML not found.")

    if checks['itunes_xml_found']:
        music_folder_key = soup.find('key', text='Music Folder')
        if music_folder_key:
            base_path_url = unquote(music_folder_key.next_sibling.text)
            itunes_music_folder_url = base_path_url + 'Music/'
            checks['music_folder_key_found'] = True
            print(f"[OK]   Auto-detected iTunes base path as: {base_path_url}")
            print(f"[OK]   Adjusted Music Folder path is: {itunes_music_folder_url}")
            
            all_songs = soup.dict.dict.find_all('dict')
            sample_song_url = None
            for song_entry in reversed(all_songs):
                if song_entry.find('key', string='Location'):
                    location_url = unquote(song_entry.find('key', string='Location').next_sibling.text)
                    if location_url.lower().startswith(itunes_music_folder_url.lower()):
                        sample_song_url = location_url; checks['sample_song_found_in_xml'] = True
                        print(f"[OK]   Found sample song in XML: {sample_song_url}"); break
            if not checks['sample_song_found_in_xml']: print("[FAIL] Could not find a sample song located within the adjusted Music Folder.")
        else: print("[FAIL] Could not find the 'Music Folder' key in your iTunes XML.")

    if checks['navidrome_db_found'] and checks['sample_song_found_in_xml']:
        relative_path = re.sub(re.escape(itunes_music_folder_url), '', sample_song_url, flags=re.IGNORECASE).lstrip('/').replace('\\', '/')
        print(f"       - Calculated relative path for check: {relative_path}")
        
        conn = sqlite3.connect(config['navidrome_db'])
        cur = conn.cursor()
        cur.execute('SELECT id FROM media_file WHERE path = ?', (relative_path,))
        result = cur.fetchone()
        conn.close()
        
        if result: checks['song_found_in_navidrome_db'] = True; print(f"[OK]   SUCCESS! Found a matching song in the Navidrome database.")
        else: print(f"[FAIL] Could not find a matching song in the Navidrome database.")
    
    if all(checks.values()): print("\n--- Pre-flight Check Passed ---\n"); return itunes_music_folder_url
    else: print("\n--- PRE-FLIGHT CHECK FAILED ---"); sys.exit(1)

def determine_userID(cursor):
    cursor.execute('SELECT id, user_name FROM user')
    users = cursor.fetchall()
    if len(users) == 1: print(f'Changes will be applied to the {users[0][1]} Navidrome account.'); return users[0][0]
    else: raise Exception('There needs to be exactly one user account set up with Navidrome.')

def update_playstats(d1, id, playcount, playdate, rating=0):
    d1.setdefault(id, {}); d1[id].setdefault('play count', 0)
    d1[id].setdefault('play date', datetime.datetime.fromordinal(1))
    d1[id]['play count'] += playcount; d1[id]['rating'] = rating
    if playdate > d1[id]['play date']: d1[id].update({'play date': playdate})

def write_to_annotation(cursor, dictionary_with_stats, entry_type, user_id):
    annotation_entries = []
    for item_id in dictionary_with_stats:
        this_entry = dictionary_with_stats[item_id]
        play_count = this_entry['play count']
        play_date = this_entry['play date'].strftime('%Y-%m-%d %H:%M:%S.%f')[:-3] + "+00:00"
        rating_value = this_entry.get('rating', 0)
        starred_value = 0
        annotation_entries.append((user_id, item_id, entry_type, play_count, play_date, rating_value, starred_value, None))
    
    cursor.executemany('INSERT INTO annotation (user_id, item_id, item_type, play_count, play_date, rating, starred, starred_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)', annotation_entries)

# --- Main script starts here ---
print()
print('This script will migrate ratings, play counts, AND timestamps from your ITunes library to your Navidrome database.')
_ = input('\nAre you sure you want to continue? (y/n): ').lower()
if _ != 'y': print('Good bye.'); sys.exit(0)

config = get_configuration()
nddb_path, itdb_path = Path(config['navidrome_db']), Path(config['itunes_xml'])
print('\nParsing Itunes library. This may take a while.')
with open(itdb_path, 'r', encoding="utf-8") as f: soup = BeautifulSoup(f, 'lxml-xml')

it_root_music_path_url = pre_flight_check(config, soup)
songs = soup.dict.dict.find_all('dict'); song_count = len(songs)
print(f'Found {song_count:,} files in Itunes database to process.')
del(soup)

conn = None
try:
    conn = sqlite3.connect(nddb_path)
    cur = conn.cursor()
    userID = determine_userID(cur)
    songID_correlation, artists, albums, files, timestamp_updates = {}, {}, {}, {}, []
    cur.execute('DELETE FROM annotation'); print("Old annotations cleared.")
    status_interval = song_count // 8 if song_count > 0 else 1
    counter = 0

    print("Processing all songs to gather data...")
    for it_song_entry in songs:
        counter += 1
        if counter % status_interval == 0:
            print(f'{counter:,} files parsed so far of {song_count:,} total songs.')

        if it_song_entry.find('key', string='Location') == None: continue
        song_path_url = unquote(it_song_entry.find('key', string='Location').next_sibling.text)
        if not song_path_url.lower().startswith(it_root_music_path_url.lower()): continue   
        
        relative_path = re.sub(re.escape(it_root_music_path_url), '', song_path_url, flags=re.IGNORECASE).lstrip('/').replace('\\', '/')
        
        try:
            cur.execute('SELECT id, artist_id, album_id FROM media_file WHERE path = ?', (relative_path,))
            song_id, artist_id, album_id = cur.fetchone()
        except TypeError: continue

        it_song_ID = int(it_song_entry.find('key', string='Track ID').next_sibling.text)
        songID_correlation.update({it_song_ID: song_id})

        try:
            date_added_str = it_song_entry.find('key', string='Date Added').next_sibling.text[:-1]
            date_added_obj = datetime.datetime.strptime(date_added_str, '%Y-%m-%dT%H:%M:%S')
            formatted_date = date_added_obj.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3] + "+00:00"
            timestamp_updates.append((formatted_date, formatted_date, formatted_date, song_id))
        except AttributeError: pass
        
        try:
            song_rating = int(int(it_song_entry.find('key', string='Rating').next_sibling.text) / 20)
        except AttributeError: song_rating = 0
            
        try:
            play_count = int(it_song_entry.find('key', string='Play Count').next_sibling.text)
            last_played = datetime.datetime.strptime(it_song_entry.find('key', string='Play Date UTC').next_sibling.text[:-1], '%Y-%m-%dT%H:%M:%S')
        except AttributeError:
            play_count = 0; last_played = datetime.datetime.fromordinal(1)

        update_playstats(artists, artist_id, play_count, last_played)
        update_playstats(albums, album_id, play_count, last_played)
        update_playstats(files, song_id, play_count, last_played, rating=song_rating)

    print(f"\nUpdating song timestamps for {len(timestamp_updates):,} songs...")
    cur.executemany('UPDATE media_file SET created_at = ?, updated_at = ?, birth_time = ? WHERE id = ?', timestamp_updates)
    print("Song timestamp migration complete.")

    print('Writing ratings and play counts to annotation table:')
    write_to_annotation(cur, artists, 'artist', userID)
    write_to_annotation(cur, files, 'media_file', userID)
    write_to_annotation(cur, albums, 'album', userID)
    print('Annotation data written.')

    # --- NEW: Final step to synchronize album 'Date Added' timestamps ---
    print("\nSynchronizing album timestamps...")
    album_sync_query = """
    UPDATE album
    SET 
        created_at = (SELECT MIN(created_at) FROM media_file WHERE media_file.album_id = album.id),
        updated_at = (SELECT MIN(created_at) FROM media_file WHERE media_file.album_id = album.id),
        imported_at = (SELECT MIN(created_at) FROM media_file WHERE media_file.album_id = album.id)
    WHERE EXISTS (
        SELECT 1 FROM media_file WHERE media_file.album_id = album.id
    );
    """
    cur.execute(album_sync_query)
    print(f"{cur.rowcount} album timestamps were synchronized.")

    conn.commit()
    print("\nAll database changes have been successfully committed.")

except sqlite3.Error as e:
    print(f"\nA database error occurred: {e}");
    if conn: conn.rollback(); print("All changes have been rolled back.")
finally:
    if conn: conn.close(); print("Database connection closed.")

with open('IT_file_correlations.py', 'w') as f:
    f.write('# iTunes to Navidrome song ID correlations.\n')
    f.write('itunes_correlations = ')
    f.write(pprint.pformat(songID_correlation))

print('File correlation index saved.')
print('\nMigration script finished.')