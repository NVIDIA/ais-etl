"""
Benchmark script for transforming audio files using FFmpeg based on [NeMo's Speech Data Processor](https://github.com/NVIDIA/NeMo-speech-data-processor).

This script:
- Reads an audio file.
- Converts it to a WAV file with specified parameters.
- Saves the transformed file.
- Runs the process multiple times for benchmarking.

Dependencies:
- FFmpeg must be installed and accessible in the system PATH.

Usage:
    `python benchmark_audio.py <input_audio> <output_dir> <num_iterations>`

    Note: to time the script, use the following command:
    `time python benchmark_audio.py <input_audio> <output_dir> <num_iterations>`
"""

import subprocess
import wave
import io
import os
import sys

# Default audio processing parameters
AC = 1  # Number of audio channels
AR = 44100  # Audio sample rate


def transform(input_bytes: bytes, ac: int = AC, ar: int = AR) -> bytes:
    """
    Converts raw audio input to a WAV file with specified audio channels and sample rate.

    Args:
        input_bytes (bytes): The raw input audio data.
        ac (int, optional): Number of audio channels. Defaults to AC (1).
        ar (int, optional): Audio sample rate. Defaults to AR (44100).

    Returns:
        bytes: Processed WAV file in memory.

    Raises:
        RuntimeError: If FFmpeg processing fails.
    """

    process_args = [
        "ffmpeg",
        "-nostdin",
        "-loglevel",
        "error",
        "-i",
        "pipe:0",
        "-map",
        "0:a",
        "-ac",
        str(ac),
        "-ar",
        str(ar),
        "-c:a",
        "pcm_s16le",
        "-f",
        "s16le",  # Output raw PCM data
        "-y",
        "pipe:1",
    ]

    try:
        process = subprocess.Popen(
            process_args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        raw_audio_data, stderr = process.communicate(input=input_bytes)

        if process.returncode != 0:
            raise RuntimeError(f"FFmpeg process failed: {stderr.decode()}")

    except FileNotFoundError:
        raise RuntimeError("FFmpeg is not installed or not found in PATH.")

    # Create a WAV file in memory
    with io.BytesIO() as wav_io:
        with wave.open(wav_io, "wb") as wav_file:
            wav_file.setnchannels(ac)
            wav_file.setsampwidth(2)  # 16-bit audio
            wav_file.setframerate(ar)
            wav_file.writeframes(raw_audio_data)
        return wav_io.getvalue()


def process_audio_file(input_filepath: str, output_filepath: str):
    """
    Reads an input audio file, converts it to WAV format, and saves it.

    Args:
        input_filepath (str): Path to the input audio file.
        output_filepath (str): Path where the converted WAV file should be saved.
    """

    if not os.path.exists(input_filepath):
        raise FileNotFoundError(f"Input file not found: {input_filepath}")

    with open(input_filepath, "rb") as input_file:
        input_bytes = input_file.read()

    wav_bytes = transform(input_bytes)

    os.makedirs(os.path.dirname(output_filepath), exist_ok=True)

    with open(output_filepath, "wb") as output_file:
        output_file.write(wav_bytes)

    print(f"Processed: {output_filepath}")


def main():
    """
    Main function to process an audio file multiple times for benchmarking.

    Args:
        sys.argv[1] (str): Path to the input audio file.
        sys.argv[2] (str): Output directory for transformed files.
        sys.argv[3] (int, optional): Number of iterations (default: 300).
    """

    if len(sys.argv) < 3:
        print(
            "Usage: python benchmark_audio.py <input_audio> <output_dir> [num_iterations]"
        )
        sys.exit(1)

    input_file = sys.argv[1]
    output_dir = sys.argv[2]
    num_iterations = int(sys.argv[3]) if len(sys.argv) > 3 else 300

    for i in range(num_iterations):
        output_file = os.path.join(output_dir, f"output_audio{i}.wav")
        process_audio_file(input_file, output_file)


if __name__ == "__main__":
    main()
