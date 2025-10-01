"""
FFmpeg ETL Transformer (HTTPMultiThreadedServer)

HTTPMultiThreadedServer-based ETL that normalizes/encodes audio via FFmpeg.
- Reads audio bytes from stdin (pipe:0)
- Applies optional channel/sample-rate/codec/bitrate/format settings
- Writes the transformed audio to stdout (pipe:1)

Env vars (all optional):
  AC      -> channels (e.g., "1", "2")
  AR      -> sample rate (e.g., "16000", "44100")
  BR      -> bitrate (e.g., "128k", "64k")   # lossy codecs only
  CODEC   -> audio codec (e.g., "pcm_s16le", "flac", "libmp3lame", "aac")
  FORMAT  -> container/format (e.g., "wav", "flac", "mp3", "m4a", "opus", "ogg")

Default codec: pcm_s16le
Default format: wav
"""

import os
import subprocess

from aistore.sdk.etl.webserver.http_multi_threaded_server import HTTPMultiThreadedServer


_MIME_BY_FORMAT = {
    "wav": "audio/wav",
    "flac": "audio/flac",
    "mp3": "audio/mpeg",
    "m4a": "audio/mp4",
    "aac": "audio/aac",
    "opus": "audio/opus",
    "ogg": "audio/ogg",
}

_AUDIO_EXTS = {".wav", ".flac", ".mp3", ".m4a", ".aac", ".opus", ".ogg"}


class FFmpegServer(HTTPMultiThreadedServer):
    """FastAPI-based server for FFmpeg audio transformation."""

    def __init__(self, host: str = "0.0.0.0", port: int = 8000):
        super().__init__(host=host, port=port)
        # Read env (do not coerce unless present)
        self.channels = os.getenv("AC")  # "1", "2", ...
        self.samplerate = os.getenv("AR")  # "16000", "44100", ...
        self.bitrate = os.getenv("BR")  # "128k", "64k", ...
        self.codec = os.getenv(
            "CODEC", "pcm_s16le"
        )  # "pcm_s16le", "flac", "libmp3lame", "aac", ...
        self.audio_filters = os.getenv(
            "AUDIO_FILTERS"
        )  # "loudnorm", "silenceremove", "atempo", "volume", ...
        self.format = os.getenv(
            "FORMAT", "wav"
        )  # "wav", "flac", "mp3", "m4a", "opus", "ogg", ...

        # Build ffmpeg command lazily (only include flags that have values)
        self.ffmpeg_cmd = [
            "ffmpeg",
            "-nostdin",
            "-loglevel",
            "error",
            "-i",
            "pipe:0",
        ]
        if self.channels:
            self.ffmpeg_cmd += ["-ac", str(self.channels)]
        if self.samplerate:
            self.ffmpeg_cmd += ["-ar", str(self.samplerate)]

        # Codec default (always include)
        self.ffmpeg_cmd += ["-c:a", self.codec]

        if self.audio_filters:
            self.ffmpeg_cmd += ["-af", self.audio_filters]

        # Bitrate only for lossy codecs (safe to include conditionally)
        if self.bitrate:
            self.ffmpeg_cmd += ["-b:a", self.bitrate]

        # Output format (default wav)
        self.ffmpeg_cmd += ["-f", self.format, "pipe:1"]

    def transform(self, data: bytes, path: str, _etl_args: str) -> bytes:
        """
        Transform input audio using FFmpeg. If the path extension doesn't look
        like audio, pass the bytes through unchanged.
        """
        ext = os.path.splitext(path or "")[1].lower()
        if ext and ext not in _AUDIO_EXTS:
            return data
        with subprocess.Popen(
            self.ffmpeg_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ) as proc:
            out, err = proc.communicate(input=data)
            if proc.returncode != 0:
                msg = err.decode("utf-8", errors="ignore").strip()
                self.logger.error("FFmpeg error: %s", msg)
                raise RuntimeError(f"FFmpeg process failed: {msg}")
            return out

    def get_mime_type(self) -> str:
        """Return MIME type based on configured output format."""
        return _MIME_BY_FORMAT.get(self.format.lower(), "application/octet-stream")


if __name__ == "__main__":
    server = FFmpegServer()
    server.start()
