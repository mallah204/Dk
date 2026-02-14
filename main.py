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
        opts.update({
            'format': 'bestvideo[height<=360]+bestaudio/best[height<=360]/best',
        })
    return opts

@app.route('/download', methods=['GET'])
def download():
    url = request.args.get('url')
    mode = request.args.get('mode', 'video') # 'video' or 'audio'
    
    if not url:
        return jsonify({'error': 'URL is required'}), 400

    try:
        # Create a persistent directory for the download session
        session_id = str(time.time()).replace('.', '')
        download_dir = os.path.join(tempfile.gettempdir(), f'ytdl_{session_id}')
        os.makedirs(download_dir, exist_ok=True)
        
        outtmpl = os.path.join(download_dir, '%(title)s.%(ext)s')
        opts = get_yt_dlp_opts(mode, outtmpl)
        
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
            # If audio, the extension might have changed to mp3 by postprocessor
            if mode == 'audio':
                filename = os.path.splitext(filename)[0] + '.mp3'

            if not os.path.exists(filename):
                # Fallback check for common patterns if prepare_filename doesn't match exactly
                files = os.listdir(download_dir)
                if files:
                    filename = os.path.join(download_dir, files[0])

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
