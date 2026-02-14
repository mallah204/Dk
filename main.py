from flask import Flask, request, jsonify, send_file
import yt_dlp
import os
import tempfile
import threading
import time

app = Flask(__name__)

COOKIES_FILE = 'cookies/youtube.txt'

def get_yt_dlp_opts(mode, outtmpl):
    opts = {
        'cookiefile': COOKIES_FILE,
        'quiet': True,
        'no_warnings': True,
        'outtmpl': outtmpl,
    }
    if mode == 'audio':
        opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '64',
            }],
        })
    else: # video
        # Simplified format string to be more robust
        opts.update({
            'format': 'best[height<=360]/best',
        })
    return opts

@app.route('/download', methods=['GET'])
def download():
    url = request.args.get('url')
    mode = request.args.get('mode', 'video')
    
    if not url:
        return jsonify({'error': 'URL is required'}), 400

    try:
        session_id = str(time.time()).replace('.', '')
        download_dir = os.path.join(tempfile.gettempdir(), f'ytdl_{session_id}')
        os.makedirs(download_dir, exist_ok=True)
        
        outtmpl = os.path.join(download_dir, '%(title)s.%(ext)s')
        
        # Use a more lenient approach for extraction
        with yt_dlp.YoutubeDL(get_yt_dlp_opts(mode, outtmpl)) as ydl:
            # First, try to just get info without downloading to verify
            try:
                info = ydl.extract_info(url, download=True)
            except yt_dlp.utils.DownloadError:
                # Fallback: remove strict format constraints if it fails
                opts = get_yt_dlp_opts(mode, outtmpl)
                opts['format'] = 'best'
                with yt_dlp.YoutubeDL(opts) as ydl_fallback:
                    info = ydl_fallback.extract_info(url, download=True)

            filename = ydl.prepare_filename(info)
            if mode == 'audio':
                filename = os.path.splitext(filename)[0] + '.mp3'

            # Double check if file exists, if not look in directory
            if not os.path.exists(filename):
                files = [f for f in os.listdir(download_dir) if not f.endswith('.part')]
                if files:
                    filename = os.path.join(download_dir, files[0])

            if not os.path.exists(filename):
                return jsonify({'error': 'File not found after download'}), 500

            return send_file(
                filename,
                as_attachment=True,
                download_name=os.path.basename(filename)
            )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/', methods=['GET'])
def index():
    return jsonify({
        'message': 'YouTube Downloader API is running',
        'endpoints': {
            'download_video': '/download?mode=video&url=<YOUTUBE_URL>',
            'download_audio': '/download?mode=audio&url=<YOUTUBE_URL>'
        },
        'defaults': {
            'video_quality': '360p',
            'audio_quality': 'lowest'
        }
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
