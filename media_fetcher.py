import requests
import urllib.parse
from config import PEXELS_API_KEY

class MediaFetcher:
    def __init__(self):
        self.api_key = PEXELS_API_KEY
        self.base_url = "https://api.pexels.com/videos/search"
        if not self.api_key:
            print("ERROR: PEXELS_API_KEY is not set in .env file. Please check the configuration.")

    def search_video(self, keyword: str, min_duration=2, target_width=1920, target_height=1080) -> str:
        """
        Search for a video clip with at least target resolution (default 1080p).
        Returns download URL of the best matching video file.
        """
        if not self.api_key:
            print(f"Media fetch skipped: No API key. Keyword was: '{keyword}'")
            return None

        keyword = keyword.strip()
        if not keyword:
            print("Warning: Received empty keyword for search.")
            return None

        encoded_keyword = urllib.parse.quote(keyword)
        params = {
            "query": encoded_keyword,
            "per_page": 10,
            "orientation": "landscape",
            "min_width": target_width,
            "min_height": target_height
        }
        headers = {"Authorization": self.api_key}

        print(f"Pexels API Request for '{keyword}' ---")
        try:
            resp = requests.get(self.base_url, headers=headers, params=params, timeout=10)
            if resp.status_code != 200:
                print(f"Pexels API error: {resp.status_code} - {resp.text[:200]}")
                return None

            data = resp.json()
            if not data.get("videos"):
                print(f"No videos found with min resolution {target_width}x{target_height}. Trying without resolution filter...")
                # Fallback: remove min_width/min_height
                params.pop("min_width", None)
                params.pop("min_height", None)
                resp = requests.get(self.base_url, headers=headers, params=params, timeout=10)
                if resp.status_code != 200:
                    return None
                data = resp.json()
                if not data.get("videos"):
                    print(f"No videos found for keyword '{keyword}'.")
                    return None

            # Select the video file with highest resolution (width * height)
            best_url = None
            best_resolution = 0
            for video in data["videos"]:
                for file in video.get("video_files", []):
                    # Skip if duration is too short
                    if file.get("duration", 0) < min_duration:
                        continue
                    width = file.get("width", 0)
                    height = file.get("height", 0)
                    resolution = width * height
                    # Prefer files that meet or exceed target resolution
                    if width >= target_width and height >= target_height:
                        if resolution > best_resolution:
                            best_resolution = resolution
                            best_url = file["link"]
            if best_url:
                print(f"Found video with resolution {best_resolution} pixels (target {target_width}x{target_height}).")
                return best_url

            # If no file meets the target, take the highest resolution available overall
            for video in data["videos"]:
                for file in video.get("video_files", []):
                    if file.get("duration", 0) < min_duration:
                        continue
                    width = file.get("width", 0)
                    height = file.get("height", 0)
                    resolution = width * height
                    if resolution > best_resolution:
                        best_resolution = resolution
                        best_url = file["link"]
            if best_url:
                print(f"No video meeting target resolution. Using best available: {best_resolution} pixels.")
                return best_url

            print(f"No suitable video found for '{keyword}'.")
            return None

        except Exception as e:
            print(f"Exception in search_video: {e}")
            return None

    def download_media(self, url: str, dest_path: str):
        try:
            print(f"Downloading high-res video from: {url}")
            r = requests.get(url, stream=True, timeout=30)
            r.raise_for_status()
            with open(dest_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"Successfully downloaded to: {dest_path}")
        except Exception as e:
            print(f"Failed to download media: {e}")