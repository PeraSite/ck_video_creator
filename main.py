import os
import shlex
import subprocess
import sys

import ffmpeg
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtWidgets import QVBoxLayout, QLineEdit, QListWidget, QListWidgetItem, QAbstractItemView, QPushButton


class SoundItem(QWidget):
    def __init__(self, file_name, file_path, is_voice):
        QWidget.__init__(self, flags=Qt.Widget)
        layout = QHBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)

        layout.addWidget(QLabel("녹음" if is_voice else "음악"), 1, alignment=Qt.AlignCenter)

        self.intro_checkbox = QCheckBox()
        layout.addWidget(self.intro_checkbox, 1, alignment=Qt.AlignCenter)

        layout.addWidget(QLabel(file_name), 8)
        self.setLayout(layout)

        self.file_name = file_name
        self.file_path = file_path
        self.is_voice = is_voice


class Main(QDialog):
    def __init__(self):
        super().__init__()

        # 윈도우 설정
        self.setFixedSize(500, 500)
        self.setFocus()
        self.setWindowTitle("청강대 아침음악방송 편집기")

        # UI 표기
        root_layout = QVBoxLayout()

        # 회차 입력
        self.number_input = QLineEdit()
        self.number_input.setPlaceholderText("회차를 입력하세요")
        root_layout.addWidget(self.number_input)

        # 사운드 파일 목록
        voice_files = os.listdir("voices/")
        music_files = os.listdir("musics/")
        self.sound_list = QListWidget()
        for file_name in voice_files + music_files:
            is_voice = file_name in voice_files
            file_path = ("voices/" if is_voice else "musics/") + file_name
            item_widget = SoundItem(file_name, file_path, is_voice)

            item = QListWidgetItem(self.sound_list)
            size = item_widget.sizeHint()
            size.setHeight(30)
            item.setSizeHint(size)
            self.sound_list.addItem(item)
            self.sound_list.setItemWidget(item, item_widget)
        self.sound_list.setDragDropMode(QAbstractItemView.InternalMove)
        root_layout.addWidget(self.sound_list)

        # 시작 버튼
        start_button = QPushButton("시작하기")
        start_button.clicked.connect(self.start)
        root_layout.addWidget(start_button)

        self.setLayout(root_layout)
        self.show()

    def start(self):
        # 회차 가져오기
        number = self.number_input.text()

        # UI에서 파일 데이터 가져오기
        for widget in self.sound_list.findItems('*', Qt.MatchWildcard):
            item_widget = widget.listWidget().itemWidget(widget)

            file_path = item_widget.file_path
            input_data.append(file_path)

            # 인트로 데이터 가져오기
            if item_widget.intro_checkbox.isChecked():
                if item_widget.is_voice:
                    intro_data["voices"].append(file_path)
                else:
                    intro_data["background_music"] = file_path

        file_list = read_input()
        voices = enhance_all_voices()
        intro_audio = create_intro_audio(voices)

        if not os.path.exists(f"아침음악방송_{number}회_오디오.mp3"):
            final_audio = create_final_audio(intro_audio, voices, file_list)
            (
                final_audio.output(f"아침음악방송_{number}회_오디오.mp3")
                .overwrite_output()
                .run()
            )

        if os.path.exists("image.png"):
            create_final_video(f"아침음악방송_{number}회_영상.mp4")

        QMessageBox.information(self, "완료", "완료되었습니다.")


input_data = []
intro_data = {
    "background_music": None,
    "voices": []
}


def main():
    app = QApplication(sys.argv)
    main = Main()
    app.exec()


def read_input():
    print("Reading input...")

    for file in input_data:
        if not os.path.exists(file):
            raise FileNotFoundError(f"{file} does not exist!")

    # 파일 리스트를 (파일명, 음성파일 여부) 튜플로 만들기
    file_list = [(file, file.startswith("voices")) for file in input_data]
    return file_list


def create_final_video(file_name: str):
    print("Creating final video...")

    command = "ffmpeg -r 1 -loop 1 -y -i image.png -i final_audio.mp3 -r 1 -pix_fmt yuv420p -vf scale=-1:1080 " \
              "-shortest " + file_name

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


def create_intro_audio(voices):
    print(f"Processing Intro...")

    # 처음으로 등장하는 음성과 음악 파일을 찾아서 처리
    background_music_path = intro_data["background_music"]
    print(f" - Background music: {background_music_path}")

    print(f" - Voices:")
    intro_voices = []
    for intro_voice_path in intro_data["voices"]:
        print(f"   - {intro_voice_path}")
        intro_voices.append(voices[intro_voice_path])

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
