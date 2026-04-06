# backend/predict.py
import os
import io
import base64
import numpy as np
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing import image
from PIL import Image, ImageOps

# Load trained model
model_path = os.path.join(os.path.dirname(__file__), "../model/digit_model.h5")
model = load_model(model_path)

def predict_digit(img_path):
    """Predict digit from an uploaded image file."""
    img = image.load_img(img_path, target_size=(28, 28), color_mode="grayscale")
    img_array = image.img_to_array(img).reshape(1, 28, 28, 1) / 255.0
    prediction = model.predict(img_array, verbose=0)
    digit = int(np.argmax(prediction))
    confidence = round(float(np.max(prediction) * 100), 2)
    return digit, confidence

def predict_digit_from_canvas(img_data):
    """Predict digit from canvas base64 image data."""
    # Decode base64
    img_str = img_data.split(",")[1]
    img_bytes = base64.b64decode(img_str)
    img = Image.open(io.BytesIO(img_bytes)).convert("L")  # grayscale

    # Invert if necessary (canvas draws black on white? adjust as needed)
    img_array = np.array(img)
    if np.mean(img_array) < 128:
        img = Image.fromarray(255 - img_array)

    # Crop to bounding box
    bbox = ImageOps.invert(img).getbbox()
    if bbox:
        img = img.crop(bbox)

    # Resize to 20x20 (using LANCZOS for quality)
    img = img.resize((20, 20), Image.LANCZOS)

    # Paste onto 28x28 white canvas
    new_img = Image.new("L", (28, 28), 255)
    new_img.paste(img, ((28 - 20) // 2, (28 - 20) // 2))

    # Normalize and reshape
    img_array = np.array(new_img) / 255.0
    img_array = img_array.reshape(1, 28, 28, 1)

    # Predict
    pred = model.predict(img_array, verbose=0)
    digit = int(np.argmax(pred))
    confidence = round(float(np.max(pred) * 100), 2)
    return {"digit": digit, "confidence": confidence}

def predict_digit_from_voice(audio_path):
    """
    Predict digit from voice recording using speech recognition.
    Converts audio to text and extracts the digit mentioned.
    """
    import speech_recognition as sr
    import librosa
    import soundfile as sf
    
    try:
        # Load audio file with librosa
        audio_data, sr_rate = librosa.load(audio_path, sr=16000)
        
        # Convert to 16-bit PCM format that speech_recognition expects
        audio_data_int16 = (audio_data * 32767).astype(np.int16)
        
        # Save as WAV with proper format
        temp_wav = audio_path.replace('.wav', '_converted.wav')
        sf.write(temp_wav, audio_data_int16, 16000)
        
        # Now use speech_recognition with the converted file
        recognizer = sr.Recognizer()
        with sr.AudioFile(temp_wav) as source:
            audio = recognizer.record(source)
        
        # Try Google Speech Recognition
        try:
            text = recognizer.recognize_google(audio, language='en-US').lower()
            print(f"[DEBUG] Recognized text: {text}")
        except sr.UnknownValueError:
            print("[DEBUG] Speech not understood")
            return 0, 30.0
        except sr.RequestError as e:
            print(f"[DEBUG] API error: {e}")
            return 0, 20.0
        
        # Extract digit from recognized text (handles "zero", "one", "two", etc.)
        digit_words = {
            'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4,
            'five': 5, 'six': 6, 'seven': 7, 'eight': 8, 'nine': 9
        }
        
        # Try to find digit word in recognized text
        for word, digit in digit_words.items():
            if word in text:
                print(f"[DEBUG] Found digit word: {word} -> {digit}")
                # Clean up temp file
                if os.path.exists(temp_wav):
                    os.remove(temp_wav)
                return digit, 85.0
        
        # If no digit word found, check for direct numbers
        for char in text:
            if char.isdigit():
                print(f"[DEBUG] Found digit character: {char}")
                # Clean up temp file
                if os.path.exists(temp_wav):
                    os.remove(temp_wav)
                return int(char), 80.0
        
        # If nothing found but something was recognized
        print(f"[DEBUG] No digit found in text: {text}")
        # Clean up temp file
        if os.path.exists(temp_wav):
            os.remove(temp_wav)
        return 0, 50.0
        
    except Exception as e:
        print(f"[ERROR] Voice recognition error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return 0, 10.0
