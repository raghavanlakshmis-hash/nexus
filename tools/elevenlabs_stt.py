import os
import requests
import tempfile

ELEVENLABS_STT_URL = "https://api.elevenlabs.io/v1/speech-to-text"

def transcribe_audio(audio_bytes: bytes, mime_type: str = "audio/wav") -> dict:
    """
    Send audio bytes to ElevenLabs STT API.
    Returns dict with success status and transcript text.

    Args:
        audio_bytes: Raw audio bytes from browser recording
        mime_type: Audio format — "audio/wav" or "audio/webm"

    Returns:
        { "success": bool, "transcript": str | None, "error": str | None }
    """
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        return {
            "success": False,
            "transcript": None,
            "error": "ELEVENLABS_API_KEY not set in environment"
        }

    try:
        # Write audio bytes to a temp file
        suffix = ".wav" if "wav" in mime_type else ".webm"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        with open(tmp_path, "rb") as audio_file:
            response = requests.post(
                ELEVENLABS_STT_URL,
                headers={"xi-api-key": api_key},
                files={"file": (f"checkin{suffix}", audio_file, mime_type)},
                data={"model_id": "scribe_v1"},  # ElevenLabs STT model
                timeout=30
            )

        os.unlink(tmp_path)  # Clean up temp file

        if response.status_code == 200:
            data = response.json()
            transcript = data.get("text", "").strip()

            if not transcript:
                return {
                    "success": False,
                    "transcript": None,
                    "error": "Transcription returned empty. Please try again or type your response."
                }

            return {
                "success": True,
                "transcript": transcript,
                "error": None
            }

        else:
            return {
                "success": False,
                "transcript": None,
                "error": f"ElevenLabs API error {response.status_code}: {response.text[:200]}"
            }

    except requests.Timeout:
        return {
            "success": False,
            "transcript": None,
            "error": "ElevenLabs STT timed out. Please type your response instead."
        }
    except Exception as e:
        return {
            "success": False,
            "transcript": None,
            "error": f"STT failed: {str(e)}"
        }


def parse_transcript_to_responses(transcript: str, questions: list, state: dict) -> dict:
    """
    Use Claude to parse a free-form spoken transcript into
    structured check-in responses matching the question set.

    Args:
        transcript: Raw text from ElevenLabs STT
        questions: List of check-in question dicts from generate_checkin_questions()
        state: Current recovery state (for context)

    Returns:
        Dict of structured responses keyed by question ID
    """
    from anthropic import Anthropic
    client = Anthropic()

    question_summary = "\n".join([
        f"- {q['id']}: {q['question']}" for q in questions
    ])

    system_prompt = """You are parsing a patient's spoken check-in response into structured data.
The patient spoke freely — your job is to extract answers to specific questions from their speech.
Be generous in interpretation. If they mention a symptom, flag it.
Return ONLY valid JSON with one key per question ID.
If the transcript doesn't address a question, set that key to null."""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=500,
            system=system_prompt,
            messages=[{
                "role": "user",
                "content": f"""Patient's spoken check-in (Day {state.get('recovery_day', 1)} of recovery from {state.get('diagnosis', 'unknown')}):

"{transcript}"

Extract answers for these questions:
{question_summary}

Return JSON with these exact keys: {[q['id'] for q in questions]}"""
            }]
        )

        import json
        return json.loads(response.content[0].text)

    except Exception as e:
        # Fallback: return transcript as free_text answer
        return {
            "concerns": transcript,
            "_parse_error": str(e),
            "_raw_transcript": transcript
        }