from flask import Flask, request, jsonify, send_file
import yt_dlp
import os
import tempfile
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
        'nocheckcertificate': True,
        # Use simple format strings that are more likely to exist
        'format': 'bestaudio/best' if mode == 'audio' else 'best/bestvideo+bestaudio',
    }
    
    if mode == 'audio':
        opts.update({
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '128', # Reduced quality slightly for better compatibility
            }],
        })
    else:
        opts.update({
            'merge_output_format': 'mp4',
        })
        
    return opts

@app.route('/download', methods=['GET'])
def download():
    url = request.args.get('url')
    mode = request.args.get('mode', 'video')
    
    if not url:
        return jsonify({'error': 'URL is required'}), 400

    # Clean the URL (remove tracking params which sometimes mess up yt-dlp)
    if '?' in url and 'watch' not in url:
        url = url.split('?')[0]

    download_dir = tempfile.mkdtemp()
    
    try:
        outtmpl = os.path.join(download_dir, '%(title)s.%(ext)s')
        opts = get_yt_dlp_opts(mode, outtmpl)
        
        with yt_dlp.YoutubeDL(opts) as ydl:
            try:
                # Main attempt
                info = ydl.extract_info(url, download=True)
            except Exception as e:
                # Absolute fallback: just download anything
                opts['format'] = 'best'
                if 'postprocessors' in opts and mode != 'audio':
                    del opts['postprocessors']
                if 'merge_output_format' in opts:
                    del opts['merge_output_format']
                
                with yt_dlp.YoutubeDL(opts) as ydl_fallback:
                    info = ydl_fallback.extract_info(url, download=True)
            
            filename = ydl.prepare_filename(info)
            
            # Extension cleanup for post-processed files
            if mode == 'audio':
                base, _ = os.path.splitext(filename)
                if os.path.exists(base + '.mp3'):
                    filename = base + '.mp3'
            elif mode == 'video':
                base, _ = os.path.splitext(filename)
                if os.path.exists(base + '.mp4'):
                    filename = base + '.mp4'

        if not os.path.exists(filename):
            # Final scan
            files = [f for f in os.listdir(download_dir) if not f.endswith('.part')]
            if files:
                filename = os.path.join(download_dir, files[0])
            else:
                return jsonify({'error': 'Download failed to produce a file'}), 500

        return send_file(
            filename,
            as_attachment=True,
            download_name=os.path.basename(filename)
        )
    except Exception as e:
        # If even fallback fails, we return the specific error but without the ANSI codes
        error_msg = str(e).replace('\u001b[0;31m', '').replace('\u001b[0m', '')
        return jsonify({'error': f"Download Error: {error_msg}"}), 500
    finally:
        # Background cleanup or periodic cleanup is better, but here we keep it simple
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
