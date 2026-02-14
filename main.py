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
        # Allow any available format to prevent "Requested format not available" errors
        opts.update({
            'format': 'best',
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
        
        # Start with simple options
        opts = get_yt_dlp_opts(mode, outtmpl)
        
        with yt_dlp.YoutubeDL(opts) as ydl:
            try:
                info = ydl.extract_info(url, download=True)
            except Exception as e:
                # If it fails with cookies, try without as a last resort
                # or just log the error
                print(f"Download error: {str(e)}")
                return jsonify({'error': str(e)}), 500

            filename = ydl.prepare_filename(info)
            if mode == 'audio':
                filename = os.path.splitext(filename)[0] + '.mp3'

            # Search for the file if prepare_filename is slightly off
            if not os.path.exists(filename):
                for f in os.listdir(download_dir):
                    if not f.endswith('.part'):
                        filename = os.path.join(download_dir, f)
                        break

            if not os.path.exists(filename):
                return jsonify({'error': f'File not found after download attempt in {download_dir}'}), 500

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
