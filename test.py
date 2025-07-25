import torch
from TTS.api import TTS
import numpy as np
import pyaudio
import sys  # For exiting gracefully
from scipy.io.wavfile import write as write_wav
import scipy.signal
import io
import base64

# --- Configuration ---
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {device}")

TTS_MODEL_NAME = "tts_models/multilingual/multi-dataset/xtts_v2"

# --- FIX FOR PYTORCH 2.6+ WEIGHTS_ONLY ERROR ---
# Import all required classes from Coqui TTS
from TTS.config.shared_configs import BaseDatasetConfig
from TTS.tts.configs.xtts_config import XttsConfig
from TTS.tts.models.xtts import XttsAudioConfig, XttsArgs

try:
    torch.serialization.add_safe_globals([
        BaseDatasetConfig,
        XttsConfig,
        XttsAudioConfig,
        XttsArgs
    ])
    print("Added Coqui TTS custom classes to PyTorch's safe globals for loading.")
except AttributeError:
    print("Warning: torch.serialization.add_safe_globals not available. "
          "You might be on an older PyTorch version.")

# --- Initialize TTS Model ---
try:
    print(f"Loading TTS model: {TTS_MODEL_NAME}...")
    tts = TTS(model_name=TTS_MODEL_NAME, progress_bar=True).to(device)
    print("TTS model loaded successfully.")

    sample_rate = tts.synthesizer.output_sample_rate
    print(f"Model output sample rate: {sample_rate} Hz")

except Exception as e:
    print(f"\nError loading TTS model: {e}", file=sys.stderr)
    print("Please ensure your internet connection is stable and the model name is correct.", file=sys.stderr)
    print("You can list available models with `tts --list_models` in your terminal.", file=sys.stderr)
    print("If using XTTS v2, ensure you have enough RAM/VRAM as it's a large model.", file=sys.stderr)
    sys.exit(1)

# --- Setup PyAudio for Real-time Playback ---
try:
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paFloat32,
                    channels=1,
                    rate=sample_rate,
                    output=True)
    print("PyAudio stream opened.")
except Exception as e:
    print(f"\nError initializing PyAudio: {e}", file=sys.stderr)
    print("Please ensure PyAudio is correctly installed (`pip install pyaudio`).", file=sys.stderr)
    print("On some systems, you might need PortAudio development libraries (e.g., `sudo apt-get install portaudio19-dev` on Debian/Ubuntu, `brew install portaudio` on macOS).", file=sys.stderr)
    sys.exit(1)

# --- Streaming Text-to-Speech Function ---
def stream_text_to_speech(text_input, tts_model, audio_stream):
    sentences = text_input.split('.')  # Simple split for demonstration
    for sentence in sentences:
        processed_sentence = sentence.strip()
        if not processed_sentence:
            continue

        print(f"Synthesizing: \"{processed_sentence}...\"")
        try:
            wav = tts_model.tts(
                text=processed_sentence,
                speaker=None,
                speaker_wav="/vv/en-IN-Chirp-HD-O.wav",  # Default voice
                language="en"    # Language code
            )

            wav = np.array(wav).astype(np.float32)
            orig_sr = tts.synthesizer.output_sample_rate  # typically 22050 or 16000

            # Convert to NumPy array
            wav_np = np.array(wav, dtype=np.float32)

            # Resample to 8000 Hz
            target_sr = 8000
            wav_resampled = scipy.signal.resample_poly(wav_np, up=target_sr, down=orig_sr)

            # Normalize and convert to int16 (LINEAR16)
            wav_int16 = np.int16(wav_resampled / np.max(np.abs(wav_resampled)) * 32767)

            # Save to buffer as raw PCM (no WAV headers)
            buffer = io.BytesIO()
            buffer.write(wav_int16.tobytes())
            buffer.seek(0)

            # Encode to base64
            audio_base64 = base64.b64encode(buffer.read()).decode('utf-8')
            max_val = np.max(np.abs(wav))
            if max_val > 0:
                wav /= max_val
            else:
                wav = np.zeros_like(wav)
            print(wav.tobytes())

            # audio_stream.write(wav.tobytes())
            print(f"Played audio for: \"{processed_sentence}\"")

        except Exception as e:
            print(f"Error during synthesis for sentence \"{processed_sentence}\": {e}", file=sys.stderr)

# --- Main Loop ---
print("\n--- Real-time TTS Demo (Sentence by Sentence) ---")
print(f"Using Coqui TTS model: {TTS_MODEL_NAME}")
print("Type some text and press Enter. Type 'exit' to quit.")

try:
    while True:
        user_input = input("Enter text: ")
        if user_input.lower().strip() == 'exit':
            break
        elif not user_input.strip():
            continue
        stream_text_to_speech(user_input, tts, stream)

except KeyboardInterrupt:
    print("\nCtrl+C detected. Exiting.")
except Exception as e:
    print(f"\nAn unexpected error occurred: {e}", file=sys.stderr)

# # --- Cleanup ---
# print("Cleaning up...")
# try:
#     if stream.is_active():
#         stream.stop_stream()
#     stream.close()
#     p.terminate()
#     print("Audio stream closed.")
# except Exception as e:
#     print(f"Error during cleanup: {e}", file=sys.stderr)

# print("Demo finished.")
