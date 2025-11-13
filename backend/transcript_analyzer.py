"""
Transcript analysis component for identifying speaker timestamps
"""
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
from typing import List, Dict, Tuple, Optional
import re
import logging
from urllib.parse import urlparse, parse_qs

logger = logging.getLogger(__name__)

class TranscriptAnalyzer:
    """Analyze video transcripts to identify speaker timestamps"""

    def __init__(self):
        self.formatter = TextFormatter()

    def get_transcript(self, video_url: str, languages: List[str] = None) -> Optional[List[Dict]]:
        """
        Get transcript from YouTube video

        Args:
            video_url: YouTube video URL
            languages: List of language codes to try (default: ['en', 'ru'])

        Returns:
            List of transcript entries with timestamps or None if not available
        """
        try:
            if languages is None:
                languages = ['en', 'ru']

            video_id = self._extract_video_id(video_url)
            if not video_id:
                logger.error(f"Could not extract video ID from {video_url}")
                return None

            logger.info(f"Getting transcript for video {video_id}")

            # Try to get transcript
            try:
                transcript = YouTubeTranscriptApi.get_transcript(
                    video_id,
                    languages=languages
                )
                logger.info(f"Found transcript with {len(transcript)} entries")
                return transcript

            except Exception as e:
                logger.warning(f"Could not get manual transcript, trying auto-generated: {str(e)}")

                # Try auto-generated transcript
                try:
                    transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
                    transcript = transcript_list.find_generated_transcript(languages).fetch()
                    logger.info(f"Found auto-generated transcript with {len(transcript)} entries")
                    return transcript
                except Exception as e2:
                    logger.warning(f"Could not get auto-generated transcript: {str(e2)}")
                    return None

        except Exception as e:
            logger.error(f"Error getting transcript: {str(e)}")
            return None

    def _extract_video_id(self, url: str) -> Optional[str]:
        """Extract video ID from YouTube URL"""
        try:
            # Parse URL
            parsed = urlparse(url)

            # Handle different YouTube URL formats
            if parsed.hostname in ['www.youtube.com', 'youtube.com']:
                if parsed.path == '/watch':
                    query = parse_qs(parsed.query)
                    return query.get('v', [None])[0]
                elif parsed.path.startswith('/embed/'):
                    return parsed.path.split('/')[2]
                elif parsed.path.startswith('/v/'):
                    return parsed.path.split('/')[2]

            elif parsed.hostname in ['youtu.be', 'www.youtu.be']:
                return parsed.path[1:]

            return None

        except Exception as e:
            logger.error(f"Error extracting video ID: {str(e)}")
            return None

    def search_speaker_mentions(self, transcript: List[Dict],
                               speaker_name: str) -> List[Tuple[float, float]]:
        """
        Search for mentions of speaker name in transcript

        Args:
            transcript: Transcript entries
            speaker_name: Name to search for

        Returns:
            List of (start_time, end_time) tuples where speaker is mentioned
        """
        try:
            if not transcript:
                return []

            logger.info(f"Searching for mentions of '{speaker_name}'")

            mentions = []
            name_lower = speaker_name.lower()
            name_parts = name_lower.split()

            for entry in transcript:
                text = entry.get('text', '').lower()

                # Check if any part of the name is mentioned
                if any(part in text for part in name_parts if len(part) > 2):
                    start_time = entry.get('start', 0)
                    duration = entry.get('duration', 0)
                    end_time = start_time + duration

                    mentions.append((start_time, end_time))

            logger.info(f"Found {len(mentions)} mentions")
            return mentions

        except Exception as e:
            logger.error(f"Error searching speaker mentions: {str(e)}")
            return []

    def filter_by_speaker(self, transcript: List[Dict],
                         speaker_name: str,
                         voice_segments: List[Tuple[float, float]],
                         context_window: float = 10.0) -> List[Tuple[float, float]]:
        """
        Filter voice segments to only include those likely from target speaker

        Args:
            transcript: Transcript entries
            speaker_name: Target speaker name
            voice_segments: List of detected voice segments
            context_window: Time window (seconds) around mentions to consider

        Returns:
            Filtered list of voice segments
        """
        try:
            logger.info(f"Filtering segments for speaker '{speaker_name}'")

            # Get speaker mentions
            mentions = self.search_speaker_mentions(transcript, speaker_name)

            if not mentions:
                logger.warning("No mentions found, returning all segments")
                return voice_segments

            # Filter segments that are close to mentions
            filtered_segments = []

            for seg_start, seg_end in voice_segments:
                for mention_start, mention_end in mentions:
                    # Check if segment is within context window of mention
                    if (seg_start >= mention_start - context_window and
                        seg_start <= mention_end + context_window):
                        filtered_segments.append((seg_start, seg_end))
                        break

            logger.info(f"Filtered to {len(filtered_segments)} segments")
            return filtered_segments

        except Exception as e:
            logger.error(f"Error filtering by speaker: {str(e)}")
            return voice_segments

    def identify_speaker_segments(self, transcript: List[Dict],
                                 speaker_indicators: List[str] = None) -> Dict[str, List[Tuple[float, float]]]:
        """
        Identify segments for different speakers based on indicators

        Args:
            transcript: Transcript entries
            speaker_indicators: List of patterns that indicate speaker changes

        Returns:
            Dictionary mapping speaker labels to time segments
        """
        try:
            if speaker_indicators is None:
                # Common patterns that indicate speaker changes
                speaker_indicators = [
                    r'^\s*>>\s*',  # >> at start
                    r'^\s*\[.*?\]\s*:',  # [Name]:
                    r'^\s*\w+\s*:',  # Name:
                    r'^\s*-\s+',  # - at start
                ]

            logger.info("Identifying speaker segments")

            segments = {}
            current_speaker = "unknown"
            speaker_times = []

            for entry in transcript:
                text = entry.get('text', '')
                start_time = entry.get('start', 0)
                duration = entry.get('duration', 0)
                end_time = start_time + duration

                # Check for speaker indicator
                new_speaker = None
                for pattern in speaker_indicators:
                    match = re.match(pattern, text)
                    if match:
                        # Extract speaker name if possible
                        speaker_text = text[:50].strip()
                        new_speaker = self._extract_speaker_name(speaker_text)
                        break

                if new_speaker:
                    # Save previous speaker's segments
                    if speaker_times:
                        if current_speaker not in segments:
                            segments[current_speaker] = []
                        segments[current_speaker].extend(speaker_times)

                    # Start new speaker
                    current_speaker = new_speaker
                    speaker_times = [(start_time, end_time)]
                else:
                    # Continue current speaker
                    speaker_times.append((start_time, end_time))

            # Save last speaker's segments
            if speaker_times:
                if current_speaker not in segments:
                    segments[current_speaker] = []
                segments[current_speaker].extend(speaker_times)

            logger.info(f"Identified {len(segments)} speakers")
            return segments

        except Exception as e:
            logger.error(f"Error identifying speaker segments: {str(e)}")
            return {}

    def _extract_speaker_name(self, text: str) -> str:
        """Extract speaker name from text"""
        # Remove common prefixes
        text = re.sub(r'^\s*>>\s*', '', text)
        text = re.sub(r'^\s*-\s+', '', text)

        # Extract name before colon
        match = re.match(r'^\s*\[?(.*?)\]?\s*:', text)
        if match:
            return match.group(1).strip()

        # Return first few words
        words = text.split()[:2]
        return ' '.join(words)

    def get_transcript_text(self, transcript: List[Dict]) -> str:
        """
        Get full transcript as text

        Args:
            transcript: Transcript entries

        Returns:
            Full transcript text
        """
        try:
            if not transcript:
                return ""

            text = ' '.join([entry.get('text', '') for entry in transcript])
            return text

        except Exception as e:
            logger.error(f"Error getting transcript text: {str(e)}")
            return ""

    def find_keywords(self, transcript: List[Dict],
                     keywords: List[str]) -> Dict[str, List[Tuple[float, str]]]:
        """
        Find occurrences of keywords in transcript

        Args:
            transcript: Transcript entries
            keywords: List of keywords to search for

        Returns:
            Dictionary mapping keywords to list of (timestamp, context) tuples
        """
        try:
            logger.info(f"Searching for {len(keywords)} keywords")

            results = {keyword: [] for keyword in keywords}

            for entry in transcript:
                text = entry.get('text', '')
                start_time = entry.get('start', 0)

                text_lower = text.lower()

                for keyword in keywords:
                    if keyword.lower() in text_lower:
                        results[keyword].append((start_time, text))

            # Log results
            for keyword, occurrences in results.items():
                if occurrences:
                    logger.info(f"Found '{keyword}' {len(occurrences)} times")

            return results

        except Exception as e:
            logger.error(f"Error finding keywords: {str(e)}")
            return {keyword: [] for keyword in keywords}

    def summarize_transcript(self, transcript: List[Dict],
                           max_sentences: int = 5) -> str:
        """
        Create a simple summary of transcript

        Args:
            transcript: Transcript entries
            max_sentences: Maximum number of sentences in summary

        Returns:
            Summary text
        """
        try:
            if not transcript:
                return ""

            # Get full text
            text = self.get_transcript_text(transcript)

            # Split into sentences (simple approach)
            sentences = re.split(r'[.!?]+', text)
            sentences = [s.strip() for s in sentences if len(s.strip()) > 20]

            # Take first and last sentences, and some from middle
            if len(sentences) <= max_sentences:
                summary_sentences = sentences
            else:
                # First sentence
                summary_sentences = [sentences[0]]

                # Some from middle
                step = len(sentences) // (max_sentences - 2)
                for i in range(1, max_sentences - 1):
                    idx = min(i * step, len(sentences) - 2)
                    summary_sentences.append(sentences[idx])

                # Last sentence
                summary_sentences.append(sentences[-1])

            summary = '. '.join(summary_sentences) + '.'
            return summary

        except Exception as e:
            logger.error(f"Error summarizing transcript: {str(e)}")
            return ""

    def get_transcript_stats(self, transcript: List[Dict]) -> Dict:
        """
        Get statistics about transcript

        Args:
            transcript: Transcript entries

        Returns:
            Dictionary with statistics
        """
        try:
            if not transcript:
                return {
                    'num_entries': 0,
                    'total_duration': 0,
                    'total_words': 0,
                    'avg_words_per_entry': 0
                }

            num_entries = len(transcript)

            # Calculate total duration
            if transcript:
                last_entry = transcript[-1]
                total_duration = last_entry.get('start', 0) + last_entry.get('duration', 0)
            else:
                total_duration = 0

            # Count words
            total_words = 0
            for entry in transcript:
                text = entry.get('text', '')
                words = len(text.split())
                total_words += words

            avg_words = total_words / num_entries if num_entries > 0 else 0

            stats = {
                'num_entries': num_entries,
                'total_duration': total_duration,
                'total_words': total_words,
                'avg_words_per_entry': avg_words
            }

            return stats

        except Exception as e:
            logger.error(f"Error getting transcript stats: {str(e)}")
            return {}
