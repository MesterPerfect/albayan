import unittest
from unittest.mock import patch, MagicMock, call, ANY
import os
import sys
import time # For mocking time.sleep
from urllib.parse import urlparse as original_urlparse # Keep a reference if needed

# Assuming the module structure allows this import
from utils.audio_player.bass_player import AudioPlayer, bass_initializer, BassFlag
from utils.audio_player.status import PlaybackStatus
from exceptions.audio_pplayer import (
    AudioFileNotFoundError, LoadFileError, UnsupportedFormatError, PlaybackControlError,
    InvalidSourceError, PlaybackInitializationError
)

# Mock the bass object that is initialized at the module level in bass_player.py
# This mock needs to be in place *before* AudioPlayer is defined if bass_player.py is re-imported
# or if the bass object is accessed at class level.
# For instance methods, patching utils.audio_player.bass_player.bass is usually sufficient.
mock_bass_module_object = MagicMock()

# BASS function return values / side effects can be configured per test.
# Common BASS constants that might be checked or used by the code
BASS_ACTIVE_PLAYING = 1
BASS_ACTIVE_PAUSED = 2
BASS_ACTIVE_STALLED = 3
BASS_ACTIVE_STOPPED = 0 # Or some other value that means stopped

# Attribute constants (from BASS documentation, e.g., BASS_ATTRIB_VOL)
BASS_ATTRIB_VOL = 2


