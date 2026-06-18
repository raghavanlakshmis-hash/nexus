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
    """
    from anthropic import Anthropic
    from dotenv import load_dotenv
    load_dotenv(override=True)
    client = Anthropic()

    import json

    # Build a type-aware schema so Claude knows exactly what values to return
    schema_lines = []
    for q in questions:
        qtype = q.get("type", "free_text")
        if qtype == "med_checkbox":
            schema_lines.append(
                f'  "{q["id"]}": '
                f'// Did the patient take {q.get("med_name", q["id"])}? '
                f'Return "Yes — I took it" | "No — I missed it" | null'
            )
        elif qtype == "scale_1_10":
            schema_lines.append(
                f'  "{q["id"]}": '
                f'// {q["question"]} Return an integer 1-10. '
                f'Convert words to numbers ("four"→4, "seven"→7). Return null if not mentioned.'
            )
        elif qtype == "number_lbs":
            schema_lines.append(
                f'  "{q["id"]}": '
                f'// {q["question"]} Return a number (lbs) or null.'
            )
        elif qtype == "yes_no_detail":
            schema_lines.append(
                f'  "{q["id"]}": '
                f'// {q["question"]} Return "Yes" | "No" | null. '
                f'Also add "{q["id"]}_detail" key with any detail they gave, or null.'
            )
        else:
            schema_lines.append(
                f'  "{q["id"]}": // {q["question"]} Return the patient\'s answer as a string or null.'
            )

    schema_str = "{\n" + "\n".join(schema_lines) + "\n}"

    prompt = f"""A patient just finished their spoken daily check-in (Day {state.get('recovery_day', 1)}, recovering from {state.get('diagnosis', 'their condition')}).

Their exact words: "{transcript}"

Extract their answers and return ONLY this JSON object — no explanation, no markdown:
{schema_str}

Rules:
- For medications: if they say "I took [med]" → "Yes — I took it". If they say "I missed" or don't mention it at all → null (not "No — I missed it", leave it null so they can confirm).
- For energy/feeling numbers: convert spoken words to integers ("four" → 4, "seven and a half" → 8).
- For yes/no questions: "no symptoms" or "I don't have any" counts as "No".
- Only return "No — I missed it" if they explicitly say they missed or skipped a medication.
- Return null for anything genuinely not mentioned."""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}]
        )

        raw = response.content[0].text.strip()
        # Strip markdown fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        return json.loads(raw)

    except json.JSONDecodeError as e:
        print(f"[STT parse] JSON decode failed: {e} | raw: {raw[:200]}")
        return {"concerns": transcript}
    except Exception as e:
        print(f"[STT parse] Claude call failed: {e}")
        return {"concerns": transcript}