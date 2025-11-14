"""
Main FastAPI application for voice comparison service
"""

import logging

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, HttpUrl

from .audio_processor import AudioProcessor
from .speaker_recognition import SpeakerRecognition
from .transcript_analyzer import TranscriptAnalyzer
from .voice_analyzer import VoiceAnalyzer
from .youtube_downloader import YouTubeDownloader

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Voice Speaker Recognition Service",
    description="Service for comparing speaker voices from YouTube videos",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize components
youtube_dl = YouTubeDownloader()
audio_processor = AudioProcessor()
voice_analyzer = VoiceAnalyzer()
speaker_recognition = SpeakerRecognition()
transcript_analyzer = TranscriptAnalyzer()


# Data models
class VideoRequest(BaseModel):
    urls: list[HttpUrl]
    target_speaker: str | None = None
    use_transcripts: bool = True


class PlaylistRequest(BaseModel):
    playlist_url: HttpUrl
    target_speaker: str | None = None
    use_transcripts: bool = True


class ComparisonRequest(BaseModel):
    video1_urls: list[HttpUrl]
    video2_urls: list[HttpUrl]
    target_speaker1: str | None = None
    target_speaker2: str | None = None
    use_transcripts: bool = True


class JobStatus(BaseModel):
    job_id: str
    status: str
    progress: float
    message: str
    result: dict | None = None


# In-memory job storage (in production use Redis or DB)
jobs = {}


@app.get("/")
async def root():
    """Root endpoint"""
    return {"service": "Voice Speaker Recognition Service", "version": "1.0.0", "status": "running"}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.post("/api/download-video")
async def download_video(request: VideoRequest, background_tasks: BackgroundTasks):
    """Download video(s) from YouTube and extract audio"""
    try:
        job_id = f"job_{len(jobs) + 1}"
        jobs[job_id] = {
            "status": "processing",
            "progress": 0.0,
            "message": "Starting download...",
            "result": None,
        }

        logger.info(f"Starting job {job_id} for URLs: {request.urls}")

        # Process in background
        background_tasks.add_task(
            process_videos,
            job_id,
            [str(url) for url in request.urls],
            request.target_speaker,
            request.use_transcripts,
        )

        return {"job_id": job_id, "message": "Processing started"}

    except Exception as e:
        logger.error(f"Error in download_video: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/download-playlist")
async def download_playlist(request: PlaylistRequest, background_tasks: BackgroundTasks):
    """Download entire playlist from YouTube"""
    try:
        job_id = f"job_{len(jobs) + 1}"
        jobs[job_id] = {
            "status": "processing",
            "progress": 0.0,
            "message": "Getting playlist info...",
            "result": None,
        }

        logger.info(f"Starting job {job_id} for playlist: {request.playlist_url}")

        # Get video URLs from playlist
        video_urls = youtube_dl.get_playlist_videos(str(request.playlist_url))

        # Process in background
        background_tasks.add_task(
            process_videos, job_id, video_urls, request.target_speaker, request.use_transcripts
        )

        return {"job_id": job_id, "message": f"Processing started for {len(video_urls)} videos"}

    except Exception as e:
        logger.error(f"Error in download_playlist: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/compare-speakers")
async def compare_speakers(request: ComparisonRequest, background_tasks: BackgroundTasks):
    """Compare speakers from two sets of videos"""
    try:
        job_id = f"job_{len(jobs) + 1}"
        jobs[job_id] = {
            "status": "processing",
            "progress": 0.0,
            "message": "Starting comparison...",
            "result": None,
        }

        logger.info(f"Starting comparison job {job_id}")

        # Process in background
        background_tasks.add_task(
            compare_speaker_voices,
            job_id,
            [str(url) for url in request.video1_urls],
            [str(url) for url in request.video2_urls],
            request.target_speaker1,
            request.target_speaker2,
            request.use_transcripts,
        )

        return {"job_id": job_id, "message": "Comparison started"}

    except Exception as e:
        logger.error(f"Error in compare_speakers: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/job/{job_id}")
async def get_job_status(job_id: str):
    """Get status of a processing job"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    return jobs[job_id]


@app.delete("/api/job/{job_id}")
async def cancel_job(job_id: str):
    """Cancel a processing job"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    jobs[job_id]["status"] = "cancelled"
    return {"message": "Job cancelled"}