# Patch the bass object at the source module level
# This ensures that when AudioPlayer instances call methods on 'bass', they are calling our mock.
@patch('utils.audio_player.bass_player.bass', new=mock_bass_module_object)
class TestAudioPlayer(unittest.TestCase):

    def setUp(self):
        # Reset the mock_bass_module_object for each test to clear call counts and configurations
        mock_bass_module_object.reset_mock()
        
        # Clear the global instances list for AudioPlayer before each test
        AudioPlayer.instances = []

        # Common dummy source, can be overridden in tests
        self.dummy_mp3_path = "tests/fixtures/dummy.mp3" # Assumed to exist for some tests
        self.dummy_url = "http://example.com/audio.mp3"

        # Mock os.path.isfile
        self.mock_isfile = patch('os.path.isfile').start()
        self.mock_isfile.return_value = True # Default to file exists for most tests

        # Mock urlparse
        self.mock_urlparse = patch('utils.audio_player.bass_player.urlparse').start()
        # Default urlparse: treat as local file unless scheme and netloc are set
        self.mock_urlparse.return_value = original_urlparse("") 

        # Mock time.sleep to speed up tests that use it (e.g. load_audio retries)
        self.mock_time_sleep = patch('time.sleep').start()


    def tearDown(self):
        # Stop all patches started with start()
        patch.stopall()
        # Ensure AudioPlayer.instances is clean if a test didn't clean up
        for instance in AudioPlayer.instances:
            if instance.current_channel:
                instance.stop() # Try to gracefully stop
        AudioPlayer.instances = []


    # --- 1. Initialization (__init__) ---
    def test_initialization_defaults(self):
        player = AudioPlayer(volume=0.75)
        self.assertEqual(player.volume, 0.75)
        self.assertEqual(player.flag, BassFlag.AUTO_FREE) # Default flag
        self.assertIsNone(player.source)
        self.assertIsNone(player.current_channel)
        self.assertIn(player, AudioPlayer.instances)

    def test_initialization_with_custom_flag(self):
        custom_flag = 12345 # Dummy flag value
        player = AudioPlayer(volume=0.5, flag=custom_flag)
        self.assertEqual(player.flag, custom_flag)
        self.assertIn(player, AudioPlayer.instances)

    # --- 2. load_audio ---
    def test_load_audio_local_file_success(self):
        player = AudioPlayer(volume=0.5)
        mock_bass_module_object.BASS_StreamCreateFile.return_value = 1 # Mock channel handle
        
        player.load_audio(self.dummy_mp3_path)

        self.mock_isfile.assert_called_once_with(self.dummy_mp3_path)
        mock_bass_module_object.BASS_StreamCreateFile.assert_called_once_with(
            False, self.dummy_mp3_path.encode('utf-8'), 0, 0, player.flag
        )
        self.assertEqual(player.current_channel, 1)
        self.assertEqual(player.source, self.dummy_mp3_path)
        mock_bass_module_object.BASS_ChannelSetAttribute.assert_called_once_with(
            1, BASS_ATTRIB_VOL, ANY # ctypes.c_float(0.5) - check type or value approximately
        )
        # Check the actual value passed to BASS_ChannelSetAttribute for volume
        args, _ = mock_bass_module_object.BASS_ChannelSetAttribute.call_args
        self.assertIsInstance(args[2], ctypes.c_float)
        self.assertAlmostEqual(args[2].value, 0.5)


    def test_load_audio_url_success(self):
        player = AudioPlayer(volume=0.6)
        self.mock_urlparse.return_value = original_urlparse(self.dummy_url) # Simulate URL
        mock_bass_module_object.BASS_StreamCreateURL.return_value = 2 # Mock channel handle

        player.load_audio(self.dummy_url)

        self.mock_urlparse.assert_called_once_with(self.dummy_url)
        mock_bass_module_object.BASS_StreamCreateURL.assert_called_once_with(
            self.dummy_url.encode(), 0, player.flag, None, None
        )
        self.assertEqual(player.current_channel, 2)
        self.assertEqual(player.source, self.dummy_url)
        mock_bass_module_object.BASS_ChannelSetAttribute.assert_called_once_with(
            2, BASS_ATTRIB_VOL, ANY
        )
        args, _ = mock_bass_module_object.BASS_ChannelSetAttribute.call_args
        self.assertAlmostEqual(args[2].value, 0.6)


    def test_load_audio_unsupported_extension(self):
        player = AudioPlayer(volume=0.5)
        with self.assertRaises(UnsupportedFormatError):
            player.load_audio("test.txt")

    def test_load_audio_invalid_source_type(self):
        player = AudioPlayer(volume=0.5)
        with self.assertRaises(InvalidSourceError):
            player.load_audio(123) # Not a string

    def test_load_audio_invalid_source_empty(self):
        player = AudioPlayer(volume=0.5)
        with self.assertRaises(InvalidSourceError):
            player.load_audio("") # Empty string

    def test_load_audio_file_not_found_local(self):
        player = AudioPlayer(volume=0.5)
        self.mock_isfile.return_value = False
        with self.assertRaises(AudioFileNotFoundError):
            player.load_audio(self.dummy_mp3_path)

    def test_load_audio_bass_returns_zero_with_retries(self):
        player = AudioPlayer(volume=0.5)
        mock_bass_module_object.BASS_StreamCreateFile.return_value = 0 # Simulate BASS failure
        
        with self.assertRaises(LoadFileError):
            player.load_audio(self.dummy_mp3_path, attempts=3) # Default attempts in method
        
        self.assertEqual(mock_bass_module_object.BASS_StreamCreateFile.call_count, 3)
        self.assertEqual(self.mock_time_sleep.call_count, 3) # Retries include sleep


    def test_load_audio_stop_previous_channel(self):
        player = AudioPlayer(volume=0.5)
        # First load
        mock_bass_module_object.BASS_StreamCreateFile.return_value = 101 # Channel for first file
        player.load_audio("first.mp3")
        self.assertEqual(player.current_channel, 101)
        mock_bass_module_object.BASS_ChannelSetAttribute.assert_called_with(101, BASS_ATTRIB_VOL, ANY)

        # Reset mocks for BASS calls for the second load, but keep the channel
        mock_bass_module_object.reset_mock() 
        # Important: BASS_StreamCreateFile needs to return a NEW channel for the second file
        mock_bass_module_object.BASS_StreamCreateFile.return_value = 102 
        
        # Second load
        player.load_audio("second.mp3")

        # Check that stop and free were called for the first channel (101)
        mock_bass_module_object.BASS_ChannelStop.assert_called_once_with(101)
        mock_bass_module_object.BASS_StreamFree.assert_called_once_with(101)
        
        # Check that the new channel is set
        self.assertEqual(player.current_channel, 102)
        self.assertEqual(player.source, "second.mp3")
        # Check that volume was set for the new channel
        mock_bass_module_object.BASS_ChannelSetAttribute.assert_called_once_with(102, BASS_ATTRIB_VOL, ANY)

    # --- 3. Playback Control (play, pause, stop) ---
    def test_play_success(self):
        player = AudioPlayer(volume=0.5)
        player.current_channel = 1 # Simulate loaded audio
        player.play()
        mock_bass_module_object.BASS_ChannelPlay.assert_called_once_with(1, False)

    def test_play_no_audio_loaded(self):
        player = AudioPlayer(volume=0.5)
        with self.assertRaises(PlaybackControlError) as ctx:
            player.play()
        self.assertIn("No audio file loaded", str(ctx.exception))


    def test_pause_success(self):
        player = AudioPlayer(volume=0.5)
        player.current_channel = 1 # Simulate loaded audio
        # Assume it's playing or doesn't matter for pause command itself
        player.pause()
        mock_bass_module_object.BASS_ChannelPause.assert_called_once_with(1)

    def test_pause_no_channel(self):
        player = AudioPlayer(volume=0.5)
        player.pause() # Should not raise error
        mock_bass_module_object.BASS_ChannelPause.assert_not_called()

    def test_stop_success(self):
        player = AudioPlayer(volume=0.5)
        player.current_channel = 1 # Simulate loaded audio
        player.stop()
        mock_bass_module_object.BASS_ChannelStop.assert_called_once_with(1)
        mock_bass_module_object.BASS_StreamFree.assert_called_once_with(1)
        self.assertIsNone(player.current_channel)

    def test_stop_no_channel(self):
        player = AudioPlayer(volume=0.5)
        player.stop() # Should not raise error
        mock_bass_module_object.BASS_ChannelStop.assert_not_called()
        mock_bass_module_object.BASS_StreamFree.assert_not_called()


    # --- 4. Volume Control ---
    def test_set_volume_float(self):
        player = AudioPlayer(volume=0.0) # Initial volume doesn't matter here
        player.current_channel = 1 # Simulate loaded audio
        player.set_volume(0.7)
        self.assertAlmostEqual(player.volume, 0.7)
        mock_bass_module_object.BASS_ChannelSetAttribute.assert_called_once_with(1, BASS_ATTRIB_VOL, ANY)
        args, _ = mock_bass_module_object.BASS_ChannelSetAttribute.call_args
        self.assertAlmostEqual(args[2].value, 0.7)

    def test_set_volume_int(self):
        player = AudioPlayer(volume=0.0)
        player.current_channel = 1
        player.set_volume(75) # Should be converted to 0.75
        self.assertAlmostEqual(player.volume, 0.75)
        args, _ = mock_bass_module_object.BASS_ChannelSetAttribute.call_args
        self.assertAlmostEqual(args[2].value, 0.75)

    def test_set_volume_clamping_high(self):
        player = AudioPlayer(volume=0.0)
        player.current_channel = 1
        player.set_volume(1.5)
        self.assertAlmostEqual(player.volume, 1.0)
        args, _ = mock_bass_module_object.BASS_ChannelSetAttribute.call_args
        self.assertAlmostEqual(args[2].value, 1.0)

    def test_set_volume_clamping_low(self):
        player = AudioPlayer(volume=0.0)
        player.current_channel = 1
        player.set_volume(-0.5)
        self.assertAlmostEqual(player.volume, 0.0)
        args, _ = mock_bass_module_object.BASS_ChannelSetAttribute.call_args
        self.assertAlmostEqual(args[2].value, 0.0)
        
    def test_set_volume_no_channel(self):
        player = AudioPlayer(volume=0.5)
        player.set_volume(0.8) # Set volume property
        self.assertAlmostEqual(player.volume, 0.8)
        mock_bass_module_object.BASS_ChannelSetAttribute.assert_not_called() # No channel to set on

    def test_increase_volume(self):
        player = AudioPlayer(volume=0.5)
        player.current_channel = 1
        with patch.object(player, 'set_volume', wraps=player.set_volume) as mock_set_vol:
            player.increase_volume(0.2) # Increase by 0.2
            mock_set_vol.assert_called_once_with(0.7)
        self.assertAlmostEqual(player.volume, 0.7)

    def test_decrease_volume(self):
        player = AudioPlayer(volume=0.5)
        player.current_channel = 1
        with patch.object(player, 'set_volume', wraps=player.set_volume) as mock_set_vol:
            player.decrease_volume(0.2) # Decrease by 0.2
            mock_set_vol.assert_called_once_with(0.3)
        self.assertAlmostEqual(player.volume, 0.3)

    # --- 5. Position Control ---
    def test_set_position_success(self):
        player = AudioPlayer(volume=0.5)
        player.current_channel = 1
        mock_bass_module_object.BASS_ChannelSeconds2Bytes.return_value = 12345 # Mock byte position
        mock_bass_module_object.BASS_ChannelSetPosition.return_value = True # Mock success
        
        with patch.object(player, 'get_length', return_value=60.0): # Duration of 60s
            result = player.set_position(30.0)

        self.assertTrue(result)
        mock_bass_module_object.BASS_ChannelSeconds2Bytes.assert_called_once_with(1, 30.0)
        mock_bass_module_object.BASS_ChannelSetPosition.assert_called_once_with(1, 12345, 0) # mode 0

    def test_set_position_clamping_low(self):
        player = AudioPlayer(volume=0.5)
        player.current_channel = 1
        with patch.object(player, 'get_length', return_value=60.0):
            player.set_position(-10.0) # Should be clamped to 0.0
        mock_bass_module_object.BASS_ChannelSeconds2Bytes.assert_called_once_with(1, 0.0)

    def test_set_position_clamping_high(self):
        player = AudioPlayer(volume=0.5)
        player.current_channel = 1
        with patch.object(player, 'get_length', return_value=60.0) as mock_get_len:
            player.set_position(70.0) # Should be clamped to duration - 1 (59.0)
        mock_bass_module_object.BASS_ChannelSeconds2Bytes.assert_called_once_with(1, 59.0)

    def test_set_position_no_channel(self):
        player = AudioPlayer(volume=0.5)
        player.set_position(10.0) # Should not error, no BASS calls
        mock_bass_module_object.BASS_ChannelSeconds2Bytes.assert_not_called()
        mock_bass_module_object.BASS_ChannelSetPosition.assert_not_called()

    def test_forward_success(self):
        player = AudioPlayer(volume=0.5)
        player.current_channel = 1
        with patch.object(player, 'get_position', return_value=20.0) as mock_get_pos, \
             patch.object(player, 'set_position') as mock_set_pos:
            player.forward(10) # Forward 10 seconds
            mock_get_pos.assert_called_once()
            mock_set_pos.assert_called_once_with(30.0) # 20 + 10

    def test_rewind_success(self):
        player = AudioPlayer(volume=0.5)
        player.current_channel = 1
        with patch.object(player, 'get_position', return_value=20.0) as mock_get_pos, \
             patch.object(player, 'set_position') as mock_set_pos:
            player.rewind(10) # Rewind 10 seconds
            mock_get_pos.assert_called_once()
            mock_set_pos.assert_called_once_with(10.0) # 20 - 10

    # --- 6. Information Retrieval ---
    def test_get_length_success(self):
        player = AudioPlayer(volume=0.5)
        player.current_channel = 1
        mock_bass_module_object.BASS_ChannelGetLength.return_value = 88200 # Mock byte length
        mock_bass_module_object.BASS_ChannelBytes2Seconds.return_value = 44.1 # Mock duration
        
        length = player.get_length()
        self.assertAlmostEqual(length, 44.1)
        mock_bass_module_object.BASS_ChannelGetLength.assert_called_once_with(1, 0) # mode 0
        mock_bass_module_object.BASS_ChannelBytes2Seconds.assert_called_once_with(1, 88200)

    def test_get_length_no_channel(self):
        player = AudioPlayer(volume=0.5)
        self.assertEqual(player.get_length(), 0)

    def test_get_position_success(self):
        player = AudioPlayer(volume=0.5)
        player.current_channel = 1
        mock_bass_module_object.BASS_ChannelGetPosition.return_value = 44100 # Mock byte position
        mock_bass_module_object.BASS_ChannelBytes2Seconds.return_value = 22.05 # Mock seconds
        
        position = player.get_position()
        self.assertAlmostEqual(position, 22.05)
        mock_bass_module_object.BASS_ChannelGetPosition.assert_called_once_with(1, 0) # mode 0
        mock_bass_module_object.BASS_ChannelBytes2Seconds.assert_called_once_with(1, 44100)

    def test_get_position_no_channel(self):
        player = AudioPlayer(volume=0.5)
        self.assertEqual(player.get_position(), 0)

    def test_get_playback_status(self):
        player = AudioPlayer(volume=0.5)
        
        # No channel
        self.assertEqual(player.get_playback_status(), PlaybackStatus.STOPPED)

        player.current_channel = 1
        
        mock_bass_module_object.BASS_ChannelIsActive.return_value = BASS_ACTIVE_PLAYING
        self.assertEqual(player.get_playback_status(), PlaybackStatus.PLAYING)
        
        mock_bass_module_object.BASS_ChannelIsActive.return_value = BASS_ACTIVE_PAUSED
        self.assertEqual(player.get_playback_status(), PlaybackStatus.PAUSED)

        mock_bass_module_object.BASS_ChannelIsActive.return_value = BASS_ACTIVE_STALLED
        self.assertEqual(player.get_playback_status(), PlaybackStatus.STALLED)
        
        mock_bass_module_object.BASS_ChannelIsActive.return_value = BASS_ACTIVE_STOPPED # Or any other value
        self.assertEqual(player.get_playback_status(), PlaybackStatus.STOPPED)

    def test_is_playing_paused_stalled_stopped(self):
        player = AudioPlayer(volume=0.5)
        player.current_channel = 1

        with patch.object(player, 'get_playback_status') as mock_get_status:
            mock_get_status.return_value = PlaybackStatus.PLAYING
            self.assertTrue(player.is_playing())
            self.assertFalse(player.is_paused())

            mock_get_status.return_value = PlaybackStatus.PAUSED
            self.assertTrue(player.is_paused())
            self.assertFalse(player.is_stalled())

            mock_get_status.return_value = PlaybackStatus.STALLED
            self.assertTrue(player.is_stalled())
            self.assertFalse(player.is_stopped())
            
            mock_get_status.return_value = PlaybackStatus.STOPPED
            self.assertTrue(player.is_stopped())
            self.assertFalse(player.is_playing())


    def test_get_error(self):
        player = AudioPlayer(volume=0.5)
        mock_bass_module_object.BASS_ErrorGetCode.return_value = 5 # Example error code
        self.assertEqual(player.get_error(), 5)
        mock_bass_module_object.BASS_ErrorGetCode.assert_called_once()

if __name__ == '__main__':
    unittest.main()
