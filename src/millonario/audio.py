from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer, QSoundEffect


class AudioService(QObject):
    def __init__(self, audio_dir: Path, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.audio_dir = audio_dir

        self.music_output = QAudioOutput(self)
        self.music_output.setVolume(0.28)
        self.music_player = QMediaPlayer(self)
        self.music_player.setAudioOutput(self.music_output)
        self.music_player.setLoops(QMediaPlayer.Loops.Infinite)

        self.voice_output = QAudioOutput(self)
        self.voice_output.setVolume(0.8)
        self.voice_player = QMediaPlayer(self)
        self.voice_player.setAudioOutput(self.voice_output)

        self.correct_effect = self._sound_effect("correct.wav", 0.9)
        self.incorrect_effect = self._sound_effect("incorrect.wav", 0.9)
        self.lifeline_effect = self._sound_effect("lifeline.wav", 0.75)

    def _sound_effect(self, filename: str, volume: float) -> QSoundEffect:
        effect = QSoundEffect(self)
        path = self.audio_dir / filename
        if path.exists():
            effect.setSource(QUrl.fromLocalFile(str(path)))
        effect.setVolume(volume)
        return effect

    def start_question_music(self) -> None:
        self._set_source_if_exists(
            self.music_player,
            self.audio_dir / "question_music.mp3",
        )
        self.music_player.play()

    def start_intro_music(self) -> None:
        self._set_source_if_exists(
            self.music_player,
            self.audio_dir / "intro.mp3",
        )
        self.music_player.play()

    def stop_music(self) -> None:
        self.music_player.stop()

    def play_correct(self) -> None:
        self.correct_effect.play()

    def play_incorrect(self) -> None:
        self.incorrect_effect.play()

    def play_fifty(self) -> None:
        self.lifeline_effect.play()

    def play_phone(self) -> None:
        self._play_voice("call.mp3")

    def play_audience(self) -> None:
        self._play_voice("audience.wav")

    def _play_voice(self, filename: str) -> None:
        self._set_source_if_exists(self.voice_player, self.audio_dir / filename)
        self.voice_player.play()

    @staticmethod
    def _set_source_if_exists(player: QMediaPlayer, path: Path) -> None:
        if path.exists():
            source = QUrl.fromLocalFile(str(path))
            if player.source() != source:
                player.setSource(source)

    def shutdown(self) -> None:
        self.music_player.stop()
        self.voice_player.stop()
        for effect in (
            self.correct_effect,
            self.incorrect_effect,
            self.lifeline_effect,
        ):
            effect.stop()
