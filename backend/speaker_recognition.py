"""
Speaker recognition and voice comparison component
"""
import torch
import torchaudio
import numpy as np
from speechbrain.pretrained import EncoderClassifier
from typing import List, Dict, Optional
import logging
from pathlib import Path
import json

logger = logging.getLogger(__name__)

class SpeakerRecognition:
    """Speaker recognition and voice comparison using deep learning models"""

    def __init__(self, model_dir: str = "data/models"):
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"Using device: {self.device}")

        self.model = None
        self.sample_rate = 16000

    def _load_model(self):
        """Load pre-trained speaker recognition model"""
        if self.model is None:
            try:
                logger.info("Loading speaker recognition model...")

                # Use SpeechBrain's pre-trained model for speaker recognition
                self.model = EncoderClassifier.from_hparams(
                    source="speechbrain/spkrec-ecapa-voxceleb",
                    savedir=str(self.model_dir / "spkrec-ecapa-voxceleb"),
                    run_opts={"device": str(self.device)}
                )

                logger.info("Model loaded successfully")

            except Exception as e:
                logger.error(f"Error loading model: {str(e)}")
                raise

    def extract_embedding(self, audio_path: str) -> np.ndarray:
        """
        Extract speaker embedding from audio file

        Args:
            audio_path: Path to audio file

        Returns:
            Speaker embedding as numpy array
        """
        try:
            self._load_model()

            logger.info(f"Extracting embedding from {audio_path}")

            # Load audio
            waveform, sr = torchaudio.load(audio_path)

            # Resample if necessary
            if sr != self.sample_rate:
                resampler = torchaudio.transforms.Resample(sr, self.sample_rate)
                waveform = resampler(waveform)

            # Convert to mono if stereo
            if waveform.shape[0] > 1:
                waveform = torch.mean(waveform, dim=0, keepdim=True)

            # Extract embedding
            with torch.no_grad():
                embedding = self.model.encode_batch(waveform)
                embedding = embedding.squeeze().cpu().numpy()

            return embedding

        except Exception as e:
            logger.error(f"Error extracting embedding: {str(e)}")
            raise

    def create_speaker_profile(self, audio_files: List[str],
                              use_segments: bool = True) -> Dict:
        """
        Create speaker profile from multiple audio files

        Args:
            audio_files: List of audio file paths
            use_segments: Whether to extract segments first

        Returns:
            Dictionary containing speaker profile
        """
        try:
            logger.info(f"Creating speaker profile from {len(audio_files)} files")

            embeddings = []

            for audio_path in audio_files:
                if use_segments:
                    # Extract voice segments
                    from voice_analyzer import VoiceAnalyzer
                    analyzer = VoiceAnalyzer()
                    segment_files = analyzer.extract_voice_segments(audio_path)

                    # Get embeddings from segments
                    for segment_file in segment_files:
                        try:
                            embedding = self.extract_embedding(segment_file)
                            embeddings.append(embedding)
                        except Exception as e:
                            logger.warning(f"Failed to extract embedding from segment: {str(e)}")
                            continue
                else:
                    # Get embedding from entire file
                    embedding = self.extract_embedding(audio_path)
                    embeddings.append(embedding)

            if not embeddings:
                raise ValueError("No embeddings could be extracted")

            # Calculate mean embedding (speaker profile)
            embeddings_array = np.array(embeddings)
            mean_embedding = np.mean(embeddings_array, axis=0)
            std_embedding = np.std(embeddings_array, axis=0)

            profile = {
                'mean_embedding': mean_embedding.tolist(),
                'std_embedding': std_embedding.tolist(),
                'num_samples': len(embeddings),
                'num_files': len(audio_files),
                'embedding_dim': len(mean_embedding)
            }

            logger.info(f"Speaker profile created with {len(embeddings)} embeddings")
            return profile

        except Exception as e:
            logger.error(f"Error creating speaker profile: {str(e)}")
            raise

    def compare_speakers(self, profile1: Dict, profile2: Dict) -> float:
        """
        Compare two speaker profiles

        Args:
            profile1: First speaker profile
            profile2: Second speaker profile

        Returns:
            Similarity score (0-1, higher means more similar)
        """
        try:
            logger.info("Comparing speaker profiles")

            # Get mean embeddings
            embedding1 = np.array(profile1['mean_embedding'])
            embedding2 = np.array(profile2['mean_embedding'])

            # Calculate cosine similarity
            similarity = self._cosine_similarity(embedding1, embedding2)

            # Normalize to 0-1 range (cosine similarity is -1 to 1)
            similarity = (similarity + 1) / 2

            logger.info(f"Similarity score: {similarity:.4f}")
            return float(similarity)

        except Exception as e:
            logger.error(f"Error comparing speakers: {str(e)}")
            raise

    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors"""
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0

        similarity = dot_product / (norm1 * norm2)
        return float(similarity)

    def compare_audio_files(self, audio_path1: str, audio_path2: str) -> float:
        """
        Compare two audio files directly

        Args:
            audio_path1: Path to first audio file
            audio_path2: Path to second audio file

        Returns:
            Similarity score (0-1)
        """
        try:
            logger.info(f"Comparing {audio_path1} and {audio_path2}")

            # Extract embeddings
            embedding1 = self.extract_embedding(audio_path1)
            embedding2 = self.extract_embedding(audio_path2)

            # Calculate similarity
            similarity = self._cosine_similarity(embedding1, embedding2)
            similarity = (similarity + 1) / 2

            return float(similarity)

        except Exception as e:
            logger.error(f"Error comparing audio files: {str(e)}")
            raise

    def calculate_confidence(self, similarity_score: float,
                           quality1: Dict, quality2: Dict) -> float:
        """
        Calculate confidence in the comparison result

        Args:
            similarity_score: Similarity score between speakers
            quality1: Quality metrics for first speaker
            quality2: Quality metrics for second speaker

        Returns:
            Confidence score (0-1)
        """
        try:
            # Base confidence from similarity score certainty
            # High or low similarity scores are more confident
            score_confidence = 1 - 2 * abs(similarity_score - 0.5)

            # Quality-based confidence
            q1 = quality1.get('average_quality', 0.5)
            q2 = quality2.get('average_quality', 0.5)
            quality_confidence = (q1 + q2) / 2

            # Data amount confidence
            duration1 = quality1.get('speech_duration', 0)
            duration2 = quality2.get('speech_duration', 0)
            min_duration = min(duration1, duration2)

            # More data = higher confidence (plateau at 30 seconds)
            data_confidence = min(min_duration / 30.0, 1.0)

            # Combined confidence
            confidence = (
                score_confidence * 0.4 +
                quality_confidence * 0.3 +
                data_confidence * 0.3
            )

            return float(confidence)

        except Exception as e:
            logger.error(f"Error calculating confidence: {str(e)}")
            return 0.5

    def save_profile(self, profile: Dict, output_path: str):
        """
        Save speaker profile to file

        Args:
            profile: Speaker profile dictionary
            output_path: Output file path
        """
        try:
            with open(output_path, 'w') as f:
                json.dump(profile, f, indent=2)

            logger.info(f"Profile saved to {output_path}")

        except Exception as e:
            logger.error(f"Error saving profile: {str(e)}")
            raise

    def load_profile(self, profile_path: str) -> Dict:
        """
        Load speaker profile from file

        Args:
            profile_path: Path to profile file

        Returns:
            Speaker profile dictionary
        """
        try:
            with open(profile_path, 'r') as f:
                profile = json.load(f)

            logger.info(f"Profile loaded from {profile_path}")
            return profile

        except Exception as e:
            logger.error(f"Error loading profile: {str(e)}")
            raise

    def batch_compare(self, profile: Dict, audio_files: List[str]) -> List[float]:
        """
        Compare a speaker profile against multiple audio files

        Args:
            profile: Speaker profile
            audio_files: List of audio file paths

        Returns:
            List of similarity scores
        """
        try:
            logger.info(f"Batch comparing against {len(audio_files)} files")

            mean_embedding = np.array(profile['mean_embedding'])
            similarities = []

            for audio_path in audio_files:
                try:
                    embedding = self.extract_embedding(audio_path)
                    similarity = self._cosine_similarity(mean_embedding, embedding)
                    similarity = (similarity + 1) / 2
                    similarities.append(similarity)
                except Exception as e:
                    logger.warning(f"Failed to compare {audio_path}: {str(e)}")
                    similarities.append(0.0)

            return similarities

        except Exception as e:
            logger.error(f"Error in batch comparison: {str(e)}")
            raise

    def identify_speaker(self, audio_path: str, known_profiles: Dict[str, Dict],
                        threshold: float = 0.7) -> Optional[str]:
        """
        Identify speaker from known profiles

        Args:
            audio_path: Path to audio file
            known_profiles: Dictionary of {name: profile}
            threshold: Minimum similarity threshold

        Returns:
            Name of identified speaker or None
        """
        try:
            logger.info(f"Identifying speaker in {audio_path}")

            # Extract embedding
            embedding = self.extract_embedding(audio_path)

            # Compare against all known profiles
            best_match = None
            best_score = 0

            for name, profile in known_profiles.items():
                mean_embedding = np.array(profile['mean_embedding'])
                similarity = self._cosine_similarity(embedding, mean_embedding)
                similarity = (similarity + 1) / 2

                if similarity > best_score:
                    best_score = similarity
                    best_match = name

            # Return match if above threshold
            if best_score >= threshold:
                logger.info(f"Identified as {best_match} (score: {best_score:.4f})")
                return best_match
            else:
                logger.info(f"No match found (best score: {best_score:.4f})")
                return None

        except Exception as e:
            logger.error(f"Error identifying speaker: {str(e)}")
            raise
