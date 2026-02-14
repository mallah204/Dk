from flask import Flask, request, jsonify, send_file
import yt_dlp
import os
import tempfile
import time

app = Flask(__name__)

COOKIES_FILE = 'cookies/youtube.txt'

def get_yt_dlp_opts(mode, outtmpl):
    opts = {
        'cookiefile': COOKIES_FILE,
        'quiet': True,
        'no_warnings': True,
        'outtmpl': outtmpl,
        'add_header': [
            'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
        ],
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
        # Default to 360p but allow any if not available
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
        
        # Try with preferred quality first
        try:
            opts = get_yt_dlp_opts(mode, outtmpl)
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
        except Exception:
            # Absolute fallback for format errors
            opts = get_yt_dlp_opts(mode, outtmpl)
            opts['format'] = 'best'
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)

        # Handle post-processed extensions for audio
        if mode == 'audio':
            base_path = os.path.splitext(filename)[0]
            if os.path.exists(base_path + '.mp3'):
                filename = base_path + '.mp3'

        # Absolute file search fallback
        if not os.path.exists(filename):
            for f in os.listdir(download_dir):
                if not f.endswith('.part'):
                    filename = os.path.join(download_dir, f)
                    break

        if not os.path.exists(filename):
            return jsonify({'error': 'Download failed to produce a file'}), 500

        return send_file(
            filename,
            as_attachment=True,
            download_name=os.path.basename(filename)
        )
    except Exception as e:
        error_msg = str(e).split('\n')[0]
        return jsonify({'error': f"Download Error: {error_msg}"}), 500

@app.route('/', methods=['GET'])
def index():
    return jsonify({
        'message': 'YouTube Downloader API is running',
        'endpoints': {
            'download_video': '/download?mode=video&url=<YOUTUBE_URL>',
            'download_audio': '/download?mode=audio&url=<YOUTUBE_URL>'
        }
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
