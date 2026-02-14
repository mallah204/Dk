from flask import Flask, request, jsonify, send_file
import yt_dlp
import tempfile
import os

app = Flask(__name__)

# Base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Optional cookies file
COOKIES_FILE = os.path.join(BASE_DIR, 'cookies', 'youtube.txt')

# FFmpeg binary path (important for Render)
FFMPEG_PATH = os.path.join(BASE_DIR, 'bin', 'ffmpeg')


def get_ydl_opts(mode, output_path):
    # Safer formats (less "Requested format not available" error)
    video_format = "best[height<=360]/best"
    audio_format = "bestaudio/best"

    opts = {
        'outtmpl': output_path,
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'format': audio_format if mode == "audio" else video_format,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
        }
    }

    # Add cookies only if exist
    if os.path.exists(COOKIES_FILE):
        opts['cookiefile'] = COOKIES_FILE

    # Add ffmpeg path only if exist
    if os.path.exists(FFMPEG_PATH):
        opts['ffmpeg_location'] = FFMPEG_PATH

    if mode == "video":
        opts['merge_output_format'] = 'mp4'

    if mode == "audio":
        opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '64',
        }]

    return opts


def download_media(url, mode):
    temp_dir = tempfile.mkdtemp()
    output_template = os.path.join(temp_dir, "%(title)s.%(ext)s")

    try:
        ydl_opts = get_ydl_opts(mode, output_template)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

        # Fix filename after processing
        if mode == "audio":
            filename = os.path.splitext(filename)[0] + ".mp3"

        if mode == "video":
            filename = os.path.splitext(filename)[0] + ".mp4"

        # Fallback if filename changed
        if not os.path.exists(filename):
            files = [f for f in os.listdir(temp_dir) if not f.endswith('.part')]
            if files:
                filename = os.path.join(temp_dir, files[0])
            else:
                return None, "Download failed"

        return filename, None

    except Exception as e:
        return None, str(e)


@app.route("/video")
def video():
    url = request.args.get("url")
    if not url:
        return jsonify({"error": "URL parameter missing"}), 400

    file_path, error = download_media(url, "video")
    if error:
        return jsonify({"error": f"Download Error: {error}"}), 500

    return send_file(file_path, as_attachment=True)


@app.route("/audio")
def audio():
    url = request.args.get("url")
    if not url:
        return jsonify({"error": "URL parameter missing"}), 400

    file_path, error = download_media(url, "audio")
    if error:
        return jsonify({"error": f"Download Error: {error}"}), 500

    return send_file(file_path, as_attachment=True)


@app.route("/")
def home():
    return jsonify({
        "status": "online",
        "endpoints": {
            "video": "/video?url=VIDEO_URL",
            "audio": "/audio?url=VIDEO_URL"
        }
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)