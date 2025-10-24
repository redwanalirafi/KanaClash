import os
import streamlit as st
import google.generativeai as genai
import speech_recognition as sr
import librosa
import numpy as np

# --- Audio Feature Extraction ---
def extract_fluency_features(audio_path):
    y, sr = librosa.load(audio_path)
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    # Ensure tempo is a float, not an ndarray
    if isinstance(tempo, (list, np.ndarray)):
        tempo = float(np.mean(tempo))

    duration = librosa.get_duration(y=y, sr=sr)
    non_silent_intervals = librosa.effects.split(y, top_db=30)
    silence_ratio = 1 - sum((end - start) for start, end in non_silent_intervals) / len(y)

    return {
        "tempo": float(tempo),
        "duration": float(duration),
        "silence_ratio": float(silence_ratio)
    }

# --- Configure Gemini API ---
genai.configure(api_key="XXX")

st.title("🎙️ AI Japanese Speech Feedback App (Gemini Demo)")

# --- Input target sentence ---
target_sentence = st.text_input("Target Japanese sentence:", "これはなんですか。")

if st.button("Record & Analyze"):
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        st.info("🎧 Speak now...")
        audio = recognizer.listen(source)
        st.success("✅ Recording complete!")

    # --- Save audio file ---
    audio_path = "user_audio.wav"
    with open(audio_path, "wb") as f:
        f.write(audio.get_wav_data())

    # --- Speech to Text ---
    try:
        user_text = recognizer.recognize_google(audio, language="ja-JP")
        st.write(f"🗣️ You said: {user_text}")

        # --- Extract fluency features ---
        features = extract_fluency_features(audio_path)

        print(features)

    except Exception as e:
        st.error(f"Speech recognition failed: {e}")
        st.stop()

    # --- Prepare Prompt ---
    prompt = f"""
You are an expert Japanese speech coach.

Evaluate this spoken performance for *fluency* and *naturalness*.

Target sentence: {target_sentence}
Recognized user speech: {user_text}
Audio statistics:
- Speaking tempo: {features['tempo']:.2f}
- Duration: {features['duration']:.2f} seconds
- Silence ratio: {features['silence_ratio']:.2f}

Give:
1. Fluency score (0–100)
2. Naturalness score (0–100)
3. English explanation of issues
4. Japanese explanation of issues
5. Concrete tips to sound more native
6. A short sentence describing emotional tone (e.g., “Sounds calm but hesitant.”)
"""

    # --- Send to Gemini ---
    model = genai.GenerativeModel("models/gemini-2.5-flash")
    response = model.generate_content(prompt)
    result = response.text

    # --- Display Results ---
    st.subheader("🎙️ Fluency & Naturalness Analysis")
    st.write(result)
