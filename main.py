from flask import Flask, request, jsonify, send_file
import yt_dlp
import os
import tempfile
import shutil

app = Flask(__name__)

# Use absolute path for cookies if available
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COOKIES_FILE = os.path.join(BASE_DIR, 'cookies', 'youtube.txt')

def get_yt_dlp_opts(mode, outtmpl):
    # Selector for video: best 360p or worst available
    video_selector = 'best[height<=360]/worst'
    # Selector for audio: worst audio or best available
    audio_selector = 'worstaudio/best'
    
    opts = {
        'cookiefile': COOKIES_FILE if os.path.exists(COOKIES_FILE) else None,
        'quiet': True,
        'no_warnings': True,
        'outtmpl': outtmpl,
        'add_header': [
            'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
        ],
        'nocheckcertificate': True,
        'format': audio_selector if mode == 'audio' else video_selector,
        'ignoreerrors': True, # Crucial: don't stop on single format errors
    }
    
    if mode == 'audio':
        opts.update({
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '64',
            }],
        })
    else:
        opts.update({
            'merge_output_format': 'mp4',
        })
        
    return opts

@app.route('/video', methods=['GET'])
def download_video():
    url = request.args.get('url')
    if not url:
        return jsonify({'error': 'URL is required'}), 400
    return process_download(url, 'video')

@app.route('/audio', methods=['GET'])
def download_audio():
    url = request.args.get('url')
    if not url:
        return jsonify({'error': 'URL is required'}), 400
    return process_download(url, 'audio')

def process_download(url, mode):
    download_dir = tempfile.mkdtemp()
    try:
        outtmpl = os.path.join(download_dir, '%(title)s.%(ext)s')
        opts = get_yt_dlp_opts(mode, outtmpl)
        
        info = None
        filename = None
        
        # We try to extract info and download
        with yt_dlp.YoutubeDL(opts) as ydl:
            try:
                # Attempt with the preferred format selector
                info = ydl.extract_info(url, download=True)
                if not info or '_type' in info and info['_type'] == 'playlist':
                    raise Exception("Format selection failed or playlist returned")
                filename = ydl.prepare_filename(info)
            except Exception as e:
                # FALLBACK: Try with absolute 'best' format if the specific selector fails
                print(f"Preferred format failed: {e}. Trying fallback 'best' format.")
                opts['format'] = 'best'
                # Re-initialize to clear any cached failure states
                with yt_dlp.YoutubeDL(opts) as ydl_fallback:
                    info = ydl_fallback.extract_info(url, download=True)
                    filename = ydl_fallback.prepare_filename(info)

        if not info:
             return jsonify({'error': 'Download failed: Requested format and fallbacks are not available.'}), 500

        # Extension handling for post-processors
        if mode == 'audio':
            base, _ = os.path.splitext(filename)
            if os.path.exists(base + '.mp3'):
                filename = base + '.mp3'
            else:
                for f in os.listdir(download_dir):
                    if f.endswith('.mp3'):
                        filename = os.path.join(download_dir, f)
                        break
        elif mode == 'video':
            base, _ = os.path.splitext(filename)
            if os.path.exists(base + '.mp4'):
                filename = base + '.mp4'
        
        if not os.path.exists(filename):
            files = [f for f in os.listdir(download_dir) if not f.endswith('.part')]
            if files:
                filename = os.path.join(download_dir, files[0])
            else:
                return jsonify({'error': 'Download completed but no file was found on disk.'}), 500

        # Copy to a safer temp location before cleaning up the temp dir
        final_dest = os.path.join(tempfile.gettempdir(), os.path.basename(filename))
        shutil.copy2(filename, final_dest)
        shutil.rmtree(download_dir)

        return send_file(
            final_dest,
            as_attachment=True,
            download_name=os.path.basename(filename)
        )
    except Exception as e:
        if os.path.exists(download_dir):
            shutil.rmtree(download_dir)
        return jsonify({'error': str(e)}), 500

@app.route('/', methods=['GET'])
def index():
    return jsonify({
        'status': 'online',
        'endpoints': {
            'video': '/video?url=<url>',
            'audio': '/audio?url=<url>'
        }
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
