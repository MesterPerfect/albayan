import os
from typing import Optional
from pathlib import Path # Added Path import
from .bass_player import AudioPlayer
from utils.settings import SettingsManager
from exceptions.error_decorators import exception_handler

class SoundEffectPlayer(AudioPlayer):
    instances = []
    def __init__(self, sounds_folder: Path) -> None: # Changed type hint for sounds_folder
        super().__init__(SettingsManager.current_settings["audio"]["volume_level"])
        self.sounds_folder = sounds_folder
        self.sounds = {}
        self.load_sound_effects()
        SoundEffectPlayer.instances.append(self)

    @exception_handler
    def load_sound_effects(self) -> None:
        """Loads sound effects from the specified folder into a dictionary."""
        if not self.sounds_folder.is_dir():
            # Or handle this error as appropriate for your application
            print(f"Sounds folder not found: {self.sounds_folder}")
            return
        for file_path in self.sounds_folder.iterdir(): # Changed to iterdir()
            if file_path.suffix.lower() in self.supported_extensions: # Changed to use suffix
                self.sounds[file_path.stem] = file_path # Store Path object, use stem

    @exception_handler
    def play(self, file_name: Optional[str]= None) -> None:
        """Plays a specified or random sound effect if enabled."""
        if not SettingsManager.current_settings["audio"]["sound_effect_enabled"]:
            return

        if file_name not in self.sounds:
            raise ValueError(f"Invalid file name '{file_name}'. Available sounds: {list(self.sounds.keys())}")

        file_path = self.sounds[file_name]
        self.load_audio(file_path)
        super().play()
