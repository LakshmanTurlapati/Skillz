---
name: speak
description: Convert an assistant response into concise, natural spoken audio with ElevenLabs Multilingual v2 and play it automatically. Use only when the user explicitly asks to "speak," "say it aloud," "read it aloud," "voice it," or invokes $speak; do not trigger for ordinary written responses or general discussion about speech or ElevenLabs.
---

# Speak

Create a short, listener-friendly narration from the answer, synthesize it with ElevenLabs, save the MP3, and start playback on the user's Mac.

## Workflow

1. Finish the underlying task and prepare the accurate written answer first.
2. Rewrite that answer as self-contained spoken prose:
   - Summarize long material while preserving conclusions, important numbers, decisions, warnings, and next actions.
   - Use the user's language unless they request another language.
   - Prefer short sentences and natural transitions.
   - Remove Markdown syntax, tables, citations, raw URLs, code blocks, and repetitive detail unless they are essential to understand the answer.
   - Expand symbols, abbreviations, file paths, and commands into pronounceable wording when they must be included.
   - Never read credentials, tokens, or other secrets aloud.
3. Keep routine narration around 30 to 90 seconds. Follow an explicit user request for a different length or for verbatim reading.
4. Put only the narration in a UTF-8 text file under the current workspace's `.context/speak/` directory. Use a file-editing tool; do not interpolate arbitrary narration into a shell command.
5. Run:

   ```bash
   python3 <skill-directory>/scripts/speak.py --input <narration-file>
   ```

   Replace `<skill-directory>` with the directory containing this `SKILL.md`. The script uses the configured voice, calls ElevenLabs with `eleven_multilingual_v2`, saves an MP3, and starts `afplay` automatically.
6. Return the normal written answer and briefly confirm that playback started. Include the generated audio path reported by the script.

## Behavior and failures

- Treat synthesis as an external, potentially billable action. Call it exactly once per explicit speaking request unless the user asks for another rendition.
- Use the already-prepared narration as the API input; do not send unrelated workspace content.
- If neither `ELEVENLABS_API_KEY` nor the macOS Keychain entry is available, stop before synthesis and ask the user for an ElevenLabs API key and, optionally, a preferred ElevenLabs voice ID. Never echo, narrate, save, or commit the API key. Use a supplied voice ID for that request; otherwise keep the configured default.
- If synthesis or playback fails, preserve the written answer and report the concise error. Do not retry repeatedly.
- Let `ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID`, or `ELEVENLABS_MODEL_ID` override the defaults when present. Otherwise, the script reads the API key from the macOS Keychain and uses its configured voice and Multilingual v2.
- On a non-Mac environment, generate the audio when credentials are available and report that automatic `afplay` playback is unavailable.
