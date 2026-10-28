import os
import wave
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import numpy as np

from config import Config

logger = logging.getLogger("crimevision.whisper")


def format_seconds_to_timestamp(seconds: float) -> str:
    """Format float seconds into HH:MM:SS."""
    total_sec = max(0, int(round(seconds)))
    h = total_sec // 3600
    m = (total_sec % 3600) // 60
    s = total_sec % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


class WhisperService:
    """
    Forensic Speech-to-Text & Multilingual Audio Transcription Service.
    Supports English, Hindi, and multilingual speech with timestamped segmentations.
    Includes pure-Python WAV reader when system ffmpeg is unavailable.
    """

    _model = None
    _model_name = None
    _is_fallback = False
    _initialized = False

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or Config.WHISPER_MODEL_NAME
        self._initialize()

    def _initialize(self):
        if WhisperService._initialized:
            return

        try:
            import whisper

            logger.info(f"Loading Whisper model ({self.model_name})...")
            WhisperService._model = whisper.load_model(self.model_name)
            WhisperService._model_name = f"OpenAI Whisper ({self.model_name})"
            WhisperService._is_fallback = False
            WhisperService._initialized = True
            logger.info("Whisper model loaded successfully.")
        except Exception as e:
            logger.warning(
                f"Whisper model could not be loaded ({e}). Audio fallback will be utilized."
            )
            WhisperService._is_fallback = True
            WhisperService._model_name = "Whisper Offline Fallback"
            WhisperService._initialized = True

    def transcribe_audio(
        self,
        audio_path: Path,
        language: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Transcribe audio evidence into timestamped segments and detected language.
        Returns:
            - language (e.g., 'en', 'hi', 'es')
            - full transcript
            - segments: [{start, end, text, confidence}]
            - model_used
        """
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        # Attempt real Whisper inference
        if not WhisperService._is_fallback and WhisperService._model is not None:
            try:
                # First attempt standard transcription
                audio_input: Union[str, np.ndarray] = str(audio_path)

                # If ffmpeg is absent, attempt Python native wav loader for .wav files
                if audio_path.suffix.lower() == ".wav":
                    try:
                        audio_array = self._read_wav_to_16k_mono(audio_path)
                        if audio_array is not None:
                            audio_input = audio_array
                    except Exception as e_wav:
                        logger.debug(f"Direct WAV loader fallback: {e_wav}")

                options = {}
                if language:
                    options["language"] = language

                result = WhisperService._model.transcribe(audio_input, **options)

                detected_lang = result.get("language", "en")
                raw_segments = result.get("segments", [])
                formatted_segments = []

                for s in raw_segments:
                    start_sec = float(s.get("start", 0.0))
                    end_sec = float(s.get("end", 0.0))
                    text = s.get("text", "").strip()
                    # Approximate confidence from avg_logprob
                    logprob = s.get("avg_logprob", -0.5)
                    conf = min(0.99, max(0.40, np.exp(logprob))) if logprob else 0.85

                    formatted_segments.append(
                        {
                            "start": round(start_sec, 2),
                            "end": round(end_sec, 2),
                            "start_str": format_seconds_to_timestamp(start_sec),
                            "end_str": format_seconds_to_timestamp(end_sec),
                            "text": text,
                            "language": detected_lang,
                            "confidence": round(float(conf), 4),
                        }
                    )

                full_text = result.get("text", "").strip()

                return {
                    "language": detected_lang,
                    "transcript": full_text,
                    "segments": formatted_segments,
                    "model_used": WhisperService._model_name,
                    "status": "COMPLETED",
                }
            except Exception as e:
                logger.error(f"Whisper transcription failed: {e}. Activating audio fallback.")

        # Fallback transcription when Whisper model or ffmpeg is not available
        return self._fallback_transcription(audio_path)

    def _read_wav_to_16k_mono(self, wav_path: Path) -> Optional[np.ndarray]:
        """Pure Python 16kHz mono audio loader for WAV files without requiring ffmpeg."""
        try:
            with wave.open(str(wav_path), "rb") as wf:
                n_channels = wf.getnchannels()
                sampwidth = wf.getsampwidth()
                framerate = wf.getframerate()
                n_frames = wf.getnframes()
                raw_bytes = wf.readframes(n_frames)

            # Convert to numpy array
            if sampwidth == 2:
                data = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32) / 32768.0
            elif sampwidth == 4:
                data = np.frombuffer(raw_bytes, dtype=np.int32).astype(np.float32) / 2147483648.0
            elif sampwidth == 1:
                data = (np.frombuffer(raw_bytes, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
            else:
                return None

            # Reshape for multi-channel
            if n_channels > 1:
                data = data.reshape(-1, n_channels).mean(axis=1)

            # Resample to 16000 Hz if needed
            target_sr = 16000
            if framerate != target_sr:
                from scipy import signal
                num_target_samples = int(len(data) * target_sr / framerate)
                data = signal.resample(data, num_target_samples).astype(np.float32)

            return data
        except Exception as e:
            logger.error(f"Error reading WAV: {e}")
            return None

    def _fallback_transcription(self, audio_path: Path) -> Dict[str, Any]:
        """Provides informative fallback metadata and simulated forensic transcript."""
        audio_dur = 0.0
        try:
            if audio_path.suffix.lower() == ".wav":
                with wave.open(str(audio_path), "rb") as wf:
                    frames = wf.getnframes()
                    rate = wf.getframerate()
                    audio_dur = frames / float(rate)
        except Exception:
            pass

        return {
            "language": "en",
            "transcript": "Audio signal recorded and indexed for forensic timeline. Multilingual speech model in standby.",
            "segments": [
                {
                    "start": 0.0,
                    "end": round(audio_dur, 2) if audio_dur > 0 else 5.0,
                    "start_str": "00:00:00",
                    "end_str": format_seconds_to_timestamp(audio_dur if audio_dur > 0 else 5.0),
                    "text": "Audio signal recorded and indexed for forensic timeline. Multilingual speech model in standby.",
                    "language": "en",
                    "confidence": 0.70,
                }
            ],
            "model_used": "Audio Signal Parser (Standby Fallback)",
            "status": "FALLBACK_COMPLETED",
        }
