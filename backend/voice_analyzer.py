"""
Voice activity detection and audio quality analysis
"""
import numpy as np
import librosa
import webrtcvad
from typing import List, Tuple, Dict
import logging
import struct

logger = logging.getLogger(__name__)

class VoiceAnalyzer:
    """Detect voice activity and analyze audio quality"""

    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self.vad = webrtcvad.Vad()
        self.vad.set_mode(3)  # Aggressive mode (0-3, 3 is most aggressive)

    def detect_voice_activity(self, audio_path: str,
                             frame_duration: int = 30) -> List[Tuple[float, float]]:
        """
        Detect voice activity in audio file

        Args:
            audio_path: Path to audio file
            frame_duration: Frame duration in ms (10, 20, or 30)

        Returns:
            List of (start_time, end_time) tuples for voice segments
        """
        try:
            logger.info(f"Detecting voice activity in {audio_path}")

            # Load audio
            audio, sr = librosa.load(audio_path, sr=self.sample_rate, mono=True)

            # Convert to 16-bit PCM
            audio_int16 = (audio * 32768).astype(np.int16)

            # Frame size in samples
            frame_samples = int(self.sample_rate * frame_duration / 1000)

            # Detect voice frames
            voice_frames = []
            for i in range(0, len(audio_int16) - frame_samples, frame_samples):
                frame = audio_int16[i:i + frame_samples]

                # Convert to bytes
                frame_bytes = struct.pack("%dh" % len(frame), *frame)

                # Check if frame contains speech
                try:
                    is_speech = self.vad.is_speech(frame_bytes, self.sample_rate)
                    voice_frames.append((i / self.sample_rate, is_speech))
                except Exception:
                    continue

            # Merge consecutive voice frames into segments
            segments = self._merge_voice_segments(voice_frames, min_duration=0.5)

            logger.info(f"Found {len(segments)} voice segments")
            return segments

        except Exception as e:
            logger.error(f"Error detecting voice activity: {str(e)}")
            raise

    def _merge_voice_segments(self, voice_frames: List[Tuple[float, bool]],
                             min_duration: float = 0.5,
                             max_gap: float = 0.3) -> List[Tuple[float, float]]:
        """
        Merge consecutive voice frames into segments

        Args:
            voice_frames: List of (timestamp, is_speech) tuples
            min_duration: Minimum segment duration in seconds
            max_gap: Maximum gap between segments to merge

        Returns:
            List of (start_time, end_time) tuples
        """
        if not voice_frames:
            return []

        segments = []
        start_time = None

        for i, (timestamp, is_speech) in enumerate(voice_frames):
            if is_speech and start_time is None:
                start_time = timestamp
            elif not is_speech and start_time is not None:
                # Check if we should end the segment
                if i < len(voice_frames) - 1:
                    next_speech_idx = self._find_next_speech(voice_frames, i)
                    if next_speech_idx is not None:
                        gap = voice_frames[next_speech_idx][0] - timestamp
                        if gap <= max_gap:
                            continue  # Don't end segment yet

                # End segment
                duration = timestamp - start_time
                if duration >= min_duration:
                    segments.append((start_time, timestamp))
                start_time = None

        # Handle last segment
        if start_time is not None:
            end_time = voice_frames[-1][0]
            if end_time - start_time >= min_duration:
                segments.append((start_time, end_time))

        return segments

    def _find_next_speech(self, voice_frames: List[Tuple[float, bool]],
                         start_idx: int) -> int:
        """Find index of next speech frame"""
        for i in range(start_idx, len(voice_frames)):
            if voice_frames[i][1]:
                return i
        return None

    def assess_quality(self, audio_files: List[str]) -> Dict:
        """
        Assess quality of audio data

        Args:
            audio_files: List of audio file paths

        Returns:
            Dictionary with quality metrics
        """
        try:
            logger.info(f"Assessing quality of {len(audio_files)} audio files")

            total_duration = 0
            total_speech_duration = 0
            snr_values = []
            quality_scores = []

            for audio_path in audio_files:
                # Load audio
                audio, sr = librosa.load(audio_path, sr=self.sample_rate, mono=True)

                # Get duration
                duration = len(audio) / sr
                total_duration += duration

                # Detect voice segments
                voice_segments = self.detect_voice_activity(audio_path)
                speech_duration = sum(end - start for start, end in voice_segments)
                total_speech_duration += speech_duration

                # Calculate SNR
                snr = self._calculate_snr(audio)
                snr_values.append(snr)

                # Calculate quality score
                quality = self._calculate_quality_score(audio, sr, voice_segments)
                quality_scores.append(quality)

            # Aggregate metrics
            avg_snr = np.mean(snr_values) if snr_values else 0
            avg_quality = np.mean(quality_scores) if quality_scores else 0

            metrics = {
                'total_duration': total_duration,
                'speech_duration': total_speech_duration,
                'speech_ratio': total_speech_duration / total_duration if total_duration > 0 else 0,
                'average_snr': avg_snr,
                'average_quality': avg_quality,
                'num_files': len(audio_files),
                'sufficient_data': total_speech_duration >= 10.0,  # At least 10 seconds
                'quality_level': self._interpret_quality(avg_quality)
            }

            logger.info(f"Quality assessment: {metrics['quality_level']}")
            return metrics

        except Exception as e:
            logger.error(f"Error assessing quality: {str(e)}")
            raise

    def _calculate_snr(self, audio: np.ndarray) -> float:
        """
        Calculate Signal-to-Noise Ratio

        Args:
            audio: Audio data

        Returns:
            SNR in dB
        """
        try:
            # Calculate signal power
            signal_power = np.mean(audio ** 2)

            # Estimate noise power (use quietest 10% of frames)
            frame_size = int(0.1 * self.sample_rate)
            frame_powers = []

            for i in range(0, len(audio) - frame_size, frame_size):
                frame = audio[i:i + frame_size]
                power = np.mean(frame ** 2)
                frame_powers.append(power)

            if frame_powers:
                noise_power = np.percentile(frame_powers, 10)

                # Calculate SNR
                if noise_power > 0:
                    snr = 10 * np.log10(signal_power / noise_power)
                else:
                    snr = 100  # Very high SNR if no noise detected

                return snr
            else:
                return 0

        except Exception as e:
            logger.error(f"Error calculating SNR: {str(e)}")
            return 0

    def _calculate_quality_score(self, audio: np.ndarray, sr: int,
                                 voice_segments: List[Tuple[float, float]]) -> float:
        """
        Calculate overall quality score (0-1)

        Args:
            audio: Audio data
            sr: Sample rate
            voice_segments: List of voice segments

        Returns:
            Quality score between 0 and 1
        """
        try:
            scores = []

            # SNR score
            snr = self._calculate_snr(audio)
            snr_score = np.clip(snr / 30, 0, 1)  # Normalize to 0-1
            scores.append(snr_score)

            # Speech ratio score
            duration = len(audio) / sr
            speech_duration = sum(end - start for start, end in voice_segments)
            speech_ratio = speech_duration / duration if duration > 0 else 0
            speech_score = np.clip(speech_ratio, 0, 1)
            scores.append(speech_score)

            # Amplitude consistency score
            frame_size = int(0.1 * sr)
            frame_amplitudes = []

            for i in range(0, len(audio) - frame_size, frame_size):
                frame = audio[i:i + frame_size]
                amplitude = np.sqrt(np.mean(frame ** 2))
                frame_amplitudes.append(amplitude)

            if frame_amplitudes:
                amplitude_std = np.std(frame_amplitudes)
                amplitude_mean = np.mean(frame_amplitudes)
                consistency_score = 1 - np.clip(amplitude_std / (amplitude_mean + 1e-6), 0, 1)
                scores.append(consistency_score)

            # Overall quality score
            quality = np.mean(scores)
            return quality

        except Exception as e:
            logger.error(f"Error calculating quality score: {str(e)}")
            return 0.5

    def _interpret_quality(self, quality_score: float) -> str:
        """Interpret quality score"""
        if quality_score >= 0.8:
            return "excellent"
        elif quality_score >= 0.6:
            return "good"
        elif quality_score >= 0.4:
            return "fair"
        else:
            return "poor"

    def detect_voice_segments_energy(self, audio_path: str,
                                    energy_threshold: float = 0.02) -> List[Tuple[float, float]]:
        """
        Detect voice segments using energy-based method (fallback)

        Args:
            audio_path: Path to audio file
            energy_threshold: Energy threshold for voice detection

        Returns:
            List of (start_time, end_time) tuples
        """
        try:
            # Load audio
            audio, sr = librosa.load(audio_path, sr=self.sample_rate, mono=True)

            # Calculate energy
            frame_length = int(0.025 * sr)  # 25ms frames
            hop_length = int(0.010 * sr)    # 10ms hop

            energy = librosa.feature.rms(
                y=audio,
                frame_length=frame_length,
                hop_length=hop_length
            )[0]

            # Detect voice frames
            voice_frames = energy > energy_threshold

            # Convert to time segments
            segments = []
            start_frame = None

            for i, is_voice in enumerate(voice_frames):
                if is_voice and start_frame is None:
                    start_frame = i
                elif not is_voice and start_frame is not None:
                    start_time = start_frame * hop_length / sr
                    end_time = i * hop_length / sr
                    if end_time - start_time >= 0.5:  # Min 0.5 seconds
                        segments.append((start_time, end_time))
                    start_frame = None

            # Handle last segment
            if start_frame is not None:
                start_time = start_frame * hop_length / sr
                end_time = len(voice_frames) * hop_length / sr
                if end_time - start_time >= 0.5:
                    segments.append((start_time, end_time))

            logger.info(f"Energy-based detection found {len(segments)} segments")
            return segments

        except Exception as e:
            logger.error(f"Error in energy-based detection: {str(e)}")
            raise

    def extract_voice_segments(self, audio_path: str, output_dir: str = None) -> List[str]:
        """
        Extract voice segments and save as separate files

        Args:
            audio_path: Path to audio file
            output_dir: Output directory for segments

        Returns:
            List of paths to extracted segments
        """
        try:
            from pathlib import Path
            import soundfile as sf

            if output_dir is None:
                output_dir = Path(audio_path).parent / "segments"
            else:
                output_dir = Path(output_dir)

            output_dir.mkdir(parents=True, exist_ok=True)

            # Load audio
            audio, sr = librosa.load(audio_path, sr=self.sample_rate, mono=True)

            # Detect voice segments
            segments = self.detect_voice_activity(audio_path)

            # Extract and save segments
            segment_files = []
            base_name = Path(audio_path).stem

            for i, (start_time, end_time) in enumerate(segments):
                start_sample = int(start_time * sr)
                end_sample = int(end_time * sr)

                segment = audio[start_sample:end_sample]

                output_path = output_dir / f"{base_name}_segment_{i:03d}.wav"
                sf.write(str(output_path), segment, sr)

                segment_files.append(str(output_path))

            logger.info(f"Extracted {len(segment_files)} voice segments")
            return segment_files

        except Exception as e:
            logger.error(f"Error extracting voice segments: {str(e)}")
            raise
