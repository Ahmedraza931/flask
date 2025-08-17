from flask import Blueprint, request, jsonify, send_file
import requests
import tempfile
import os
import zipfile
import subprocess

# Create blueprint
download_bp = Blueprint("download", __name__)

def convert_drive_link(url: str) -> str:
    """
    Convert Google Drive 'view' or 'file' URLs into direct download links.
    """
    if "drive.google.com" in url:
        if "/file/d/" in url:
            file_id = url.split("/file/d/")[1].split("/")[0]
            return f"https://drive.google.com/uc?export=download&id={file_id}"
        elif "/open?id=" in url:
            file_id = url.split("id=")[1]
            return f"https://drive.google.com/uc?export=download&id={file_id}"
    return url

@download_bp.route("/file", methods=["POST"])
def download_file():
    """
    Download a single Google Drive file (PDF, DOCX, ZIP, etc.)
    """
    try:
        data = request.get_json()
        if not data or "url" not in data:
            return jsonify({"error": "No URL provided"}), 400

        url = convert_drive_link(data["url"])
        response = requests.get(url, stream=True)

        if response.status_code != 200:
            return jsonify({"error": f"Failed to fetch file (status {response.status_code})"}), 400

        tmp_file = tempfile.NamedTemporaryFile(delete=False)
        for chunk in response.iter_content(chunk_size=8192):
            tmp_file.write(chunk)
        tmp_file.close()

        filename = "downloaded_file"
        if "content-disposition" in response.headers:
            cd = response.headers["content-disposition"]
            if "filename=" in cd:
                filename = cd.split("filename=")[-1].replace('"', '').strip()

        return send_file(tmp_file.name, as_attachment=True, download_name=filename)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@download_bp.route("/video", methods=["POST"])
def download_video():
    """
    Download a Google Drive video using yt-dlp.
    """
    try:
        data = request.get_json()
        if not data or "url" not in data:
            return jsonify({"error": "No URL provided"}), 400

        url = data["url"]
        tmp_dir = tempfile.mkdtemp()
        output_path = os.path.join(tmp_dir, "video.mp4")

        # Run yt-dlp command
        cmd = ["yt-dlp", "-o", output_path, url]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            return jsonify({"error": f"yt-dlp failed: {result.stderr}"}), 400

        return send_file(output_path, as_attachment=True, download_name="video.mp4")

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@download_bp.route("/folder", methods=["POST"])
def download_folder():
    """
    Download all files in a Google Drive folder (zip them).
    """
    try:
        data = request.get_json()
        if not data or "url" not in data:
            return jsonify({"error": "No URL provided"}), 400

        folder_url = data["url"]
        # 🔹 This part requires Google Drive API to list folder contents
        # For now, we simulate by zipping the folder link
        tmp_dir = tempfile.mkdtemp()
        zip_path = os.path.join(tmp_dir, "folder.zip")

        with zipfile.ZipFile(zip_path, "w") as zipf:
            zipf.writestr("README.txt", f"Folder download not fully implemented.\nURL: {folder_url}")

        return send_file(zip_path, as_attachment=True, download_name="folder.zip")

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@download_bp.route("/start", methods=["POST"])
def download_start():
    """
    Smart endpoint: auto-detect file, video, or folder.
    """
    try:
        data = request.get_json()
        if not data or "url" not in data:
            return jsonify({"error": "No URL provided"}), 400

        url = data["url"]

        if "folders" in url:
            return download_folder()
        elif "file/d/" in url:
            # Try video first, fallback to file
            try:
                return download_video()
            except Exception:
                return download_file()
        else:
            return download_file()

    except Exception as e:
        return jsonify({"error": str(e)}), 500
