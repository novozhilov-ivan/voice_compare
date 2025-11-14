"""
YouTube video downloader component
"""

import logging
from pathlib import Path

import yt_dlp

logger = logging.getLogger(__name__)


class YouTubeDownloader:
    """Download videos and audio from YouTube"""

    def __init__(self, output_dir: str = "data/videos", cookies_file: str | None = None):
        """
        Initialize YouTube downloader

        Args:
            output_dir: Directory to save downloaded videos
            cookies_file: Path to Netscape format cookies file (e.g., "cookies.txt")
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.cookies_file = cookies_file

        logger.info(f"YouTubeDownloader.__init__ called with cookies_file={cookies_file}")

        # Common options to bypass bot detection
        common_opts = {
            # Anti-bot detection headers
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "referer": "https://www.youtube.com/",
            # Network settings
            "socket_timeout": 30,
            "retries": 10,
            "fragment_retries": 10,
            # Additional options
            "nocheckcertificate": True,
            "no_check_certificates": True,
        }

        # Add cookies if file provided
        if cookies_file:
            cookies_path = Path(cookies_file)
            logger.info(f"Checking cookies file: {cookies_file}, exists={cookies_path.exists()}")
            if cookies_path.exists():
                common_opts["cookiefile"] = cookies_file
                logger.info(f"✓ Cookies added to yt-dlp options: {cookies_file}")
            else:
                logger.warning(f"✗ Cookies file not found: {cookies_file}")
        else:
            logger.warning("✗ No cookies_file provided to YouTubeDownloader")

        # yt-dlp options for video download
        self.ydl_opts_video = {
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "outtmpl": str(self.output_dir / "%(id)s.%(ext)s"),
            "quiet": False,
            "no_warnings": False,
            "extract_flat": False,
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": ["en", "ru"],
            **common_opts,
        }

        # yt-dlp options for audio only
        self.ydl_opts_audio = {
            "format": "bestaudio/best",
            "outtmpl": str(self.output_dir / "%(id)s.%(ext)s"),
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "wav",
                    "preferredquality": "192",
                }
            ],
            "quiet": False,
            "no_warnings": False,
            **common_opts,
        }

    def download_video(
        self,
        url: str,
        audio_only: bool = False,
        skip_if_exists: bool = True,
        progress_callback: callable = None,
    ) -> str:
        """
        Download a single video from YouTube

        Args:
            url: YouTube video URL
            audio_only: If True, download only audio
            skip_if_exists: If True, skip download if file already exists
            progress_callback: Optional callback function(progress_dict) for download progress

        Returns:
            Path to downloaded file
        """
        try:
            logger.info(f"Downloading video from: {url}")

            opts = self.ydl_opts_audio if audio_only else self.ydl_opts_video

            # Add progress callback if provided
            if progress_callback:
                opts = opts.copy()  # Don't modify the original
                opts["progress_hooks"] = [progress_callback]

            # Debug: log if cookies are in options
            if "cookiefile" in opts:
                logger.info(f"✓ yt-dlp will use cookiefile: {opts['cookiefile']}")
            else:
                logger.warning("✗ NO cookiefile in yt-dlp options!")

            with yt_dlp.YoutubeDL(opts) as ydl:
                # Get video info first
                info = ydl.extract_info(url, download=False)
                video_id = info["id"]

                # Check if file already exists (caching)
                if skip_if_exists:
                    if audio_only:
                        existing_file = self.output_dir / f"{video_id}.wav"
                    else:
                        for ext in ["mp4", "webm", "mkv"]:
                            potential_path = self.output_dir / f"{video_id}.{ext}"
                            if potential_path.exists():
                                existing_file = potential_path
                                break
                        else:
                            existing_file = None

                    if existing_file and existing_file.exists():
                        logger.info(f"✓ Video already exists (cached): {existing_file}")
                        return str(existing_file)

                # Download
                logger.info(f"Starting download for video_id: {video_id}")
                ydl.download([url])

                # Find downloaded file
                if audio_only:
                    file_path = self.output_dir / f"{video_id}.wav"
                else:
                    # Find the actual file (could be mp4, webm, etc.)
                    for ext in ["mp4", "webm", "mkv"]:
                        potential_path = self.output_dir / f"{video_id}.{ext}"
                        if potential_path.exists():
                            file_path = potential_path
                            break
                    else:
                        raise FileNotFoundError(f"Downloaded file not found for {video_id}")

                logger.info(f"Downloaded to: {file_path}")
                return str(file_path)

        except Exception as e:
            logger.error(f"Error downloading video {url}: {str(e)}")
            raise

    def get_video_info(self, url: str) -> dict:
        """
        Get video information without downloading

        Args:
            url: YouTube video URL

        Returns:
            Dictionary with video information
        """
        try:
            opts = {
                "quiet": True,
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            }
            if self.cookies_file and Path(self.cookies_file).exists():
                opts["cookiefile"] = self.cookies_file

            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)

                return {
                    "id": info.get("id"),
                    "title": info.get("title"),
                    "duration": info.get("duration"),
                    "uploader": info.get("uploader"),
                    "upload_date": info.get("upload_date"),
                    "view_count": info.get("view_count"),
                    "description": info.get("description"),
                    "thumbnail": info.get("thumbnail"),
                }

        except Exception as e:
            logger.error(f"Error getting video info for {url}: {str(e)}")
            raise

    def get_playlist_videos(self, playlist_url: str) -> list[str]:
        """
        Get all video URLs from a playlist

        Args:
            playlist_url: YouTube playlist URL

        Returns:
            List of video URLs
        """
        try:
            logger.info(f"Getting playlist videos from: {playlist_url}")

            opts = {
                "extract_flat": True,
                "quiet": True,
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            }
            if self.cookies_file and Path(self.cookies_file).exists():
                opts["cookiefile"] = self.cookies_file

            with yt_dlp.YoutubeDL(opts) as ydl:
                playlist_info = ydl.extract_info(playlist_url, download=False)

                if "entries" not in playlist_info:
                    raise ValueError("Not a valid playlist URL")

                video_urls = []
                for entry in playlist_info["entries"]:
                    if entry is not None:
                        video_id = entry.get("id")
                        if video_id:
                            video_urls.append(f"https://www.youtube.com/watch?v={video_id}")

                logger.info(f"Found {len(video_urls)} videos in playlist")
                return video_urls

        except Exception as e:
            logger.error(f"Error getting playlist videos: {str(e)}")
            raise

    def download_multiple_videos(self, urls: list[str], audio_only: bool = False) -> list[str]:
        """
        Download multiple videos

        Args:
            urls: List of YouTube video URLs
            audio_only: If True, download only audio

        Returns:
            List of paths to downloaded files
        """
        downloaded_files = []

        for i, url in enumerate(urls):
            logger.info(f"Downloading video {i + 1}/{len(urls)}")
            try:
                file_path = self.download_video(url, audio_only)
                downloaded_files.append(file_path)
            except Exception as e:
                logger.error(f"Failed to download {url}: {str(e)}")
                continue

        return downloaded_files

    def get_channel_videos(self, channel_url: str, max_videos: int | None = None) -> list[str]:
        """
        Get video URLs from a channel

        Args:
            channel_url: YouTube channel URL
            max_videos: Maximum number of videos to retrieve

        Returns:
            List of video URLs
        """
        try:
            logger.info(f"Getting videos from channel: {channel_url}")

            opts = {
                "extract_flat": True,
                "quiet": True,
                "playlistend": max_videos if max_videos else None,
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            }
            if self.cookies_file and Path(self.cookies_file).exists():
                opts["cookiefile"] = self.cookies_file

            # Add /videos to channel URL if not present
            if "/videos" not in channel_url:
                channel_url = channel_url.rstrip("/") + "/videos"

            with yt_dlp.YoutubeDL(opts) as ydl:
                channel_info = ydl.extract_info(channel_url, download=False)

                video_urls = []
                entries = channel_info.get("entries", [])

                for entry in entries:
                    if entry is not None:
                        video_id = entry.get("id")
                        if video_id:
                            video_urls.append(f"https://www.youtube.com/watch?v={video_id}")

                logger.info(f"Found {len(video_urls)} videos in channel")
                return video_urls

        except Exception as e:
            logger.error(f"Error getting channel videos: {str(e)}")
            raise

    def cleanup_old_files(self, keep_recent: int = 10):
        """
        Clean up old downloaded files

        Args:
            keep_recent: Number of recent files to keep
        """
        try:
            files = sorted(self.output_dir.glob("*"), key=lambda x: x.stat().st_mtime, reverse=True)

            for file in files[keep_recent:]:
                logger.info(f"Removing old file: {file}")
                file.unlink()

        except Exception as e:
            logger.error(f"Error cleaning up files: {str(e)}")
