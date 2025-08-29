# Navidrome Migration and Playlist Management Tools

![Python](https://img.shields.io/badge/Python-3.x-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

This repository provides a collection of Python command-line utilities designed to help you manage your music library and playlists with a [Navidrome](https://www.navidrome.org/) (or any Subsonic-compatible) music server. From migrating historical data from iTunes to verifying and fixing local M3U playlists, these tools streamline your music management workflow.

## Table of Contents

*   [Features](#features)
*   [Requirements](#requirements)
*   [Installation](#installation)
*   [Configuration (`config.json`)](#configuration-configjson)
*   [Scripts Overview](#scripts-overview)
    *   [`itunestoND.py` (iTunes Data Migration)](#itunestondpy-itunes-data-migration)
    *   [`itunesPlaylistMigrator.py` (iTunes Playlist Migration)](#itunesplaylistmigratorpy-itunes-playlist-migration)
    *   [`playlisttools.py` (Local/Server Playlist Management)](#playlisttoolspy-localserver-playlist-management)
*   [M3U File Format Expectation](#m3u-file-format-expectation)
*   [Contributing](#contributing)
*   [License](#license)

## Features

### `itunestoND.py` (Main Data Migration)
*   **Full History Migration:** Migrates not just play counts, but also your 0-5 star ratings and the original "Date Added" for every song by directly modifying the database.
*   **Album Timestamp Synchronization:** After migrating song data, the script intelligently updates each album's "Date Added" (`created_at`, `updated_at`, `imported_at`) to reflect the date the *first song* from that album was added to your library.
*   **Intelligent Pre-flight Check:** Automatically validates your setup before making any changes. It checks for all necessary files and verifies that the song paths in your iTunes library can be matched to entries in the Navidrome database, preventing silent failures.
*   **Configuration File:** On the first run, the script creates a `config.json` to save your database paths, so you only have to enter them once.
*   **Cross-Platform Compatibility:** Handles file path differences between a Windows-based iTunes library and a Linux-based Navidrome server (common for Raspberry Pi setups).

### `itunesPlaylistMigrator.py` (iTunes Playlist Migration)
*   **Robust Pre-flight Check:** Ensures that the `config.json` and `IT_file_correlations.py` files exist and are valid before starting.
*   **Shared Configuration:** Reads server details and paths from the same `config.json`, so you only enter your credentials once.
*   **Bulk Import Option:** Asks whether you want to migrate all playlists automatically or be prompted for each one individually.
*   **Graceful Error Handling:** If a song in an iTunes playlist is not found in the Navidrome library (e.g., a protected file that was skipped), it is gracefully skipped without crashing the script.
*   **Self-Cleaning:** If a playlist is created but contains no valid, transferrable songs, the script automatically deletes the empty playlist from Navidrome.

### `playlisttools.py` (Local/Server Playlist Management)
*   **Verify Local Playlists:** Scan local M3U files and identify tracks that are present, potentially present, or definitely missing from your Navidrome server.
*   **Fix Local Playlists:** Generate new M3U playlists containing only the tracks successfully found on Navidrome, using their server-side paths. **Preserves original track order.**
*   **Generate Reports:** Export lists of missing tracks and albums to text files for easy review.
*   **Manage Server Playlists:** List and download playlists directly from your Navidrome server as local M3U files.
*   **Merge Local Playlists:** Combine two existing local M3U playlists into a single new playlist. Includes an option for de-duplication while maintaining order.
*   **Secure Authentication:** Uses salted MD5 hashing for password authentication with Navidrome's Subsonic API.
*   **Interactive Configuration:** Guides you through setting up and verifying your Navidrome connection.

## Requirements

*   Python 3.x
*   The following Python packages:
    *   `requests`
    *   `beautifulsoup4`
    *   `lxml`
    *   `PyInputPlus`

## Installation

1.  **Clone the repository (or download the scripts):**
    ```bash
    git clone https://github.com/yourusername/navidrome-tools.git
    cd navidrome-tools
    ```
    (Replace `yourusername` with your GitHub username or the repository owner's username if you fork it.)

2.  **Install dependencies:**
    *   Open a command prompt or terminal in your workspace folder.
    *   Run the command: `pip install -r requirements.txt`.
        *(Ensure you have a `requirements.txt` file in your repository with the above dependencies listed.)*

## Configuration (`config.json`)

All scripts in this repository utilize a `config.json` file to store settings. This file is created and managed interactively on the first run of each script (or if incomplete).

*   **`itunestoND.py`** will prompt for and save:
    *   `navidrome_db`: Full path to your `navidrome.db` file.
    *   `itunes_xml`: Full path to your `iTunes Library.xml` file.

*   **`itunesPlaylistMigrator.py`** will prompt for and save:
    *   `server_url`: The base URL of your Navidrome instance (e.g., `http://localhost:4533`).
    *   `username`: Your Navidrome username.
    *   `password`: Your Navidrome password or API key.

*   **`playlisttools.py`** will prompt for and save:
    *   `navidrome_url`: The base URL of your Navidrome instance (e.g., `http://localhost:4533`).
    *   `navidrome_user`: Your Navidrome username.
    *   `navidrome_password`: Your Navidrome password or API key.

**⚠️ Important Note on Server Credentials:**
The `itunesPlaylistMigrator.py` and `playlisttools.py` both manage Navidrome server connection details within `config.json`. However, they use **different key names** (`server_url`, `username`, `password` vs `navidrome_url`, `navidrome_user`, `navidrome_password` respectively).

If you intend to use both scripts in the same directory, you will experience `config.json` being updated by whichever script you run last, potentially overwriting the server connection details for the other.

**Recommendation:**
*   You can manually edit `config.json` after the initial setup of both scripts to ensure consistency (e.g., pick one set of keys like `navidrome_url` and update `itunesPlaylistMigrator.py`'s code to use `navidrome_url` instead of `server_url`, etc., if you are comfortable modifying the script).
*   Alternatively, you can run these scripts from separate working directories, each with its own `config.json`, to avoid conflicts.

## Scripts Overview

### `itunestoND.py` (iTunes Data Migration)

This script migrates song ratings, play counts, and "Date Added" timestamps (song and album) from an iTunes library to the Navidrome database. This is a safe, offline process that modifies a *copy* of your Navidrome database.

#### How to Use `itunestoND.py`

1.  **Stop Your Navidrome Server:** Connect to your server and run `docker-compose down` (or equivalent command to stop Navidrome).
2.  **Copy the Database:** Copy your `navidrome.db` file from your server to your local workspace folder.
3.  **Run the Script:** `python itunestoND.py`
    *   Follow the prompts for `navidrome.db` and `Library.xml` paths.
    *   The script will perform a pre-flight check to ensure paths match between your iTunes XML and Navidrome DB.
    *   It will then process your library (this may take a while for large libraries).
    *   Upon completion, it will generate an `IT_file_correlations.py` file, which is essential for the playlist migrator.
4.  **Deploy the New Database:** Copy the *modified* `navidrome.db` from your workspace back to your Navidrome server, overwriting the old one.
5.  **Restart Navidrome:** Run `docker-compose up -d` (or equivalent) on your server.
6.  **Verify:** Open Navidrome and check your **Songs** and **Albums** views for migrated data.

### `itunesPlaylistMigrator.py` (iTunes Playlist Migration)

After `itunestoND.py` has run and `IT_file_correlations.py` has been created, this script uses the correlation data to transfer your iTunes playlists to Navidrome.

#### How to Use `itunesPlaylistMigrator.py`

1.  **Ensure Navidrome is Running.**
2.  **Run the Script:** `python itunesPlaylistMigrator.py`
    *   The script will perform pre-flight checks and prompt for Navidrome server credentials if not already in `config.json`.
    *   Follow the prompts to choose between bulk or individual playlist migration.
3.  **Verify:** Refresh your Navidrome interface to see your new playlists.

### `playlisttools.py` (Local/Server Playlist Management)

This versatile tool helps you manage local M3U playlists in relation to your Navidrome server and also provides functionality to manage playlists directly on Navidrome.

#### How to Use `playlisttools.py`

1.  **Ensure Navidrome is Running.**
2.  **Run the Script:** `python playlisttools.py`
    *   The script will prompt for Navidrome server credentials if not already in `config.json`.
    *   Choose from the main menu options:
        *   **1. Check Local M3U Playlists Against Navidrome:**
            *   Enter the path to a folder containing your M3U files.
            *   The tool will scan and report on found, missing, and potentially matching tracks.
            *   Access a post-scan menu to view statistics or export reports of missing tracks/albums.
        *   **2. Fix Local M3U Playlists:**
            *   Requires a recent playlist check (Option 1) to have been performed.
            *   Select a scanned playlist (or all) to generate a new `_fixed.m3u` file.
            *   These new playlists contain only the tracks found on Navidrome, using their server-side paths, and **preserve the original track order**.
        *   **3. Manage/Download Playlists from Navidrome:**
            *   List all playlists on your Navidrome server.
            *   Download a specific playlist or all playlists from Navidrome to local M3U files.
        *   **4. Merge Local M3U Playlists:**
            *   Enter the full paths to two local M3U files.
            *   The script will combine them into a new file, appending the second playlist's tracks to the first's, **preserving order**.
            *   An option to remove duplicate tracks (keeping the first occurrence) is provided.

## M3U File Format Expectation

For features that parse local M3U files (like `playlisttools.py`'s playlist checking), the script expects track paths within your M3U files to generally follow a `Artist/Album/Track Title.ext` structure. For example:

#EXTM3U
Artist Name/Album Name/01 - Song Title.mp3
Another Artist/Another Album/Track 2.flac

The script uses regular expressions to extract `Artist Name`, `Album Name`, and `Song Title`, and attempts to clean leading track numbers (e.g., "01 - ") from titles for better matching. If your M3U paths deviate significantly from this pattern, matching accuracy may be affected.

## Acknowledgments

This project stands on the shoulders of the original work by **Stampede** on the [itunes-navidrome-migration](https://github.com/Stampede/itunes-navidrome-migration) repository. This version includes heavily modified and updated scripts designed to be more robust, user-friendly, and compatible with modern Navidrome installations, along with new playlist management functionalities.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
