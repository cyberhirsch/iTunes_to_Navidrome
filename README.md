# iTunes to Navidrome Advanced Migration Scripts

A set of Python scripts designed to perform a deep and comprehensive migration of your listening history and metadata from an Apple iTunes/Music library to a self-hosted Navidrome server.

This project is the result of a collaborative effort to reverse-engineer the modern Navidrome database schema and overcome the limitations of the original migration scripts. It correctly migrates **ratings, play counts, and historical timestamps** for both individual songs and albums.

## Features

- **Full History Migration:** Migrates not just play counts, but also your 0-5 star ratings and the original "Date Added" for every song.
- **Album Timestamp Synchronization:** After migrating song data, the script intelligently updates each album's "Date Added" to reflect the date the first song from that album was added to your library.
- **Intelligent Path Detection:** A robust pre-flight check automatically detects your iTunes music folder structure, validates it against your Navidrome database, and prevents the script from running if a path mismatch is found, saving you time.
- **Configuration File:** On the first run, the script creates a `config.json` to save your database paths, so you never have to enter them again.
- **Cross-Platform Compatibility:** Includes necessary fixes to handle file path differences between a Windows-based iTunes library and a Linux-based Navidrome server (common for Raspberry Pi setups).
- **Playlist Support:** Works in conjunction with the original `itunesPlaylistMigrator.py` to bring your playlists over after the main data migration is complete.

## The Problem This Solves

Standard Navidrome setup and other migration tools often fall short in several key areas:
1.  **Loss of "Date Added":** Navidrome typically sets the "Date Added" to the day it scans the files, destroying years of curated library history.
2.  **Incomplete Data:** Migrating star ratings and historical play counts is often overlooked.
3.  **Path Mismatches:** Original scripts frequently fail when moving from a Windows iTunes library to a Linux Navidrome server due to differences in path separators (`\` vs `/`).
4.  **Silent Failures:** Scripts can run to completion without errors but fail to write any data due to database schema changes in newer Navidrome versions.

This project addresses all of these issues directly.

## Requirements

- Python 3.x installed on the machine where you will run the scripts (e.g., your Windows PC).
- Access to your iTunes `Library.xml` file. (If it's missing, you must enable it in your Apple Music/iTunes app's preferences).
- Access to your `navidrome.db` file from your server.
- The original `itunesPlaylistMigrator.py` script (for playlist migration).

## How to Use

The migration is a safe, offline process. The scripts modify a *copy* of your Navidrome database on your local machine, which you then transfer back to the server.

### Phase 1: Preparation

1.  **Set Up Your Workspace:**
    *   Create a dedicated folder on your computer (e.g., `C:\itunes-migration`).
    *   Download `itunestoND.py`, `itunesPlaylistMigrator.py`, and `requirements.txt` into this folder.

2.  **Install Dependencies:**
    *   Open a command prompt or terminal in your workspace folder.
    *   Run the command: `pip install -r requirements.txt`. If you encounter issues with `lxml`, you may need to install it separately first with `pip install lxml`.

3.  **Enable XML Library:**
    *   Open your Apple Music/iTunes application.
    *   Go to `Edit > Preferences > Advanced`.
    *   Check the box for **"Share iTunes Library XML with other applications"**. This will create the `Library.xml` file the script needs.

4.  **Prepare Navidrome:**
    *   Ensure your Navidrome server has completed a full scan of your music library.

### Phase 2: Main Data Migration (`itunestoND.py`)

1.  **Stop Your Navidrome Server:** Connect to your server (e.g., via SSH) and run `docker-compose down`.

2.  **Copy the Database:** Using a tool like WinSCP or `scp`, copy the `navidrome.db` file from your server's data directory to your local workspace folder.

3.  **Run the Script:**
    *   In your command prompt, run: `python itunestoND.py`
    *   **First Run:** The script will prompt you for the path to your `navidrome.db` file and your `Library.xml` file. It will save these to a `config.json` for future use.
    *   **Pre-flight Check:** The script will automatically perform a series of checks to ensure your paths are correct and a sample song can be matched. If this fails, it will provide a detailed error to help you correct the issue.
    *   **Migration:** If the check passes, the script will process your entire library. This may take several minutes for large collections.

4.  **Deploy the New Database:**
    *   Once the script finishes, the `navidrome.db` file in your workspace is now enriched with your iTunes history.
    *   Copy this modified file back to your Navidrome server, overwriting the old one.

5.  **Restart Navidrome:** Run `docker-compose up -d` on your server.

6.  **Verify:** Open Navidrome and navigate to the **Songs** view. Sort by "Date Added," "Rating," and "Play Count" to see your migrated data. Check the **Albums** view to see the corrected "Date Added" timestamps.

### Phase 3: Playlist Migration (`itunesPlaylistMigrator.py`)

1.  **Ensure Navidrome is Running:** The playlist script communicates with a live server.

2.  **Check for Correlation File:** The previous script generated a file named `IT_file_correlations.py`. This must be in the same folder.

3.  **Run the Playlist Script:**
    *   In your command prompt, run: `python itunesPlaylistMigrator.py`
    *   Follow the prompts to enter your Navidrome server address, username, and password.
    *   Confirm which playlists you want to migrate.

4.  **Verify:** Refresh your Navidrome interface. Your playlists should now be visible.

## Acknowledgments

This project stands on the shoulders of the original work by **Stampede** on the [itunes-navidrome-migration](https://github.com/Stampede/itunes-navidrome-migration) repository. This version is a heavily modified and updated fork designed to work with modern Navidrome installations and provide a more comprehensive data migration.
