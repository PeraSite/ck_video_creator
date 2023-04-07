import os

import ffmpeg


def main():
    file_list = read_input()
    voices = enhance_all_voices()
    intro_audio = create_intro_audio(voices, file_list)
    final_audio = create_final_audio(intro_audio, voices, file_list)

    # if image.png exists, create final video
    if os.path.exists("image.png"):
        create_final_video(final_audio, "image.png", "final_video.mp4")
    else:
        print("No image.png found, creating final audio only...")
        (
            final_audio.output("final_audio.mp3")
            .overwrite_output()
            .run()
        )

    print("Done!")


def read_input():
    print("Reading input...")

    # 순서.txt 파일을 읽어서 파일 리스트를 만들기
    input_data = []
    with open("순서.txt", "r", encoding="utf-8") as f:
        input_data.extend(f.readlines())
    input_data = [file.strip() for file in input_data]

    # 해당 파일이 있는지 검증
    for file in input_data:
        if not os.path.exists(file):
            raise FileNotFoundError(f"{file} does not exist!")

    # 파일 리스트를 (파일명, 음성파일 여부) 튜플로 만들기
    file_list = [(file, file.startswith("voices")) for file in input_data]
    return file_list


def create_final_video(audio_stream, image_path: str, output_path: str):
    print("Creating final video...")

    # 1080p로 스케일링 후 mjpeg로 인코딩
    (
        ffmpeg
        .output(audio_stream, ffmpeg.input(image_path), output_path, vf="scale=-1:1080", vcodec="mjpeg")
        .overwrite_output()
        .run()
    )


def create_final_audio(intro_audio, voices, file_list: list[tuple[str, bool]]):
    print("Creating final audio...")
    audio_streams = [intro_audio]

    # TODO: 하드코딩으로 초반 2개가 무조건 대사/음악인 부분 수정해야함
    for file, is_voice in file_list[1:]:
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
    voice_path = next(file for file, is_voice in file_list if is_voice)
    background_music_path = next(file for file, is_voice in file_list if not is_voice)
    voice = voices[voice_path]

    print(f" - Background music: {background_music_path}")
    print(f" - Voice: {voice_path}")

    music_audio = (
        ffmpeg
        .input(background_music_path)
        .filter("loudnorm", i=-30)
        .filter("afade", type="in", start_time=0, duration=1)
    )

    voice_audio = (
        voice
        .filter("adelay", "2000|2000")
    )

    return (
        ffmpeg
        .filter([voice_audio, music_audio], "amix", inputs=2, duration="first", normalize=0, dropout_transition=0)
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
