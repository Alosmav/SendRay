import http.server
import socketserver
import os
import html as html_utils
import urllib.parse
import sys
import re

# --- Configuration ---
DEFAULT_PORT = 8000
SERVER_TITLE = "ShareTik"
CHUNK_SIZE = 64 * 1024  # 64KB chunks for memory efficiency
ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
IMAGE_PREVIEW_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}
FILE_ICON_BY_EXTENSION = {
    '.pdf': 'pdf.svg',
    '.doc': 'word.svg', '.docx': 'word.svg', '.docm': 'word.svg', '.rtf': 'word.svg',
    '.ppt': 'powerpoint.svg', '.pptx': 'powerpoint.svg', '.pps': 'powerpoint.svg', '.ppsx': 'powerpoint.svg',
    '.xls': 'excel.svg', '.xlsx': 'excel.svg', '.xlsm': 'excel.svg', '.csv': 'excel.svg',
    '.zip': 'zip.svg', '.rar': 'zip.svg', '.7z': 'zip.svg', '.tar': 'zip.svg', '.gz': 'zip.svg',
    '.mp4': 'video.svg', '.mkv': 'video.svg', '.mov': 'video.svg', '.avi': 'video.svg',
    '.webm': 'video.svg', '.wmv': 'video.svg', '.m4v': 'video.svg',
    '.mp3': 'audio.svg', '.wav': 'audio.svg', '.ogg': 'audio.svg', '.m4a': 'audio.svg',
    '.flac': 'audio.svg', '.aac': 'audio.svg',
    '.jpg': 'image.svg', '.jpeg': 'image.svg', '.png': 'image.svg', '.gif': 'image.svg',
    '.webp': 'image.svg', '.bmp': 'image.svg', '.svg': 'image.svg',
}

# --- Modern UI Templates ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        :root {{
            --bg-color: #0f172a;
            --card-bg: #1e293b;
            --text-main: #f1f5f9;
            --text-muted: #94a3b8;
            --accent: #38bdf8;
            --accent-hover: #7dd3fc;
            --danger: #ef4444;
            --success: #22c55e;
            --border: #334155;
        }}
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-main);
            margin: 0;
            padding: 0;
            display: flex;
            flex-direction: column;
            min-height: 100vh;
        }}
        header {{
            background: rgba(30, 41, 59, 0.8);
            backdrop-filter: blur(10px);
            padding: 1rem 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            position: sticky;
            top: 0;
            z-index: 100;
            border-bottom: 1px solid var(--border);
        }}
        .logo {{
            font-size: 1.25rem;
            font-weight: 700;
            color: var(--accent);
            text-decoration: none;
        }}
        .nav-links {{
            display: flex;
            gap: 1rem;
        }}
        .btn {{
            padding: 0.5rem 1rem;
            border-radius: 0.5rem;
            text-decoration: none;
            font-weight: 500;
            transition: all 0.2s;
            cursor: pointer;
            border: none;
            font-size: 0.9rem;
        }}
        .btn-primary {{
            background-color: var(--accent);
            color: var(--bg-color);
        }}
        .btn-primary:hover {{
            background-color: var(--accent-hover);
        }}
        .btn-outline {{
            background-color: transparent;
            color: var(--text-main);
            border: 1px solid var(--border);
        }}
        .btn-outline:hover {{
            background-color: var(--border);
        }}
        main {{
            padding: 2rem;
            max-width: 1200px;
            margin: 0 auto;
            width: 100%;
            box-sizing: border-box;
        }}
        .breadcrumb {{
            margin-bottom: 2rem;
            color: var(--text-muted);
            font-size: 0.9rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        .breadcrumb a {{
            color: var(--accent);
            text-decoration: none;
        }}
        .search-container {{
            margin-bottom: 2rem;
            position: relative;
        }}
        .search-input {{
            width: 100%;
            padding: 0.75rem 1rem;
            border-radius: 0.75rem;
            background: var(--card-bg);
            border: 1px solid var(--border);
            color: var(--text-main);
            font-size: 1rem;
            outline: none;
            transition: border-color 0.2s;
        }}
        .search-input:focus {{
            border-color: var(--accent);
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
            gap: 1.5rem;
        }}
        .item {{
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 1rem;
            padding: 1.5rem 1rem;
            text-align: center;
            transition: all 0.2s;
            text-decoration: none;
            color: inherit;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 0.75rem;
            position: relative;
            overflow: hidden;
        }}
        .item:hover {{
            transform: translateY(-5px);
            border-color: var(--accent);
            box-shadow: 0 10px 20px -10px rgba(56, 189, 248, 0.3);
        }}
        .item-icon {{
            width: 3.5rem;
            height: 3.5rem;
            object-fit: contain;
            margin-bottom: 0.5rem;
        }}
        .item-preview {{
            width: 100%;
            height: 7rem;
            object-fit: cover;
            border-radius: 0.5rem;
        }}
        .item-name {{
            font-size: 0.9rem;
            font-weight: 500;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            width: 100%;
        }}
        .item-info {{
            font-size: 0.75rem;
            color: var(--text-muted);
        }}
        .upload-card {{
            background: var(--card-bg);
            border: 2px dashed var(--border);
            border-radius: 1.5rem;
            padding: 3rem;
            text-align: center;
            max-width: 600px;
            margin: 0 auto;
        }}
        .upload-card:hover {{
            border-color: var(--accent);
        }}
        .file-input-label {{
            display: inline-block;
            padding: 1rem 2rem;
            background: var(--accent);
            color: var(--bg-color);
            border-radius: 0.75rem;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.2s;
        }}
        .file-input-label:hover {{
            background: var(--accent-hover);
        }}
        #file-upload {{
            display: none;
        }}
        .status-msg {{
            margin-top: 1rem;
            padding: 0.75rem;
            border-radius: 0.5rem;
            font-weight: 500;
        }}
        .status-success {{ background: rgba(34, 197, 94, 0.2); color: var(--success); }}
        .status-error {{ background: rgba(239, 68, 68, 0.2); color: var(--danger); }}
    </style>
