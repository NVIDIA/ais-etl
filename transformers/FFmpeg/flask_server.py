"""
FFmpeg ETL Transformer (FlaskServer)

FlaskServer-based ETL that normalizes/encodes audio via FFmpeg.
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

from aistore.sdk.etl.webserver.flask_server import FlaskServer

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


class FFmpegServer(FlaskServer):
    """Flask-based server for FFmpeg audio transformation."""

    def __init__(self, host: str = "0.0.0.0", port: int = 8000):
        super().__init__(host=host, port=port)
        # Read env and build ffmpeg command parts (prefix + suffix).
        # At transform time, the input source is slotted between them.
        channels = os.getenv("AC")
        samplerate = os.getenv("AR")
        bitrate = os.getenv("BR")
        codec = os.getenv("CODEC", "pcm_s16le")
        audio_filters = os.getenv("AUDIO_FILTERS")
        self.out_format = os.getenv("FORMAT", "wav")

        self._cmd_prefix = ["ffmpeg", "-nostdin", "-loglevel", "error", "-i"]
        self._cmd_suffix = []
        if channels:
            self._cmd_suffix += ["-ac", channels]
        if samplerate:
            self._cmd_suffix += ["-ar", samplerate]
        self._cmd_suffix += ["-c:a", codec]
        if audio_filters:
            self._cmd_suffix += ["-af", audio_filters]
        if bitrate:
            self._cmd_suffix += ["-b:a", bitrate]
        self._cmd_suffix += ["-f", self.out_format, "pipe:1"]

    def transform(self, data, path: str, _etl_args: str) -> bytes:
        """
        Transform input audio using FFmpeg. If the path extension doesn't look
        like audio, pass the data through unchanged.

        When ETL_DIRECT_FQN=true, `data` is a str (file path) and ffmpeg reads
        the file directly — avoiding loading the entire file into memory.
        Otherwise `data` is bytes piped through stdin.
        """
        ext = os.path.splitext(path or "")[1].lower()
        if ext and ext not in _AUDIO_EXTS:
            if isinstance(data, str):
                with open(data, "rb") as f:
                    return f.read()
            return data

        # Build command: file path (FQN) or pipe:0 (bytes)
        if isinstance(data, str):
            cmd = self._cmd_prefix + [data] + self._cmd_suffix
            stdin, input_data = subprocess.DEVNULL, None
        else:
            cmd = self._cmd_prefix + ["pipe:0"] + self._cmd_suffix
            stdin, input_data = subprocess.PIPE, data

        with subprocess.Popen(
            cmd, stdin=stdin, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        ) as proc:
            out, err = proc.communicate(input=input_data)
        if proc.returncode != 0:
            msg = err.decode("utf-8", errors="ignore").strip()
            self.logger.error("FFmpeg error: %s", msg)
            raise RuntimeError(f"FFmpeg process failed: {msg}")
        return out

    def get_mime_type(self) -> str:
        """Return MIME type based on configured output format."""
        return _MIME_BY_FORMAT.get(self.out_format.lower(), "application/octet-stream")


flask_server = FFmpegServer(port=8000)
flask_app = flask_server.app
