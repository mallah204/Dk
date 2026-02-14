from flask import Flask, request, jsonify
import yt_dlp
import os

app = Flask(__name__)

# Base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Optional cookies file
COOKIES_FILE = os.path.join(BASE_DIR, 'cookies', 'youtube.txt')

# FFmpeg binary path (important for Render)
FFMPEG_PATH = os.path.join(BASE_DIR, 'bin', 'ffmpeg')


def get_ydl_opts_for_info():
    opts = {
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
        },
        'skip_download': True,  # Important! Don't download
    }

    # Add cookies if exist
    if os.path.exists(COOKIES_FILE):
        opts['cookiefile'] = COOKIES_FILE

    # Add ffmpeg path if exist
    if os.path.exists(FFMPEG_PATH):
        opts['ffmpeg_location'] = FFMPEG_PATH

    return opts


@app.route("/formats")
def list_formats():
    url = request.args.get("url")
    if not url:
        return jsonify({"error": "URL parameter missing"}), 400

    try:
        ydl_opts = get_ydl_opts_for_info()
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        # Extract all formats
        formats = []
        for f in info.get('formats', []):
            formats.append({
                'format_id': f.get('format_id'),
                'ext': f.get('ext'),
                'acodec': f.get('acodec'),
                'vcodec': f.get('vcodec'),
                'height': f.get('height'),
                'width': f.get('width'),
                'fps': f.get('fps'),
                'tbr': f.get('tbr'),
                'filesize': f.get('filesize'),
                'url': f.get('url'),
            })

        return jsonify({
            'title': info.get('title'),
            'id': info.get('id'),
            'formats': formats
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route("/")
def home():
    return jsonify({
        "status": "online",
        "endpoints": {
            "formats": "/formats?url=VIDEO_URL"
        }
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
