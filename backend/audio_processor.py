"""
Audio extraction and processing component
"""

import logging
from pathlib import Path

import ffmpeg
import librosa
import noisereduce as nr
import numpy as np
import soundfile as sf

logger = logging.getLogger(__name__)


class AudioProcessor:
    """Extract and process audio from video files"""

    def __init__(self, output_dir: str = "data/audio"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.sample_rate = 16000  # Standard for speech processing

    def extract_audio(
        self,
        video_path: str,
        output_path: str | None = None,
        start_time: float | None = None,
        end_time: float | None = None,
    ) -> str:
        """
        Extract audio from video file

        Args:
            video_path: Path to video file
            output_path: Optional output path for audio file
            start_time: Start time in seconds (None = from beginning)
            end_time: End time in seconds (None = until end)

        Returns:
            Path to extracted audio file
        """
        try:
            video_path = Path(video_path)
            if not video_path.exists():
                raise FileNotFoundError(f"Video file not found: {video_path}")

            if output_path is None:
                # Add time range to filename if specified
                time_suffix = ""
                if start_time is not None or end_time is not None:
                    time_suffix = f"_{int(start_time or 0)}-{int(end_time) if end_time else 'end'}"
                output_path = self.output_dir / f"{video_path.stem}{time_suffix}.wav"
            else:
                output_path = Path(output_path)

            time_info = ""
            if start_time is not None or end_time is not None:
                time_info = f" (time range: {start_time or 0}s - {end_time or 'end'}s)"
            logger.info(f"Extracting audio from {video_path} to {output_path}{time_info}")

            # Use ffmpeg to extract audio with optional time range
            input_kwargs = {}
            if start_time is not None:
                input_kwargs["ss"] = start_time  # Seek to start time

            stream = ffmpeg.input(str(video_path), **input_kwargs)

            output_kwargs = {
                "acodec": "pcm_s16le",
                "ac": 1,  # mono
                "ar": str(self.sample_rate),  # sample rate
            }

            if end_time is not None:
                # Calculate duration from start
                duration = end_time - (start_time or 0)
                output_kwargs["t"] = duration

            stream = ffmpeg.output(stream, str(output_path), **output_kwargs)
            ffmpeg.run(stream, overwrite_output=True, quiet=True)

            logger.info(f"Audio extracted successfully to {output_path}")
            return str(output_path)

        except Exception as e:
            logger.error(f"Error extracting audio: {str(e)}")
            raise

    def load_audio(self, audio_path: str) -> tuple[np.ndarray, int]:
        """
        Load audio file

        Args:
            audio_path: Path to audio file

        Returns:
            Tuple of (audio data, sample rate)
        """
        try:
            audio, sr = librosa.load(audio_path, sr=self.sample_rate, mono=True)
            return audio, sr

        except Exception as e:
            logger.error(f"Error loading audio: {str(e)}")
            raise

    def save_audio(self, audio: np.ndarray, output_path: str, sample_rate: int | None = None):
        """
        Save audio to file

        Args:
            audio: Audio data
            output_path: Output file path
            sample_rate: Sample rate (uses default if not specified)
        """
        try:
            sr = sample_rate if sample_rate else self.sample_rate
            sf.write(output_path, audio, sr)
            logger.info(f"Audio saved to {output_path}")

        except Exception as e:
            logger.error(f"Error saving audio: {str(e)}")
            raise

    def reduce_noise(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        """
        Reduce noise in audio signal

        Args:
            audio: Audio data
            sample_rate: Sample rate

        Returns:
            Noise-reduced audio
        """
        try:
            logger.info("Reducing noise in audio")

            # Use noisereduce library
            reduced_noise = nr.reduce_noise(
                y=audio, sr=sample_rate, stationary=True, prop_decrease=0.8
            )

            return reduced_noise

        except Exception as e:
            logger.error(f"Error reducing noise: {str(e)}")
            return audio  # Return original if noise reduction fails

    def normalize_audio(self, audio: np.ndarray) -> np.ndarray:
        """
        Normalize audio amplitude

        Args:
            audio: Audio data

        Returns:
            Normalized audio
        """
        try:
            # Peak normalization
            max_amplitude = np.max(np.abs(audio))
            normalized = audio / max_amplitude * 0.95 if max_amplitude > 0 else audio

            return normalized

        except Exception as e:
            logger.error(f"Error normalizing audio: {str(e)}")
            return audio

    def trim_silence(self, audio: np.ndarray, sample_rate: int, top_db: int = 30) -> np.ndarray:
        """
        Trim silence from beginning and end of audio

        Args:
            audio: Audio data
            sample_rate: Sample rate
            top_db: Threshold in dB below reference to consider as silence

        Returns:
            Trimmed audio
        """
        try:
            trimmed, _ = librosa.effects.trim(audio, top_db=top_db)
            return trimmed

        except Exception as e:
            logger.error(f"Error trimming silence: {str(e)}")
            return audio

    def enhance_speech(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        """
        Enhance speech quality in audio

        Args:
            audio: Audio data
            sample_rate: Sample rate

        Returns:
            Enhanced audio
        """
        try:
            logger.info("Enhancing speech quality")

            # Reduce noise
            audio = self.reduce_noise(audio, sample_rate)

            # Normalize
            audio = self.normalize_audio(audio)

            # Trim silence
            audio = self.trim_silence(audio, sample_rate)

            return audio

        except Exception as e:
            logger.error(f"Error enhancing speech: {str(e)}")
            return audio

    def split_audio(
        self, audio: np.ndarray, sample_rate: int, segment_length: float = 30.0
    ) -> list:
        """
        Split audio into segments

        Args:
            audio: Audio data
            sample_rate: Sample rate
            segment_length: Length of each segment in seconds

        Returns:
            List of audio segments
        """
        try:
            segment_samples = int(segment_length * sample_rate)
            segments = []

            for i in range(0, len(audio), segment_samples):
                segment = audio[i : i + segment_samples]
                if len(segment) > sample_rate:  # Only keep segments > 1 second
                    segments.append(segment)

            logger.info(f"Split audio into {len(segments)} segments")
            return segments

        except Exception as e:
            logger.error(f"Error splitting audio: {str(e)}")
            return [audio]

    def extract_segment(
        self, audio: np.ndarray, sample_rate: int, start_time: float, end_time: float
    ) -> np.ndarray:
        """
        Extract a segment from audio

        Args:
            audio: Audio data
            sample_rate: Sample rate
            start_time: Start time in seconds
            end_time: End time in seconds

        Returns:
            Audio segment
        """
        try:
            start_sample = int(start_time * sample_rate)
            end_sample = int(end_time * sample_rate)

            segment = audio[start_sample:end_sample]
            return segment

        except Exception as e:
            logger.error(f"Error extracting segment: {str(e)}")
            raise

    def get_audio_duration(self, audio_path: str) -> float:
        """
        Get duration of audio file in seconds

        Args:
            audio_path: Path to audio file

        Returns:
            Duration in seconds
        """
        try:
            audio, sr = self.load_audio(audio_path)
            duration = len(audio) / sr
            return duration

        except Exception as e:
            logger.error(f"Error getting audio duration: {str(e)}")
            raise

    def convert_to_mono(self, audio: np.ndarray) -> np.ndarray:
        """
        Convert stereo audio to mono

        Args:
            audio: Audio data

        Returns:
            Mono audio
        """
        try:
            if len(audio.shape) > 1:
                audio = np.mean(audio, axis=1)
            return audio

        except Exception as e:
            logger.error(f"Error converting to mono: {str(e)}")
            return audio

    def resample_audio(self, audio: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
        """
        Resample audio to different sample rate

        Args:
            audio: Audio data
            orig_sr: Original sample rate
            target_sr: Target sample rate

        Returns:
            Resampled audio
        """
        try:
            if orig_sr != target_sr:
                audio = librosa.resample(audio, orig_sr=orig_sr, target_sr=target_sr)
            return audio

        except Exception as e:
            logger.error(f"Error resampling audio: {str(e)}")
            return audio

    def process_audio_file(
        self, audio_path: str, enhance: bool = True, output_path: str | None = None
    ) -> str:
        """
        Process audio file with all enhancements

        Args:
            audio_path: Path to audio file
            enhance: Whether to enhance audio
            output_path: Optional output path

        Returns:
            Path to processed audio file
        """
        try:
            # Load audio
            audio, sr = self.load_audio(audio_path)

            # Enhance if requested
            if enhance:
                audio = self.enhance_speech(audio, sr)

            # Save processed audio
            if output_path is None:
                input_path = Path(audio_path)
                output_path = self.output_dir / f"{input_path.stem}_processed.wav"

            self.save_audio(audio, str(output_path), sr)

            return str(output_path)

        except Exception as e:
            logger.error(f"Error processing audio file: {str(e)}")
            raise