</head>
<body>
    <header>
        <a href="/" class="logo">{title}</a>
        <div class="nav-links">
            <a href="/upload" class="btn btn-primary">â†‘ Upload File</a>
            <a href="/" class="btn btn-outline">Home</a>
        </div>
    </header>
    <main>
        {content}
    </main>
    <script>
        document.addEventListener('DOMContentLoaded', () => {{
            const searchInput = document.querySelector('.search-input');
            if (searchInput) {{
                searchInput.addEventListener('input', (e) => {{
                    const term = e.target.value.toLowerCase();
                    document.querySelectorAll('.item').forEach(item => {{
                        const name = item.querySelector('.item-name').textContent.toLowerCase();
                        item.style.display = name.includes(term) ? 'flex' : 'none';
                    }});
                }});
            }}
        }});
    </script>
</body>
</html>
"""

UPLOAD_PAGE_TEMPLATE = """
<div class="upload-card">
    <h2 style="margin-top: 0; color: var(--text-main);">Upload New Files</h2>
    <p style="color: var(--text-muted); margin-bottom: 2rem;">Select one or more files to upload to the current directory</p>
    <div style="display: flex; flex-direction: column; align-items: center; gap: 1.5rem;">
        <label for="file-upload" class="file-input-label">Choose Files</label>
        <input id="file-upload" type="file" multiple style="display: none;">
        <div id="files-count" style="font-size: 0.9rem; color: var(--accent); font-weight: 500; height: 1.2rem;">No files selected</div>
        <button id="upload-btn" class="btn btn-primary" style="padding: 0.75rem 2rem; font-size: 1rem;">Start Upload</button>
    </div>

    <div id="progress-container" style="display: none; margin-top: 2rem; width: 100%; max-width: 300px; margin-left: auto; margin-right: auto;">
        <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem; font-size: 0.8rem; color: var(--text-muted);">
            <span id="progress-status">Uploading...</span>
            <span id="progress-percent">0%</span>
        </div>
        <div style="background: var(--border); height: 8px; border-radius: 4px; overflow: hidden;">
            <div id="progress-bar" style="background: var(--accent); width: 0%; height: 100%; transition: width 0.2s;"></div>
        </div>
    </div>

    <div id="upload-message" style="margin-top: 2rem;"></div>

    <p style="margin-top: 2rem; font-size: 0.8rem; color: var(--text-muted);">
        The files will be saved in the server's root directory.
    </p>
</div>

