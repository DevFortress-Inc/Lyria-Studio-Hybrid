import streamlit as st
import asyncio
import os
import time
from lyria_generator import generate_music_file
import audio_utils

st.set_page_config(page_title="Athena Studio Pro", layout="wide", page_icon="🎛️")

st.markdown("""
<style>
    .stButton>button { border-radius: 8px; font-weight: bold; border: 1px solid #3f3f46; }
    .stButton>button:hover { border-color: #60a5fa; color: #60a5fa; }
    div[data-testid="stToolbar"] { visibility: hidden; }
    footer { visibility: hidden; }
    .block-container { padding-top: 2rem; }
    div[data-testid="stToast"] { background-color: #18181b; color: white; border: 1px solid #3f3f46; }
</style>
""", unsafe_allow_html=True)

if 'original_file' not in st.session_state:
    st.session_state.original_file = None
if 'working_file' not in st.session_state:
    st.session_state.working_file = None
if 'segments_info' not in st.session_state:
    st.session_state.segments_info = []
if 'last_generated_segment' not in st.session_state:
    st.session_state.last_generated_segment = None
if 'export_mode' not in st.session_state:
    st.session_state.export_mode = False
if 'original_prompt' not in st.session_state:
    st.session_state.original_prompt = ""

query_params = st.query_params
if "file" in query_params:
    target_file = query_params["file"]
    target_prompt = query_params.get("prompt", "Audio Track")

    if os.path.exists(target_file):
        if st.session_state.get('original_file') != target_file:
            st.session_state.original_file = target_file
            st.session_state.original_prompt = target_prompt
            st.session_state.working_file = audio_utils.create_working_copy(target_file)
            st.session_state.segments_info = []
            st.session_state.last_generated_segment = None
            st.session_state.export_mode = False
            st.toast(f"Project Loaded: {target_prompt}", icon="🎹")


def finish_project(save=True):
    import gc
    gc.collect()

    if save and st.session_state.working_file:
        import shutil
        base_name = os.path.splitext(st.session_state.original_file)[0]
        clean_name = base_name.split('_edited')[0]
        new_filename = f"{clean_name}_edited_{int(time.time())}.wav"

        shutil.copy(st.session_state.working_file, new_filename)

        st.session_state.original_file = new_filename
        st.session_state.export_mode = True

        try:
            os.remove(st.session_state.working_file)
        except:
            pass
        for f in os.listdir():
            if f.startswith("candidate_seg_") and f.endswith(".wav"):
                try:
                    os.remove(f)
                except:
                    pass

        st.balloons()
        st.rerun()

    else:
        st.rerun()


if st.session_state.export_mode:
    col_spacer_l, col_content, col_spacer_r = st.columns([1, 2, 1])
    with col_content:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("### Mastering Complete")
        st.success("Your edited track has been rendered and saved successfully.")

        st.markdown("---")

        if st.session_state.original_file and os.path.exists(st.session_state.original_file):
            with open(st.session_state.original_file, "rb") as file:
                st.download_button(
                    label="Download Master WAV",
                    data=file,
                    file_name=os.path.basename(st.session_state.original_file),
                    mime="audio/wav",
                    use_container_width=True,
                    type="primary"
                )

        st.markdown("<br>", unsafe_allow_html=True)
        st.info("You may now close this Studio tab and return to the Chat.")

elif st.session_state.original_file and st.session_state.working_file:
    c_title, c_meta = st.columns([2, 1])
    with c_title:
        st.title("Athena Studio Editor")
    with c_meta:
        st.markdown(
            f"<div style='text-align:right; color:#a1a1aa; padding-top:10px;'>Editing: <b>{st.session_state.get('original_prompt', 'Unknown')}</b></div>",
            unsafe_allow_html=True)

    st.markdown("##### Master Bus (Preview)")
    st.audio(st.session_state.working_file)
    total_duration = audio_utils.get_audio_duration(st.session_state.working_file)

    st.markdown("---")

    c1, c2 = st.columns([1, 2])
    with c1:
        st.markdown("**Segmentation Logic**")
        num_segments = st.number_input("Splits", 1, 10, 4)
        if st.button("Analyze & Split Track", use_container_width=True):
            seg_len = total_duration / num_segments
            st.session_state.segments_info = []
            for i in range(num_segments):
                st.session_state.segments_info.append({
                    "id": i + 1, "start": round(i * seg_len, 2), "end": round((i + 1) * seg_len, 2),
                    "name": f"Section {i + 1}"
                })

    with c2:
        if st.session_state.segments_info:
            st.markdown("**Timeline Structure**")
            cols = st.columns(len(st.session_state.segments_info))
            for idx, seg in enumerate(st.session_state.segments_info):
                cols[idx].info(f"{seg['name']}\n{seg['start']}-{seg['end']}s")
        else:
            st.info("No segmentation applied yet. Select splits to begin deep editing.")

    if st.session_state.segments_info:
        st.markdown("---")
        st.subheader("Deep Editing")

        seg_options = [s['name'] for s in st.session_state.segments_info]
        sel_name = st.selectbox("Select Region", seg_options)
        sel_seg = next(s for s in st.session_state.segments_info if s['name'] == sel_name)

        cL, cR = st.columns([2, 1])
        with cL:
            st.markdown(f"**Modifying: {sel_name}**")
            new_prompt = st.text_area("In-painting Prompt", value=st.session_state.original_prompt, height=100)

            sc1, sc2, sc3 = st.columns(3)
            new_bpm = sc1.slider("BPM", 60, 180, 90)
            new_den = sc2.slider("Density", 0.0, 1.0, 0.6)
            xfade = sc3.number_input("Crossfade (s)", 1, 5, 3)

            if st.button(f"⚡ Regenerate {sel_name}", type="secondary", use_container_width=True):
                needed = (sel_seg['end'] - sel_seg['start']) + (xfade / 2)
                with st.spinner("Synthesizing audio variation..."):
                    cand = f"candidate_seg_{sel_seg['id']}.wav"
                    res = asyncio.run(generate_music_file(
                        weighted_prompts=[{"text": new_prompt, "weight": 1.0}],
                        duration_seconds=int(needed),
                        bpm=new_bpm,
                        guidance=7.0,
                        density=new_den,
                        output_filename=cand
                    ))
                    if res:
                        st.session_state.last_generated_segment = res
                        st.success("Variation created successfully.")

        with cR:
            st.markdown("**Candidate Preview**")
            if st.session_state.last_generated_segment:
                st.audio(st.session_state.last_generated_segment)
                if st.button("Commit Change", type="primary", use_container_width=True):
                    with st.spinner("DSP Stitching..."):
                        nw = audio_utils.stitch_segment_into_track(
                            st.session_state.working_file, st.session_state.last_generated_segment,
                            sel_seg['start'], sel_seg['end'], xfade * 1000
                        )
                        st.session_state.working_file = nw
                        st.session_state.last_generated_segment = None
                        st.rerun()
            else:
                st.markdown("*Generate a variation to see preview*")

    st.markdown("---")
    f1, f2 = st.columns([1, 4])
    if f2.button("FINISH & EXPORT MASTER", type="primary", use_container_width=True):
        finish_project(True)

else:
    st.empty()
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        st.info("**Waiting for Project...**")
        st.markdown("Please generate a track in the **React Chat** and click *'Open in Studio'* to begin editing.")