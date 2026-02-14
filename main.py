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
    }
    
    if mode == 'audio':
        # Broadest audio format selection
        opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        })
    else:
        # Broadest video format selection: try combined best, then fallback
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
            try:
                # Main attempt with preferred quality
                info = ydl.extract_info(url, download=True)
            except Exception as e:
                # Fallback attempt with absolutely any available quality
                if "Requested format is not available" in str(e):
                    opts['format'] = 'best'
                    # If video, don't force merge to mp4 on fallback
                    if 'merge_output_format' in opts:
                        del opts['merge_output_format']
                    with yt_dlp.YoutubeDL(opts) as ydl_fallback:
                        info = ydl_fallback.extract_info(url, download=True)
                else:
                    raise e
            
            filename = ydl.prepare_filename(info)
            
            # Extension cleanup
            if mode == 'audio':
                base, _ = os.path.splitext(filename)
                if os.path.exists(base + '.mp3'):
                    filename = base + '.mp3'
            elif mode == 'video':
                base, _ = os.path.splitext(filename)
                if os.path.exists(base + '.mp4'):
                    filename = base + '.mp4'

        if not os.path.exists(filename):
            # Final scan of directory for any downloaded file
            files = [f for f in os.listdir(download_dir) if not f.endswith('.part')]
            if files:
                filename = os.path.join(download_dir, files[0])
            else:
                return jsonify({'error': 'Download failed to produce a file'}), 500

        # Note: We keep the file in temp for serving. 
        # For production, consider background cleanup.
        return send_file(
            filename,
            as_attachment=True,
            download_name=os.path.basename(filename)
        )
    except Exception as e:
        return jsonify({'error': f"Download Error: {str(e)}"}), 500

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
