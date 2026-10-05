"""
Phase 91 — AI Model Lifecycle.

All local model configuration is defined here.
Models are loaded ONCE per warm instance (module-level singletons).
No re-downloads at request time.
No arbitrary version selection at runtime.
"""
import logging
import os
import threading
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

# ── Model specifications ───────────────────────────────────────────────────────

@dataclass(frozen=True)
class ModelSpec:
    name: str
    version: str
    source: str          # huggingface repo or explicit URL
    license: str
    device: str          # "cpu" or "cuda"
    compute_type: str    # e.g. "int8", "float16", "float32"


STT_MODEL = ModelSpec(
    name="faster-whisper-base.en",
    version="base.en",
    source="Systran/faster-whisper-base.en",
    license="MIT",
    device="cpu",
    compute_type="int8",
)

VAD_MODEL = ModelSpec(
    name="silero-vad",
    version="5.1.2",
    source="snakers4/silero-vad",
    license="MIT",
    device="cpu",
    compute_type="float32",
)

# ── Singleton loader ───────────────────────────────────────────────────────────

_stt_model = None
_vad_model = None
_load_lock = threading.Lock()


def _model_cache_dir() -> str:
    return os.environ.get("PRAXIS_MODEL_CACHE_DIR", os.path.expanduser("~/.cache/praxis/models"))


def get_stt_model():
    """Return the WhisperModel singleton. Loads on first call, cached thereafter."""
    global _stt_model
    if _stt_model is not None:
        return _stt_model
    with _load_lock:
        if _stt_model is not None:
            return _stt_model
        try:
            from faster_whisper import WhisperModel
            logger.info("loading_stt_model", extra={"model": STT_MODEL.name, "version": STT_MODEL.version})
            _stt_model = WhisperModel(
                STT_MODEL.version,
                device=STT_MODEL.device,
                compute_type=STT_MODEL.compute_type,
                download_root=_model_cache_dir(),
            )
            logger.info("stt_model_loaded", extra={"model": STT_MODEL.name})
        except Exception as e:
            logger.error("stt_model_load_failed", extra={"error": str(e)})
            raise
    return _stt_model


def get_vad_model():
    """Return the silero-vad model singleton."""
    global _vad_model
    if _vad_model is not None:
        return _vad_model
    with _load_lock:
        if _vad_model is not None:
            return _vad_model
        try:
            import silero_vad
            logger.info("loading_vad_model", extra={"model": VAD_MODEL.name})
            _vad_model = silero_vad.load_silero_vad()
            logger.info("vad_model_loaded", extra={"model": VAD_MODEL.name})
        except Exception as e:
            logger.error("vad_model_load_failed", extra={"error": str(e)})
            raise
    return _vad_model


def warmup_models() -> None:
    """Called once at application startup to load models before serving traffic."""
    logger.info("model_warmup_start")
    try:
        get_stt_model()
        get_vad_model()
        logger.info("model_warmup_complete")
    except Exception as e:
        logger.error("model_warmup_failed", extra={"error": str(e)})


def model_status() -> dict:
    return {
        "stt": {"loaded": _stt_model is not None, "spec": STT_MODEL.name},
        "vad": {"loaded": _vad_model is not None, "spec": VAD_MODEL.name},
    }
