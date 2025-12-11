import os
import shutil
from pydub import AudioSegment


def create_working_copy(original_path):
    base, ext = os.path.splitext(original_path)
    work_path = f"{base}_work{ext}"
    shutil.copy(original_path, work_path)
    return work_path


def get_audio_duration(file_path):
    audio = AudioSegment.from_file(file_path)
    return len(audio) / 1000.0


def stitch_segment_into_track(
        main_track_path,
        new_segment_path,
        start_time_sec,
        end_time_sec,
        crossfade_ms=5000
):
    print(f" Stitching: Insertando en {start_time_sec}s - {end_time_sec}s con {crossfade_ms}ms fade.")

    main_audio = AudioSegment.from_file(main_track_path)
    new_segment = AudioSegment.from_file(new_segment_path)

    start_ms = start_time_sec * 1000
    end_ms = end_time_sec * 1000

    part_a = main_audio[:start_ms] if start_ms > 0 else AudioSegment.empty()

    part_c = main_audio[end_ms:] if end_ms < len(main_audio) else AudioSegment.empty()

    if len(part_a) > 0:
        temp_mix = part_a.append(new_segment, crossfade=crossfade_ms)
    else:
        temp_mix = new_segment

    if len(part_c) > 0:
        final_mix = temp_mix.append(part_c, crossfade=crossfade_ms)
    else:
        final_mix = temp_mix

    final_mix.export(main_track_path, format="wav")
    return main_track_path