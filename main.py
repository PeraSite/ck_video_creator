import os
import subprocess
import shlex

import ffmpeg

input_data = [
    "voices/음악방송_11회_녹음_1.m4a",
    "voices/음악방송_11회_녹음_2.m4a",
    "voices/음악방송_11회_녹음_3.m4a",
    "musics/강하늘-24-자화상.mp3",
    "musics/박효신-01-그 날 (Original Ver.).mp3",
    "musics/안예은-01-8호 감방의 노래.mp3",
    "voices/음악방송_11회_녹음_4.m4a",
    "musics/김고은-06-그대 향한 나의 꿈.mp3",
    "musics/정성화,조재윤,배정남,이현우-14-누가 죄인인가.mp3",
    "voices/음악방송_11회_녹음_5.m4a",
    "voices/음악방송_11회_녹음_6.m4a",
    "voices/음악방송_11회_녹음_7.m4a",
    "voices/음악방송_11회_녹음_8.m4a",
]

intro_data = {
    "background_music": "musics/강하늘-24-자화상.mp3",
    "voices": [0, 1, 2]
}


def main():
    file_list = read_input()
    voices = enhance_all_voices()
    intro_audio = create_intro_audio(voices, file_list)

    final_audio = create_final_audio(intro_audio, voices, file_list)
    (
        final_audio.output("final_audio.mp3")
        .overwrite_output()
        .run()
    )
    if os.path.exists("image.png"):
        create_final_video()

    print("Done!")


def read_input():
    print("Reading input...")

    for file in input_data:
        if not os.path.exists(file):
            raise FileNotFoundError(f"{file} does not exist!")

    # 파일 리스트를 (파일명, 음성파일 여부) 튜플로 만들기
    file_list = [(file, file.startswith("voices")) for file in input_data]
    return file_list


def create_final_video():
    print("Creating final video...")

    command = "ffmpeg -r 1 -loop 1 -y -i image.png -i final_audio.mp3 -r 1 -pix_fmt yuv420p -vf scale=-1:1080 " \
              "-shortest output.mp4"

    subprocess.run(shlex.split(command), shell=True, check=True)


def create_final_audio(intro_audio, voices, file_list: list[tuple[str, bool]]):
    print("Creating final audio...")
    audio_streams = [intro_audio]

    # 인트로 음성 개수 제외
    intro_size = len(intro_data["voices"])
    print(f" - Skipping {intro_size} files...")

    for file, is_voice in file_list[intro_size:]:
        print(f" - {file} - ({'Voice' if is_voice else 'Music'})")
        if is_voice:
            audio_streams.append(voices[file])
        else:
            audio_streams.append(ffmpeg.input(file))

    return (
        ffmpeg
        .filter(audio_streams, "concat", n=len(audio_streams), v=0, a=1)
    )


def create_intro_audio(voices, file_list: list[tuple[str, bool]]):
    print(f"Processing Intro...")

    # 처음으로 등장하는 음성과 음악 파일을 찾아서 처리
    background_music_path = intro_data["background_music"]
    print(f" - Background music: {background_music_path}")

    print(f" - Voices:")
    intro_voices = []
    for i in intro_data["voices"]:
        print(f"   - {file_list[i][0]}")
        intro_voices.append(voices[file_list[i][0]])

    music_audio = (
        ffmpeg
        .input(background_music_path)
        .filter("loudnorm", i=-30)
        .filter("afade", type="in", start_time=0, duration=1)
    )

    voice_audio = (
        ffmpeg
        .filter(intro_voices, "concat", n=len(intro_voices), v=0, a=1)
        .filter("adelay", "2000|2000")
    )

    return (
        ffmpeg
        .filter([voice_audio, music_audio], "amix", inputs=2, duration="first", normalize=0, dropout_transition=0)
        .filter("areverse")
        .filter("afade", duration=1)
        .filter("areverse")
    )


def enhance_all_voices():
    print("Enhancing voices...")
    voice_files = {}

    # Process all voice files
    for file in os.listdir("voices"):
        processed_voice = enhance_voice(f"voices/{file}")
        voice_files[f'voices/{file}'] = processed_voice

    return voice_files


def enhance_voice(input_file: str):
    print(f" - Processing {input_file}...")

    # 앞뒤 공백 음성 제거, 앞뒤 0.5초 여백, 볼륨 정규화
    return (
        ffmpeg
        .input(input_file)
        .filter("silenceremove", start_periods=1, start_silence=0.1, start_threshold="-40dB")
        .filter("adelay", "500|500")
        .filter("areverse")
        .filter("silenceremove", start_periods=1, start_silence=0.1, start_threshold="-40dB")
        .filter("adelay", "1500|1500")
        .filter("areverse")
        .filter("loudnorm", i=-18, lra=11, tp=-1.5)
    )


if __name__ == '__main__':
    main()
