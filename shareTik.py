import http.server
from http import cookies
import socketserver
import os
import html as html_utils
import urllib.parse
import sys
import re
import json
import uuid
from datetime import datetime

# --- Configuration ---
DEFAULT_PORT = 8000
SERVER_TITLE = "ShareTik"
CHUNK_SIZE = 64 * 1024  # 64KB chunks for memory efficiency
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
LOG_FILE = os.path.join(BASE_DIR, "uploads.log")
SESSION_COOKIE_NAME = "sharetik_session"

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

# Sessions en mémoire : {session_id: {"pseudo": str, "ip": str, "connected_at": str}}
ACTIVE_SESSIONS = {}

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
            gap: 1rem;
            flex-wrap: wrap;
        }}
        .logo {{
            font-size: 1.25rem;
            font-weight: 700;
            color: var(--accent);
            text-decoration: none;
        }}
        .nav-links {{
            display: flex;
            gap: 0.75rem;
            align-items: center;
            flex-wrap: wrap;
        }}
        .user-badge {{
            font-size: 0.85rem;
            color: var(--text-muted);
            background: var(--bg-color);
            border: 1px solid var(--border);
            padding: 0.45rem 0.85rem;
            border-radius: 0.5rem;
        }}
        .user-badge strong {{
            color: var(--accent);
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
            box-sizing: border-box;
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
        .login-card {{
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 1.5rem;
            padding: 3rem;
            text-align: center;
            max-width: 460px;
            margin: 2rem auto;
        }}
        .pseudo-box {{
            width: 100%;
            max-width: 320px;
            text-align: left;
            margin: 0 auto 1.5rem auto;
        }}
        .pseudo-label {{
            display: block;
            font-size: 0.85rem;
            color: var(--text-muted);
            margin-bottom: 0.4rem;
        }}
        .pseudo-input {{
            width: 100%;
            padding: 0.75rem 1rem;
            border-radius: 0.75rem;
            background: var(--bg-color);
            border: 1px solid var(--border);
            color: var(--text-main);
            font-size: 0.95rem;
            outline: none;
            transition: border-color 0.2s;
            box-sizing: border-box;
        }}
        .pseudo-input:focus {{
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
            {header_actions}
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

LOGIN_PAGE_TEMPLATE = """
<div class="login-card">
    <h2 style="margin-top: 0; color: var(--text-main);">Welcome to ShareTik</h2>
    <p style="color: var(--text-muted); margin-bottom: 2rem;">Enter your pseudo to start sharing files</p>
    <form method="POST" action="/login" id="login-form">
        <div class="pseudo-box">
            <label for="pseudo-input" class="pseudo-label">Pseudo</label>
            <input id="pseudo-input" name="pseudo" type="text" class="pseudo-input" placeholder="Enter your pseudo..." maxlength="60" required autofocus>
        </div>
        <button type="submit" class="btn btn-primary" style="padding: 0.75rem 2rem; font-size: 1rem;">Continue</button>
    </form>
</div>
<script>
    const loginForm = document.getElementById('login-form');
    const pseudoInput = document.getElementById('pseudo-input');
    const savedPseudo = localStorage.getItem('sharetik_pseudo');
    if (savedPseudo && !pseudoInput.value) {{
        pseudoInput.value = savedPseudo;
    }}
    loginForm.addEventListener('submit', () => {{
        const val = pseudoInput.value.trim();
        if (val) {{
            localStorage.setItem('sharetik_pseudo', val);
        }}
    }});
</script>
"""

UPLOAD_PAGE_TEMPLATE = """
<div class="upload-card">
    <h2 style="margin-top: 0; color: var(--text-main);">Upload New Files</h2>
    <p style="color: var(--text-muted); margin-bottom: 2rem;">Uploading as <strong style="color: var(--accent);">{pseudo}</strong> to the current directory</p>
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

    fileInput.addEventListener('change', () => {{
        const count = fileInput.files.length;
        filesCountDiv.textContent = count > 0 ? `${{count}} file${{count > 1 ? 's' : ''}} selected` : 'No files selected';
    }});

    document.getElementById('upload-btn').addEventListener('click', () => {{
        const files = fileInput.files;
        if (files.length === 0) {{
            alert('Please select at least one file.');
            return;
        }}

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
        for (const file of files) {{
            formData.append('file', file);
        }}

        const xhr = new XMLHttpRequest();
        xhr.open('POST', '/upload', true);

        xhr.upload.onprogress = (e) => {{
            if (e.lengthComputable) {{
                const percent = Math.round((e.loaded / e.total) * 100);
                progBar.style.width = percent + '%';
                progPercent.textContent = percent + '%';
            }}
        }};

        xhr.onload = () => {{
            btn.disabled = false;
            btn.style.opacity = '1';
            if (xhr.status === 200) {{
                msgDiv.innerHTML = '<div class="status-msg status-success">Successfully uploaded files!</div>';
                progContainer.style.display = 'none';
                fileInput.value = '';
                filesCountDiv.textContent = 'No files selected';
            }} else {{
                msgDiv.innerHTML = '<div class="status-msg status-error">Upload failed. Server responded with status: ' + xhr.status + '</div>';
            }}
        }};

        xhr.onerror = () => {{
            btn.disabled = false;
            btn.style.opacity = '1';
            msgDiv.innerHTML = '<div class="status-msg status-error">A network error occurred. Make sure the server is running and accessible.</div>';
        }};

        xhr.send(formData);
    }});
</script>
"""


def get_icon(name, is_dir=False):
    if is_dir:
        return "/assets/folder.svg"
    ext = os.path.splitext(name)[1].lower()
    return "/assets/" + FILE_ICON_BY_EXTENSION.get(ext, 'document.svg')


def record_pseudo_upload(pseudo, ip, filename, size):
    entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "pseudo": pseudo,
        "ip": ip,
        "filename": filename,
        "size": size,
    }
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        pass


def get_latest_pseudos_by_file():
    pseudos = {}
    if not os.path.exists(LOG_FILE):
        return pseudos
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    fname = data.get("filename")
                    pseudo = data.get("pseudo")
                    if fname and pseudo:
                        pseudos[fname] = pseudo
                except json.JSONDecodeError:
                    continue
    except OSError:
        pass
    return pseudos


class StyledHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def get_session(self):
        cookie_header = self.headers.get("Cookie")
        if not cookie_header:
            return None, None
        jar = cookies.SimpleCookie()
        try:
            jar.load(cookie_header)
        except cookies.CookieError:
            return None, None
        morsel = jar.get(SESSION_COOKIE_NAME)
        if not morsel:
            return None, None
        sid = morsel.value
        session = ACTIVE_SESSIONS.get(sid)
        if not session:
            return None, sid
        return session, sid

    def build_header_actions(self, session):
        if not session:
            return '<a href="/" class="btn btn-outline">Pseudo</a>'
        safe_pseudo = html_utils.escape(session["pseudo"])
        return f'''
            <span class="user-badge">Pseudo: <strong>{safe_pseudo}</strong></span>
            <a href="/upload" class="btn btn-primary">↑ Upload File</a>
            <a href="/" class="btn btn-outline">Home</a>
        '''

    def render_page(self, content, session=None):
        return HTML_TEMPLATE.format(
            title=SERVER_TITLE,
            header_actions=self.build_header_actions(session),
            content=content,
        )

    def render_login(self, session=None):
        html_doc = self.render_page(LOGIN_PAGE_TEMPLATE, session=session)
        encoded = html_doc.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def translate_path(self, path):
        request_path = urllib.parse.urlsplit(path).path
        if request_path == "/assets" or request_path.startswith("/assets/"):
            asset_name = os.path.basename(urllib.parse.unquote(request_path))
            return os.path.join(ASSETS_DIR, asset_name)
        return super().translate_path(path)

    def _is_server_file(self, path):
        real_target = os.path.normcase(os.path.realpath(path))
        return real_target in {
            os.path.normcase(os.path.realpath(__file__)),
            os.path.normcase(os.path.realpath(LOG_FILE)),
        }

    def send_head(self):
        if self._is_server_file(self.translate_path(self.path)):
            self.send_error(404, "File not found")
            return None
        return super().send_head()

    def do_GET(self):
        request_path = urllib.parse.urlsplit(self.path).path

        if request_path == "/assets" or request_path.startswith("/assets/"):
            return super().do_GET()

        session, _ = self.get_session()
        if not session:
            self.render_login()
            return

        if request_path == "/upload":
            page_content = UPLOAD_PAGE_TEMPLATE.format(pseudo=html_utils.escape(session["pseudo"]))
            response_html = self.render_page(page_content, session=session)
            encoded = response_html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)
            return

        return super().do_GET()

    def list_directory(self, path):
        session, _ = self.get_session()
        if not session:
            self.render_login()
            return None

        if os.path.normcase(os.path.realpath(path)) == os.path.normcase(os.path.realpath(ASSETS_DIR)):
            self.send_error(404, "Directory not found")
            return None

        try:
            entries = os.listdir(path)
        except OSError:
            self.send_error(404, "No permission to access directory")
            return None

        entries = [
            f for f in entries
            if not f.startswith('.')
            and not self._is_server_file(os.path.join(path, f))
            and os.path.normcase(os.path.realpath(os.path.join(path, f))) != os.path.normcase(os.path.realpath(ASSETS_DIR))
        ]
        entries.sort(key=lambda x: (not os.path.isdir(os.path.join(path, x)), x.lower()))

        pseudos_map = get_latest_pseudos_by_file()

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
            breadcrumbs = '<a href="/">Root</a> / ' + " / ".join(links)

        items_html = '<div class="search-container"><input type="text" class="search-input" placeholder="Search files and folders..."></div>'
        items_html += '<div class="grid">'

        for name in entries:
            full_path = os.path.join(path, name)
            is_dir = os.path.isdir(full_path)
            icon = get_icon(name, is_dir)
            safe_name = html_utils.escape(name)
            url_name = urllib.parse.quote(name, safe="")
            safe_url_name = html_utils.escape(url_name, quote=True)
            link = f"{url_name}/" if is_dir else url_name
            size = ""
            if not is_dir:
                size_bytes = os.path.getsize(full_path)
                for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                    if size_bytes < 1024:
                        size = f"{size_bytes:.1f} {unit}"
                        break
                    size_bytes /= 1024

            if is_dir:
                info_text = "Folder"
            else:
                pseudo = pseudos_map.get(name)
                info_text = f"{size} • par {html_utils.escape(pseudo)}" if pseudo else size

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
                    <div class="item-info">{info_text}</div>
                </a>
            '''

        items_html += '</div>'
        content = f'''
            <div class="breadcrumb">{breadcrumbs}</div>
            {items_html}
        '''

        response_html = self.render_page(content, session=session)
        encoded = response_html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)
        return None

    def do_POST(self):
        request_path = urllib.parse.urlsplit(self.path).path

        if request_path == '/login':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length).decode('utf-8', errors='ignore')
            params = urllib.parse.parse_qs(body)
            pseudo = (params.get('pseudo', [''])[0]).strip()[:60]
            if not pseudo:
                self.render_login()
                return

            sid = uuid.uuid4().hex
            ACTIVE_SESSIONS[sid] = {
                "pseudo": pseudo,
                "ip": self.client_address[0],
                "connected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            print(f"🔐 Session started for '{pseudo}' ({self.client_address[0]})")

            self.send_response(302)
            self.send_header("Set-Cookie", f"{SESSION_COOKIE_NAME}={sid}; Path=/; HttpOnly; SameSite=Lax")
            self.send_header("Location", "/")
            self.end_headers()
            return

        if request_path == '/upload':
            session, _ = self.get_session()
            if not session:
                self.send_error(401, "Session required")
                return

            pseudo = session["pseudo"]
            print(f"📩 Upload request from '{pseudo}' {self.client_address}")

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
                uploaded_files = []
                content_length = int(self.headers.get('Content-Length', 0))
                bytes_read = 0
                buffer = b""

                while bytes_read < content_length:
                    chunk = self.rfile.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    bytes_read += len(chunk)
                    buffer += chunk

                    if boundary_bytes in buffer:
                        parts = buffer.split(boundary_bytes)

                        for i in range(len(parts) - 1):
                            part = parts[i]
                            if part.strip() and b'Content-Disposition' in part:
                                header_end = part.find(b'\r\n\r\n')
                                if header_end != -1:
                                    header_section = part[:header_end].decode('utf-8', errors='ignore')
                                    data = part[header_end+4:]

                                    if data.endswith(b'\r\n'):
                                        data = data[:-2]

                                    filename_match = re.search(r'filename="([^"]+)"', header_section)
                                    if filename_match:
                                        filename = os.path.basename(filename_match.group(1))
                                        if filename:
                                            print(f"  -> Saving file: {filename} ({len(data)} bytes)")
                                            with open(filename, 'wb') as f:
                                                f.write(data)
                                            uploaded_files.append((filename, len(data)))

                        buffer = parts[-1]

                if uploaded_files:
                    client_ip = self.client_address[0]
                    for fname, fsize in uploaded_files:
                        print(f"  -> Pseudo: '{pseudo}' | File: '{fname}' ({fsize} bytes)")
                        record_pseudo_upload(pseudo, client_ip, fname, fsize)

                    print(f"✅ Successfully uploaded {len(uploaded_files)} file(s) from '{pseudo}'")
                    self.send_response(200)
                    self.send_header("Content-type", "text/html; charset=utf-8")
                    self.end_headers()
                    msg = f'<div class="status-msg status-success">Successfully uploaded {len(uploaded_files)} file(s) as {html_utils.escape(pseudo)}!</div>'
                    response_html = self.render_page(f'''
                        <div class="upload-card">
                            {msg}
                            <div style="margin-top: 2rem; display: flex; gap: 1rem; justify-content: center;">
                                <a href="/" class="btn btn-primary">Back to Files</a>
                                <a href="/upload" class="btn btn-outline">Upload Another</a>
                            </div>
                        </div>
                    ''', session=session)
                    self.wfile.write(response_html.encode("utf-8"))
                    return
                else:
                    print("⚠️ No files were successfully parsed from the request")

            except Exception as e:
                print(f"❌ Error during streaming upload: {e}")
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
            response_html = self.render_page(f'''
                <div class="upload-card">
                    {msg}
                    <a href="/upload" class="btn btn-primary" style="display:block; margin: 2rem auto; width: fit-content;">Try Again</a>
                </div>
            ''', session=session)
            self.wfile.write(response_html.encode("utf-8"))
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
        print(f"🚀 Server started at http://localhost:{port}")
        print(f"📁 Serving files from: {os.getcwd()}")
        print(f"💡 Use Ctrl+C to stop the server")
        httpd.serve_forever()