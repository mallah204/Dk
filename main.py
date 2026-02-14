from flask import Flask, request, jsonify, send_file
import yt_dlp
import os
import tempfile
import time
import shutil

app = Flask(__name__)

# Use absolute path for cookies
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COOKIES_FILE = os.path.join(BASE_DIR, 'cookies', 'youtube.txt')

def get_yt_dlp_opts(mode, outtmpl):
    opts = {
        'cookiefile': COOKIES_FILE if os.path.exists(COOKIES_FILE) else None,
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
                'preferredquality': '192',
            }],
        })
    else: # video
        opts.update({
            # Resilient format selection
            'format': 'bestvideo+bestaudio/best',
            'merge_output_format': 'mp4',
        })
    return opts

@app.route('/download', methods=['GET'])
def download():
    url = request.args.get('url')
    mode = request.args.get('mode', 'video')
    
    if not url:
        return jsonify({'error': 'URL is required'}), 400

    download_dir = tempfile.mkdtemp()
    
    try:
        outtmpl = os.path.join(download_dir, '%(title)s.%(ext)s')
        opts = get_yt_dlp_opts(mode, outtmpl)
        
        with yt_dlp.YoutubeDL(opts) as ydl:
            # Re-fetch info and download with broad error handling
            try:
                info = ydl.extract_info(url, download=True)
            except Exception as e:
                # Fallback to absolute best if combined fails
                if mode == 'video':
                    opts['format'] = 'best'
                    with yt_dlp.YoutubeDL(opts) as ydl_fallback:
                        info = ydl_fallback.extract_info(url, download=True)
                else:
                    raise e
            
            filename = ydl.prepare_filename(info)
            
            # Handle extension changes
            if mode == 'audio':
                base, _ = os.path.splitext(filename)
                if os.path.exists(base + '.mp3'):
                    filename = base + '.mp3'
            elif mode == 'video':
                # If we merged to mp4, ensure filename reflects that
                base, _ = os.path.splitext(filename)
                if os.path.exists(base + '.mp4'):
                    filename = base + '.mp4'

        if not os.path.exists(filename):
            files = [f for f in os.listdir(download_dir) if not f.endswith('.part')]
            if files:
                filename = os.path.join(download_dir, files[0])
            else:
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
        'status': 'online',
        'usage': {
            'video': '/download?url=YOUR_URL&mode=video',
            'audio': '/download?url=YOUR_URL&mode=audio'
        }
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
