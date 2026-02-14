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
            # First extract info without downloading to handle potential errors
            info = ydl.extract_info(url, download=False)
            # Re-fetch info and download
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
            # If audio, yt-dlp might have changed the extension to .mp3
            if mode == 'audio':
                base, _ = os.path.splitext(filename)
                if os.path.exists(base + '.mp3'):
                    filename = base + '.mp3'

        if not os.path.exists(filename):
            # Fallback: find any file in the directory
            files = os.listdir(download_dir)
            if files:
                filename = os.path.join(download_dir, files[0])
            else:
                return jsonify({'error': 'File not found after download'}), 500

        # We can't easily use after_this_response for cleanup if it's missing
        # For now, we'll send the file. In a production env, a cron job or 
        # background task would clean up temp files.
        return send_file(
            filename,
            as_attachment=True,
            download_name=os.path.basename(filename)
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        # Note: shutil.rmtree here might delete file before send_file finishes
        # but in many flask envs send_file reads it into memory or handles it
        # however, to be safe we'll skip immediate cleanup in this simple fix
        pass

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