<script>
    const fileInput = document.getElementById('file-upload');
    const filesCountDiv = document.getElementById('files-count');

    fileInput.addEventListener('change', () => {
        const count = fileInput.files.length;
        filesCountDiv.textContent = count > 0 ? `${count} file${count > 1 ? 's' : ''} selected` : 'No files selected';
    });

    document.getElementById('upload-btn').addEventListener('click', () => {
        const files = fileInput.files;
        if (files.length === 0) {
            alert('Please select at least one file.');
            return;
        }

        const btn = document.getElementById('upload-btn');
        const progContainer = document.getElementById('progress-container');
        const progBar = document.getElementById('progress-bar');
        const progPercent = document.getElementById('progress-percent');
        const msgDiv = document.getElementById('upload-message');

        btn.disabled = true;
        btn.style.opacity = '0.5';
        progContainer.style.display = 'block';
        msgDiv.innerHTML = '';

        const formData = new FormData();
        for (const file of files) {
            formData.append('file', file);
        }

        const xhr = new XMLHttpRequest();
        xhr.open('POST', '/upload', true);

        xhr.upload.onprogress = (e) => {
            if (e.lengthComputable) {
                const percent = Math.round((e.loaded / e.total) * 100);
                progBar.style.width = percent + '%';
                progPercent.textContent = percent + '%';
            }
        };

        xhr.onload = () => {
            btn.disabled = false;
            btn.style.opacity = '1';
            if (xhr.status === 200) {
                msgDiv.innerHTML = '<div class="status-msg status-success">Successfully uploaded files!</div>';
                progContainer.style.display = 'none';
                fileInput.value = '';
                filesCountDiv.textContent = 'No files selected';
            } else {
                msgDiv.innerHTML = '<div class="status-msg status-error">Upload failed. Server responded with status: ' + xhr.status + '</div>';
            }
        };

        xhr.onerror = () => {
            btn.disabled = false;
            btn.style.opacity = '1';
            msgDiv.innerHTML = '<div class="status-msg status-error">A network error occurred. Make sure the server is running and accessible.</div>';
        };

        xhr.send(formData);
    });
