#!/usr/bin/env python3
"""Create ElevenLabs speech from prepared narration and play it on macOS."""

from __future__ import annotations

import argparse
import getpass
import json
import os
import platform
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


DEFAULT_VOICE_ID = "dMWVPH9DSxWOMrrrUso3"
DEFAULT_MODEL_ID = "eleven_multilingual_v2"
DEFAULT_OUTPUT_FORMAT = "mp3_44100_128"
KEYCHAIN_SERVICE = "com.conductor.speak.elevenlabs"
MAX_MULTILINGUAL_V2_CHARS = 10_000


class SpeakError(RuntimeError):
    """A user-actionable speech generation error."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate an ElevenLabs MP3 and start macOS playback."
    )
    parser.add_argument("text", nargs="*", help="Narration text; prefer --input for arbitrary text.")
    parser.add_argument("--input", type=Path, help="UTF-8 narration file, or '-' for stdin.")
    parser.add_argument("--output", type=Path, help="Output MP3 path. Defaults to a cache file.")
    parser.add_argument(
        "--voice-id",
        default=os.environ.get("ELEVENLABS_VOICE_ID", DEFAULT_VOICE_ID),
        help="ElevenLabs voice ID.",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("ELEVENLABS_MODEL_ID", DEFAULT_MODEL_ID),
        help="ElevenLabs text-to-speech model ID.",
    )
    parser.add_argument(
        "--output-format",
        default=DEFAULT_OUTPUT_FORMAT,
        help="ElevenLabs output format.",
    )
    parser.add_argument("--no-play", action="store_true", help="Generate without starting playback.")
    return parser.parse_args()


def read_narration(args: argparse.Namespace) -> str:
    if args.input is not None:
        if str(args.input) == "-":
            narration = sys.stdin.read()
        else:
            try:
                narration = args.input.expanduser().read_text(encoding="utf-8")
            except OSError as exc:
                raise SpeakError(f"Could not read narration file: {exc}") from exc
    elif args.text:
        narration = " ".join(args.text)
    elif not sys.stdin.isatty():
        narration = sys.stdin.read()
    else:
        raise SpeakError("Provide narration text or use --input.")

    narration = narration.strip()
    if not narration:
        raise SpeakError("Narration is empty.")
    if len(narration) > MAX_MULTILINGUAL_V2_CHARS:
        raise SpeakError(
            f"Narration has {len(narration):,} characters; Multilingual v2 allows "
            f"at most {MAX_MULTILINGUAL_V2_CHARS:,}. Summarize or split it first."
        )
    return narration


def keychain_api_key() -> str | None:
    if platform.system() != "Darwin" or not Path("/usr/bin/security").exists():
        return None
    result = subprocess.run(
        [
            "/usr/bin/security",
            "find-generic-password",
            "-a",
            getpass.getuser(),
            "-s",
            KEYCHAIN_SERVICE,
            "-w",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def load_api_key() -> str:
    api_key = os.environ.get("ELEVENLABS_API_KEY", "").strip() or keychain_api_key()
    if not api_key:
        raise SpeakError(
            "No ElevenLabs API key was found in ELEVENLABS_API_KEY or the macOS Keychain "
            f"service {KEYCHAIN_SERVICE}."
        )
    return api_key


def default_output_path() -> Path:
    cache_dir = Path.home() / "Library" / "Caches" / "com.conductor.app" / "speak"
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return cache_dir / f"speak-{timestamp}-{uuid.uuid4().hex[:8]}.mp3"


def api_error_message(payload: bytes, status: int) -> str:
    try:
        data = json.loads(payload.decode("utf-8", errors="replace"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return f"ElevenLabs returned HTTP {status}."

    detail = data.get("detail") if isinstance(data, dict) else None
    if isinstance(detail, dict):
        message = detail.get("message") or detail.get("status")
    elif isinstance(detail, str):
        message = detail
    else:
        message = data.get("message") if isinstance(data, dict) else None
    return str(message or f"ElevenLabs returned HTTP {status}.")


def synthesize(
    narration: str,
    api_key: str,
    voice_id: str,
    model_id: str,
    output_format: str,
) -> bytes:
    query_string = urlencode({"output_format": output_format})
    url = (
        "https://api.elevenlabs.io/v1/text-to-speech/"
        f"{quote(voice_id, safe='')}?{query_string}"
    )
    body = json.dumps({"text": narration, "model_id": model_id}).encode("utf-8")
    request = Request(
        url,
        data=body,
        method="POST",
        headers={
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": api_key,
            "User-Agent": "Conductor-Speak-Skill/1.0",
        },
    )

    try:
        with urlopen(request, timeout=90) as response:
            audio = response.read()
            content_type = response.headers.get_content_type()
    except HTTPError as exc:
        payload = exc.read(16_384)
        raise SpeakError(api_error_message(payload, exc.code)) from exc
    except URLError as exc:
        reason = getattr(exc, "reason", exc)
        raise SpeakError(f"Could not reach ElevenLabs: {reason}") from exc
    except TimeoutError as exc:
        raise SpeakError("The ElevenLabs request timed out.") from exc

    if not audio:
        raise SpeakError("ElevenLabs returned an empty audio response.")
    if content_type == "application/json":
        raise SpeakError(api_error_message(audio, 200))
    return audio


def save_audio(audio: bytes, output: Path) -> Path:
    output = output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    partial = output.with_name(f".{output.name}.{uuid.uuid4().hex}.part")
    try:
        partial.write_bytes(audio)
        partial.replace(output)
    finally:
        partial.unlink(missing_ok=True)
    return output


def start_playback(audio_path: Path) -> bool:
    player = Path("/usr/bin/afplay")
    if platform.system() != "Darwin" or not player.exists():
        return False
    subprocess.Popen(
        [str(player), str(audio_path)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
        close_fds=True,
    )
    return True


def main() -> int:
    args = parse_args()
    try:
        narration = read_narration(args)
        audio = synthesize(
            narration=narration,
            api_key=load_api_key(),
            voice_id=args.voice_id,
            model_id=args.model,
            output_format=args.output_format,
        )
        audio_path = save_audio(audio, args.output or default_output_path())
        playback_started = False if args.no_play else start_playback(audio_path)
    except SpeakError as exc:
        print(f"speak: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"speak: Local file or playback error: {exc}", file=sys.stderr)
        return 1

    print(f"Audio saved: {audio_path}")
    if args.no_play:
        print("Playback skipped.")
    elif playback_started:
        print("Playback started.")
    else:
        print("Playback unavailable on this system; the audio file was not played.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
