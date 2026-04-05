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
    Predict digit from voice recording.
    Currently returns a random digit – replace with actual speech recognition.
    """
    import random
    digit = random.randint(0, 9)
    confidence = round(random.uniform(80, 100), 2)
    return digit, confidence
