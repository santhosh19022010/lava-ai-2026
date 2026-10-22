import streamlit as st
import io
from groq import Groq

try:
    from gtts import gTTS
    HAS_TTS = True
except ImportError:
    HAS_TTS = False
try:
    import speech_recognition as sr
    HAS_SR = True
except ImportError:
    HAS_SR = False
try:
    import pdfplumber
    HAS_PDF = True
except ImportError:
    HAS_PDF = False

st.set_page_config(page_title="Lava AI", page_icon="🌋", layout="centered")
st.markdown("""
<style>
.stApp {background: linear-gradient(160deg,#1a0505,#3d0c0c,#1a0505);}
h1,h2,h3,p,span,label {color:#ffe8d6;}
.stChatMessage {background:rgba(255,107,53,.07);border-radius:12px;}
</style>""", unsafe_allow_html=True)
st.title("🌋 Lava AI")
st.caption("*Where answers erupt!*")

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content":
         "You are Lava, a warm, energetic AI assistant — a volcano of "
         "knowledge! Be helpful, clear, and a little fun."},
        {"role": "assistant", "content":
         "Hey! I'm Lava — your AI assistant! What would you like to know?"}
    ]
if "usage_total" not in st.session_state:
    st.session_state.usage_total = 0
if "saved_chats" not in st.session_state:
    st.session_state.saved_chats = {}
if "speak_idx" not in st.session_state:
    st.session_state.speak_idx = -1

ROLES = {
    "🔥 Lava (Default)": "You are Lava, a warm, energetic AI assistant — a volcano of knowledge!",
    "🤓 Tutor": "You are a patient tutor. Explain step by step, check understanding.",
    "😂 Comedian": "You are a hilarious comedian. Make everything funny but still helpful.",
    "💻 Coder": "You are an expert programmer. Give clean code with explanations.",
    "☕ Friend": "You are a supportive, casual friend. Be empathetic and relaxed.",
}

@st.cache_data
def tts_bytes(text):
    fp = io.BytesIO()
    gTTS(text=text[:600], lang="en").write_to_fp(fp)
    return fp.getvalue()

def copy_block(text):
    with st.expander("📋 Copy reply"):
        st.code(text, language=None)

with st.sidebar:
    st.header("⚙️ Settings")
    api_key = st.text_input("Groq API Key", type="password", placeholder="gsk_...")

    # Live model list (fixes 404 errors)
    if api_key:
        try:
            live_models = sorted(m.id for m in Groq(api_key=api_key).models.list().data)
            model = st.selectbox("🧠 Model", live_models)
        except Exception:
            model = st.text_input("🧠 Model name",
                                  "meta-llama/llama-3.3-70b-versatile")
    else:
        model = st.selectbox("🧠 Model", ["(add API key first)"])

    temperature = st.slider("🌡️ Creativity", 0.0, 1.0, 0.7)
    role = st.selectbox("🎭 Lava's role", list(ROLES.keys()))

    # ── NEW: Language selector ──
    lang = st.selectbox("🌍 Language", ["English", "Arabic", "Hindi",
                                        "Tamil", "Urdu", "French",
                                        "Malayalam", "Spanish"])

    speak = st.checkbox("🔊 Speak replies", value=False)

    st.divider()
    st.subheader("🎤 Voice Input")
    audio = st.audio_input("Talk to Lava")
    if audio and HAS_SR:
        try:
            r = sr.Recognizer()
            with sr.AudioFile(io.BytesIO(audio.read())) as src:
                said = r.record(src)
            st.session_state.pending = r.recognize_google(said)
            st.rerun()
        except Exception:
            st.warning("Couldn't understand audio — try again!")
    elif audio:
        st.warning("pip install SpeechRecognition")

    st.divider()
    st.subheader("🗂️ Chat History")
    name = st.text_input("Save current chat as:")
    if st.button("💾 Save") and name:
        st.session_state.saved_chats[name] = list(st.session_state.messages)
    if st.session_state.saved_chats:
        pick = st.selectbox("Load chat:", list(st.session_state.saved_chats))
        if st.button("📂 Load"):
            st.session_state.messages = list(st.session_state.saved_chats[pick])
            st.rerun()

    st.divider()
    chat_txt = "\n\n".join(f"{m['role'].upper()}: {m['content']}"
                           for m in st.session_state.messages if m["role"] != "system")
    st.download_button("⬇️ Download chat", chat_txt, "lava_chat.txt")
    st.metric("Tokens used", f"{st.session_state.usage_total:,}")
    if st.button("🗑️ Clear chat"):
        st.session_state.messages = st.session_state.messages[:1]
        st.session_state.messages.append(
            {"role": "assistant", "content": "Fresh start! What's up?"})
        st.rerun()

