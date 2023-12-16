# absync

This tool can be used to sync an audiobook from audiobookshelf to an mp3 player.
It is designed for actual hardware mp3 players without support for different
file formats, so it will transcode the tracks.
Also it is designed for mp3 players without a display, so it will add a TTS
comment with the track number to the begin of each track.

This tool will get the current progress of your last listened audiobook
from audiobookshelf and only sync the progress beginning with that position.
It will sync the next 3600 seconds of audio (configurable via sync/duration).

On each sync, the already listened files (according to the play position on the server)
will get deleted.
Files that are already present on the player (but not listened yet) won't need to be resynced.

Note that there is no way of sending back the playback position to the server,
Unless the MP3 player might store some metadate that could be utilized in the future.
Until then, you will need to use the TTS track markers to manually skip forward in
audiobookshelf.