</script>
"""

def get_icon(name, is_dir=False):
    if is_dir:
        return "/assets/folder.svg"
    ext = os.path.splitext(name)[1].lower()
    return "/assets/" + FILE_ICON_BY_EXTENSION.get(ext, 'document.svg')

class StyledHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        request_path = urllib.parse.urlsplit(path).path
        if request_path == "/assets" or request_path.startswith("/assets/"):
            asset_name = os.path.basename(urllib.parse.unquote(request_path))
            return os.path.join(ASSETS_DIR, asset_name)
        return super().translate_path(path)

    def _is_server_file(self, path):
        return os.path.normcase(os.path.realpath(path)) == os.path.normcase(os.path.realpath(__file__))

    def send_head(self):
        if self._is_server_file(self.translate_path(self.path)):
            self.send_error(404, "File not found")
            return None
        return super().send_head()

    def do_GET(self):
        if self.path == '/upload':
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            html = HTML_TEMPLATE.format(title=SERVER_TITLE, content=UPLOAD_PAGE_TEMPLATE)
            self.wfile.write(html.encode("utf-8"))
            return
        return super().do_GET()

    def list_directory(self, path):
        if os.path.normcase(os.path.realpath(path)) == os.path.normcase(os.path.realpath(ASSETS_DIR)):
            self.send_error(404, "Directory not found")
            return None

        try:
            list = os.listdir(path)
        except OSError:
            self.send_error(404, "No permission to access directory")
            return None

        list = [
            f for f in list
            if not f.startswith('.')
            and not self._is_server_file(os.path.join(path, f))
            and os.path.normcase(os.path.realpath(os.path.join(path, f))) != os.path.normcase(os.path.realpath(ASSETS_DIR))
        ]
        list.sort(key=lambda x: (not os.path.isdir(os.path.join(path, x)), x.lower()))

        rel_path = os.path.relpath(path, os.getcwd())
        if rel_path == '.':
            breadcrumbs = '<a href="/">Root</a>'
        else:
            parts = rel_path.split(os.sep)
            current = ""
            links = []
            for p in parts:
                current += "/" + p
                links.append(f'<a href="{urllib.parse.quote(current, safe="/")}">{html_utils.escape(p)}</a>')
            breadcrumbs = f'<a href="/">Root</a> / ' + " / ".join(links)

        items_html = '<div class="search-container"><input type="text" class="search-input" placeholder="Search files and folders..."></div>'
        items_html += '<div class="grid">'

        for name in list:
            full_path = os.path.join(path, name)
            is_dir = os.path.isdir(full_path)
            icon = get_icon(name, is_dir)
            safe_name = html_utils.escape(name)
            url_name = urllib.parse.quote(name, safe="")
            safe_url_name = html.escape(url_name, quote=True)
            link = f"{url_name}/" if is_dir else url_name
            size = ""
            if not is_dir:
                size_bytes = os.path.getsize(full_path)
                for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                    if size_bytes < 1024:
                        size = f"{size_bytes:.1f} {unit}"
                        break
                    size_bytes /= 1024

            if not is_dir and os.path.splitext(name)[1].lower() in IMAGE_PREVIEW_EXTENSIONS:
                preview = (
                        f'<img class="item-preview" src="{safe_url_name}" alt="{safe_name}" loading="lazy" '
                        f'onerror="this.onerror=null;this.src=\'{icon}\';this.className=\'item-icon\';">'
                )
            else:
                preview = f'<img class="item-icon" src="{icon}" alt="" loading="lazy">'

            items_html += f'''
                <a href="{html_utils.escape(link, quote=True)}" class="item">
                        {preview}
                        <div class="item-name" title="{safe_name}">{safe_name}</div>
                    <div class="item-info">{ "Folder" if is_dir else size }</div>
                </a>
            '''

        items_html += '</div>'
        content = f'''
            <div class="breadcrumb">{breadcrumbs}</div>
            {items_html}
        '''
        html = HTML_TEMPLATE.format(title=SERVER_TITLE, content=content)
        encoded = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)
        return None

    def do_POST(self):
        if self.path == '/upload':
            print(f"ðŸ“© Upload request received from {self.client_address}")

            content_type = self.headers.get('Content-Type')
            if not content_type or 'multipart/form-data' not in content_type:
                self.send_error(400, "Unsupported Content-Type")
                return

            match = re.search(r'boundary=(.+)', content_type)
            if not match:
                self.send_error(400, "Missing boundary in Content-Type")
                return
            boundary = match.group(1).strip()
            boundary_bytes = b'--' + boundary.encode('utf-8')

            try:
                # Streamed parser to handle large files
                uploaded_count = 0
                content_length = int(self.headers.get('Content-Length', 0))
                bytes_read = 0

                # Temporary buffer to handle boundary crossing
                buffer = b""

                while bytes_read < content_length:
                    chunk = self.rfile.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    bytes_read += len(chunk)
                    buffer += chunk

                    # Check if we have a boundary in the current buffer
                    if boundary_bytes in buffer:
                        # Split the buffer into parts
                        parts = buffer.split(boundary_bytes)

                        # Process all but the last part (which might be incomplete)
                        for i in range(len(parts) - 1):
                            part = parts[i]
                            if part.strip() and b'Content-Disposition' in part:
                                # Extract headers and data
                                header_end = part.find(b'\r\n\r\n')
                                if header_end != -1:
                                    header_section = part[:header_end].decode('utf-8', errors='ignore')
                                    data = part[header_end+4:]

                                    # Remove trailing \r\n
                                    if data.endswith(b'\r\n'):
                                        data = data[:-2]

                                    filename_match = re.search(r'filename="([^"]+)"', header_section)
                                    if filename_match:
                                        filename = os.path.basename(filename_match.group(1))
                                        print(f"  -> Saving file: {filename} ({len(data)} bytes)")
                                        with open(filename, 'wb') as f:
                                            f.write(data)
                                        uploaded_count += 1

                        # Keep only the last part in the buffer
                        buffer = parts[-1]

                if uploaded_count > 0:
                    print(f"âœ… Successfully uploaded {uploaded_count} file(s)")
                    self.send_response(200)
                    self.send_header("Content-type", "text/html; charset=utf-8")
                    self.end_headers()
                    msg = f'<div class="status-msg status-success">Successfully uploaded {uploaded_count} file(s)!</div>'
                    html = HTML_TEMPLATE.format(title=SERVER_TITLE, content=f'''
                        <div class="upload-card">
                            {msg}
                            <div style="margin-top: 2rem; display: flex; gap: 1rem; justify-content: center;">
                                <a href="/" class="btn btn-primary">Back to Files</a>
                                <a href="/upload" class="btn btn-outline">Upload Another</a>
                            </div>
                        </div>
                    ''')
                    self.wfile.write(html.encode("utf-8"))
                    return
                else:
                    print("âš ï¸ No files were successfully parsed from the request")

            except Exception as e:
                print(f"âŒ Error during streaming upload: {e}")
                import traceback
                traceback.print_exc()
                self.send_response(500)
                self.end_headers()
                self.wfile.write(f"Internal Server Error: {e}".encode("utf-8"))
                return

            self.send_response(400)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            msg = '<div class="status-msg status-error">No valid files selected for upload.</div>'
            html = HTML_TEMPLATE.format(title=SERVER_TITLE, content=f'''
                <div class="upload-card">
                    {msg}
                    <a href="/upload" class="btn btn-primary" style="display:block; margin: 2rem auto; width: fit-content;">Try Again</a>
                </div>
            ''')
            self.wfile.write(html.encode("utf-8"))
            return

        return super().do_POST()

class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True

if __name__ == "__main__":
    port = DEFAULT_PORT
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"Invalid port provided. Using default {DEFAULT_PORT}")

    with ThreadedTCPServer(("", port), StyledHTTPRequestHandler) as httpd:
        print(f"ðŸš€ Server started at http://localhost:{port}")
        print(f"ðŸ“ Serving files from: {os.getcwd()}")
        print(f"ðŸ’¡ Use Ctrl+C to stop the server")
        httpd.serve_forever()