# Personality + language (emojis kept OUT of API text — Windows-safe)
st.session_state.messages[0]["content"] = ROLES[role] + f" Always respond in {lang}."

c1, c2, c3, c4 = st.columns(4)
prefix = None
if c1.button("👶 ELI5"):       prefix = "Explain like I'm 5: "
if c2.button("😂 Funny"):      prefix = "Make this funny: "
if c3.button("📝 Summarize"):  prefix = "Summarize this: "
if c4.button("📋 Pros/Cons"):  prefix = "Give pros and cons of: "

with st.expander("📄 Upload a file for Lava to read"):
    f = st.file_uploader(".txt / .pdf", type=["txt", "pdf"])
    if f and api_key:
        if f.name.endswith(".pdf") and HAS_PDF:
            with pdfplumber.open(f) as pdf:
                ftext = "\n".join((p.extract_text() or "") for p in pdf.pages)
        else:
            ftext = f.read().decode(errors="ignore")
        if st.button("🚀 Summarize file"):
            st.session_state.pending = "Summarize this:\n\n" + ftext[:8000]
            st.rerun()

with st.expander("🖼️ Send Lava a picture"):
    img = st.file_uploader("jpg / png", type=["jpg", "png", "jpeg"])
    ask_img = st.text_input("Ask about the image:", "Describe this image")
    if img and st.button("👀 Analyze") and api_key:
        import base64
        b64 = base64.b64encode(img.read()).decode()
        vision_model = next((m for m in (live_models if api_key else [])
                             if "vision" in m or "llama-4" in m),
                            "meta-llama/llama-3.2-11b-vision-preview")
        res = Groq(api_key=api_key).chat.completions.create(
            model=vision_model,
            messages=[{"role": "user", "content": [
                {"type": "text", "text": ask_img},
                {"type": "image_url",
                 "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}]}])
        ans = res.choices[0].message.content
        st.session_state.messages.append({"role": "user", "content": f"[Image] {ask_img}"})
        st.session_state.messages.append({"role": "assistant", "content": ans})
        st.rerun()

for i, m in enumerate(st.session_state.messages):
    if m["role"] == "system":
        continue
    with st.chat_message(m["role"]):
        st.markdown(m["content"])
        if m["role"] == "assistant":
            copy_block(m["content"])
            if speak and HAS_TTS and i > st.session_state.speak_idx:
                st.audio(tts_bytes(m["content"]), format="audio/mp3")
                st.session_state.speak_idx = i

if st.button("🔗 Share summary"):
    if not api_key:
        st.error("Add API key first!")
    else:
        chat_model = model if isinstance(model, str) and not model.startswith("(") \
            else "meta-llama/llama-3.1-8b-instant"
        with st.spinner("Lava is summarizing..."):
            r = Groq(api_key=api_key).chat.completions.create(
                model=chat_model,
                messages=[{"role": "system", "content":
                           "Summarize this conversation in 5 lines."}] +
                         [m for m in st.session_state.messages if m["role"] != "system"])
            summary = r.choices[0].message.content
        st.info("📤 Shareable summary:\n\n" + summary)
        st.download_button("⬇️ Download summary", summary, "lava_summary.txt")

prompt = st.session_state.pop("pending", None) or st.chat_input("Ask Lava anything...")

if prompt:
    if prefix:
        prompt = prefix + prompt
    if not api_key:
        st.error("⚠️ Add your Groq API key in the sidebar!")
        st.stop()

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            stream = Groq(api_key=api_key).chat.completions.create(
                model=model, temperature=temperature,
                messages=st.session_state.messages, stream=True)
            reply_box, full = st.empty(), ""
            for chunk in stream:
                delta = chunk.choices[0].delta.content or ""
                full += delta
                reply_box.markdown(full + "▌")
            reply_box.markdown(full)
            if chunk.usage:
                st.session_state.usage_total += chunk.usage.total_tokens
            st.session_state.messages.append({"role": "assistant", "content": full})
            copy_block(full)
            if speak and HAS_TTS:
                st.audio(tts_bytes(full), format="audio/mp3")
                st.session_state.speak_idx = len(st.session_state.messages) - 1
        except Exception as e:
            st.error(f"🔥 Error: {e}")
