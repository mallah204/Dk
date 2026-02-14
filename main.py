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
    }
    
    if mode == 'audio':
        opts.update({
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '64', # low bitrate as requested
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
        
        with yt_dlp.YoutubeDL(opts) as ydl:
            try:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                
                # Handle extension changes after post-processing
                if mode == 'audio':
                    base, _ = os.path.splitext(filename)
                    if os.path.exists(base + '.mp3'):
                        filename = base + '.mp3'
                elif mode == 'video':
                    base, _ = os.path.splitext(filename)
                    if os.path.exists(base + '.mp4'):
                        filename = base + '.mp4'
                
                if not os.path.exists(filename):
                    # Fallback scan for any file in the directory
                    files = [f for f in os.listdir(download_dir) if not f.endswith('.part')]
                    if files:
                        filename = os.path.join(download_dir, files[0])
                    else:
                        raise Exception("No file generated")

                return send_file(
                    filename,
                    as_attachment=True,
                    download_name=os.path.basename(filename)
                )
            except Exception as e:
                return jsonify({'error': f"yt-dlp error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({'error': f"Server error: {str(e)}"}), 500
    # Note: Cleanup would ideally happen after send_file, but for simplicity we skip it in this endpoint

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