# Background task functions
async def process_videos(
    job_id: str, video_urls: list[str], target_speaker: str | None, use_transcripts: bool
):
    """Process videos in background"""
    try:
        total_steps = len(video_urls) * 4  # download, extract, analyze, recognize
        current_step = 0

        all_audio_files = []
        all_transcripts = []

        for i, url in enumerate(video_urls):
            # Update progress
            jobs[job_id]["message"] = f"Processing video {i + 1}/{len(video_urls)}"

            # Download video
            video_path = youtube_dl.download_video(url)
            current_step += 1
            jobs[job_id]["progress"] = current_step / total_steps

            # Extract audio
            audio_path = audio_processor.extract_audio(video_path)
            all_audio_files.append(audio_path)
            current_step += 1
            jobs[job_id]["progress"] = current_step / total_steps

            # Get transcript if needed
            if use_transcripts:
                transcript = transcript_analyzer.get_transcript(url)
                all_transcripts.append(transcript)

            # Analyze voice
            voice_segments = voice_analyzer.detect_voice_activity(audio_path)
            current_step += 1
            jobs[job_id]["progress"] = current_step / total_steps

            # Filter by target speaker if specified
            if target_speaker and use_transcripts and transcript:
                _ = transcript_analyzer.filter_by_speaker(
                    transcript, target_speaker, voice_segments
                )

            current_step += 1
            jobs[job_id]["progress"] = current_step / total_steps

        # Create speaker profile
        jobs[job_id]["message"] = "Creating speaker profile..."
        speaker_profile = speaker_recognition.create_speaker_profile(all_audio_files)

        # Analyze quality
        quality_metrics = voice_analyzer.assess_quality(all_audio_files)

        # Store result
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["progress"] = 1.0
        jobs[job_id]["message"] = "Processing completed"
        jobs[job_id]["result"] = {
            "speaker_profile": speaker_profile,
            "quality_metrics": quality_metrics,
            "videos_processed": len(video_urls),
            "audio_files": all_audio_files,
        }

    except Exception as e:
        logger.error(f"Error processing videos in job {job_id}: {str(e)}")
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["message"] = f"Error: {str(e)}"


async def compare_speaker_voices(
    job_id: str,
    video_urls_1: list[str],
    video_urls_2: list[str],
    target_speaker1: str | None,
    target_speaker2: str | None,
    use_transcripts: bool,
):
    """Compare speakers from two sets of videos"""
    try:
        # Process first set of videos
        jobs[job_id]["message"] = "Processing first speaker..."
        jobs[job_id]["progress"] = 0.1

        audio_files_1 = []
        for url in video_urls_1:
            video_path = youtube_dl.download_video(url)
            audio_path = audio_processor.extract_audio(video_path)
            audio_files_1.append(audio_path)

        profile_1 = speaker_recognition.create_speaker_profile(audio_files_1)

        # Process second set of videos
        jobs[job_id]["message"] = "Processing second speaker..."
        jobs[job_id]["progress"] = 0.5

        audio_files_2 = []
        for url in video_urls_2:
            video_path = youtube_dl.download_video(url)
            audio_path = audio_processor.extract_audio(video_path)
            audio_files_2.append(audio_path)

        profile_2 = speaker_recognition.create_speaker_profile(audio_files_2)

        # Compare profiles
        jobs[job_id]["message"] = "Comparing speakers..."
        jobs[job_id]["progress"] = 0.8

        similarity_score = speaker_recognition.compare_speakers(profile_1, profile_2)

        # Assess quality
        quality_1 = voice_analyzer.assess_quality(audio_files_1)
        quality_2 = voice_analyzer.assess_quality(audio_files_2)

        # Store result
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["progress"] = 1.0
        jobs[job_id]["message"] = "Comparison completed"
        jobs[job_id]["result"] = {
            "similarity_score": similarity_score,
            "confidence": speaker_recognition.calculate_confidence(
                similarity_score, quality_1, quality_2
            ),
            "same_person_probability": similarity_score,
            "quality_speaker1": quality_1,
            "quality_speaker2": quality_2,
            "interpretation": interpret_similarity(similarity_score),
        }

    except Exception as e:
        logger.error(f"Error comparing speakers in job {job_id}: {str(e)}")
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["message"] = f"Error: {str(e)}"


def interpret_similarity(score: float) -> str:
    """Interpret similarity score"""
    if score >= 0.9:
        return "Very high probability - likely the same person"
    elif score >= 0.75:
        return "High probability - probably the same person"
    elif score >= 0.6:
        return "Moderate probability - might be the same person"
    elif score >= 0.4:
        return "Low probability - likely different people"
    else:
        return "Very low probability - almost certainly different people"


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
