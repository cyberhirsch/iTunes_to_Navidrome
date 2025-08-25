# iTunes to Navidrome Advanced Migration Scripts

A set of heavily modified Python scripts designed to perform a deep and comprehensive migration of your listening history and metadata from an Apple iTunes/Music library to a self-hosted Navidrome server.

This project is the result of a collaborative, in-depth effort to reverse-engineer the modern Navidrome database schema and overcome the limitations of the original migration scripts. It correctly migrates **ratings, play counts, and historical timestamps** for both individual songs and albums, and adds robust error-checking and usability features.

## Features

### `itunestoND.py` (Main Data Migration)
- **Full History Migration:** Migrates not just play counts, but also your 0-5 star ratings and the original "Date Added" for every song by directly modifying the database.
- **Album Timestamp Synchronization:** After migrating song data, the script intelligently updates each album's "Date Added" (`created_at`, `updated_at`, `imported_at`) to reflect the date the *first song* from that album was added to your library.
- **Intelligent Pre-flight Check:** Automatically validates your setup before making any changes. It checks for all necessary files and verifies that the song paths in your iTunes library can be matched to entries in the Navidrome database, preventing silent failures.
- **Configuration File:** On the first run, the script creates a `config.json` to save your database paths, so you only have to enter them once.
- **Cross-Platform Compatibility:** Handles file path differences between a Windows-based iTunes library and a Linux-based Navidrome server (common for Raspberry Pi setups).

### `itunesPlaylistMigrator.py` (Playlist Migration)
- **Robust Pre-flight Check:** Ensures that the `config.json` and `IT_file_correlations.py` files exist and are valid before starting.
- **Shared Configuration:** Reads server details and paths from the same `config.json`, so you only enter your credentials once.
- **Bulk Import Option:** Asks whether you want to migrate all playlists automatically or be prompted for each one individually.
- **Graceful Error Handling:** If a song in an iTunes playlist is not found in the Navidrome library (e.g., a protected file that was skipped), it is gracefully skipped without crashing the script.
- **Self-Cleaning:** If a playlist is created but contains no valid, transferrable songs, the script automatically deletes the empty playlist from Navidrome.

## Requirements

- Python 3.x installed on the machine where you will run the scripts.
- Access to your iTunes `Library.xml` file. (If missing, enable it via `Edit > Preferences > Advanced > "Share iTunes Library XML..."` in your Apple Music/iTunes app).
- Access to your `navidrome.db` file from your server.

## How to Use

The migration is a safe, offline process. The scripts modify a *copy* of your Navidrome database on your local machine, which you then transfer back to the server.

### Phase 1: Preparation

1.  **Set Up Your Workspace:**
    *   Create a dedicated folder on your computer (e.g., `C:\itunes-migration`).
    *   Download `itunestoND.py`, `itunesPlaylistMigrator.py`, and `requirements.txt` into this folder.

2.  **Install Dependencies:**
    *   Open a command prompt or terminal in your workspace folder.
    *   Run the command: `pip install -r requirements.txt`.

3.  **Prepare Navidrome:**
    *   Ensure your Navidrome server has completed a full scan of your music library. For the most accurate migration, it is highly recommended to **start with a fresh, clean Navidrome database**.

### Phase 2: Main Data Migration (`itunestoND.py`)

1.  **Stop Your Navidrome Server:** Connect to your server and run `docker-compose down`.

2.  **Copy the Database:** Using a tool like WinSCP or `scp`, copy the `navidrome.db` file from your server to your local workspace folder.

3.  **Run the Script:**
    *   In your command prompt, run: `python itunestoND.py`
    *   **First Run:** The script will prompt you for the path to your `navidrome.db` and `Library.xml` files and save them to `config.json`.
    *   **Pre-flight Check:** The script will run its validation checks. If it fails, it will provide a detailed report.
    *   **Migration:** If the check passes, the script will process your entire library. This may take several minutes.

4.  **Deploy the New Database:**
    *   Once the script finishes, copy the modified `navidrome.db` from your workspace back to your Navidrome server, overwriting the old one.

5.  **Restart Navidrome:** Run `docker-compose up -d` on your server.

6.  **Verify:** Open Navidrome and navigate to the **Songs** view to see your historical "Date Added," "Rating," and "Play Count." Check the **Albums** view to see the corrected "Date Added" timestamps.

### Phase 3: Playlist Migration (`itunesPlaylistMigrator.py`)

1.  **Ensure Navidrome is Running.**

2.  **Run the Playlist Script:**
    *   In your command prompt, run: `python itunesPlaylistMigrator.py`
    *   **First Run:** The script will read your existing `config.json` and prompt you for your Navidrome server URL and credentials, saving them for future use.
    *   Follow the prompts to choose between a bulk or individual playlist import.

3.  **Verify:** Refresh your Navidrome interface. Your playlists should now be visible.

## Acknowledgments

This project stands on the shoulders of the original work by **Stampede** on the [itunes-navidrome-migration](https://github.com/Stampede/itunes-navidrome-migration) repository. This version is a heavily modified and updated fork designed to be more robust, user-friendly, and compatible with modern Navidrome installations.
