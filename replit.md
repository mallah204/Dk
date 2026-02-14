# replit.md

## Overview

This is a YouTube video/audio downloader API built with Flask and yt-dlp. It provides a simple HTTP endpoint that accepts a YouTube URL and download mode (video or audio), downloads the content using yt-dlp with cookie-based authentication, and serves the resulting file back to the client. Audio downloads are converted to MP3 format at 64kbps quality using FFmpeg post-processing.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Backend

- **Framework**: Flask (Python) — lightweight web framework serving a REST API
- **Core Library**: yt-dlp — a youtube-dl fork used for downloading video/audio from YouTube
- **File Handling**: Downloads are stored in temporary directories (`tempfile.gettempdir()`) with session-based naming using timestamps to avoid conflicts between concurrent requests
- **Audio Processing**: FFmpeg is used as a post-processor to extract and convert audio to MP3 format when audio mode is selected

### API Design

- **Single endpoint**: `GET /download` with query parameters:
  - `url` (required) — the YouTube video URL
  - `mode` (optional, defaults to `video`) — either `video` or `audio`
- The endpoint downloads the file server-side and then serves it back to the client

### Authentication with YouTube

- Uses a Netscape-format cookie file (`cookies/youtube.txt`) to authenticate with YouTube, which helps bypass age restrictions and access private/restricted content
- The cookie file is referenced by yt-dlp on every download request

### Deployment

- Originally configured for **Vercel** deployment (`vercel.json` present) using `@vercel/python` builder
- Also includes **gunicorn** in requirements for production WSGI serving
- For Replit, the app should be run with `gunicorn main:app` or `python main.py` for development

### Key Considerations

- The `main.py` file appears to be **incomplete** — the download function is cut off after setting up options. The agent should complete the download logic: run yt-dlp with the configured options, find the output file, serve it with `send_file()`, and clean up temporary files afterward.
- Temporary files should be cleaned up after serving to prevent disk space issues
- FFmpeg must be available in the environment for audio extraction to work
- The cookie file contains real session cookies — these will expire and may need refreshing

## External Dependencies

### Python Packages (requirements.txt)
- **Flask** — Web framework for the API
- **yt-dlp** — YouTube download library
- **gunicorn** — Production WSGI HTTP server

### System Dependencies
- **FFmpeg** — Required for audio post-processing (MP3 conversion). Must be installed at the system level (`apt install ffmpeg` or equivalent)

### External Services
- **YouTube** — The target platform for downloading content, accessed via yt-dlp with cookie-based authentication
- No database is used — this is a stateless API
- No frontend — API-only service