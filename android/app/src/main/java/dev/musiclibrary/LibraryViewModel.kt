package dev.musiclibrary

import android.content.ComponentName
import android.content.Context
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.media3.common.MediaItem
import androidx.media3.common.MediaMetadata
import androidx.media3.common.Player
import androidx.media3.session.MediaController
import androidx.media3.session.SessionToken
import com.google.common.util.concurrent.ListenableFuture
import com.google.common.util.concurrent.MoreExecutors
import dev.musiclibrary.data.Track
import dev.musiclibrary.data.TrackRepository
import dev.musiclibrary.player.PlaybackService
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class LibraryUiState(
    val tracks: List<Track> = emptyList(),
    val isLoading: Boolean = true,
    val currentTrack: Track? = null,
    val isPlaying: Boolean = false,
    val playerReady: Boolean = false,
)

class LibraryViewModel : ViewModel() {
    private val repository = TrackRepository()
    private var appContext: Context? = null
    private var controllerFuture: ListenableFuture<MediaController>? = null
    private var mediaController: MediaController? = null

    private val _uiState = MutableStateFlow(LibraryUiState())
    val uiState: StateFlow<LibraryUiState> = _uiState.asStateFlow()

    private val playerListener = object : Player.Listener {
        override fun onIsPlayingChanged(isPlaying: Boolean) {
            _uiState.update { it.copy(isPlaying = isPlaying) }
        }

        override fun onMediaItemTransition(mediaItem: MediaItem?, reason: Int) {
            syncCurrentTrack()
        }

        override fun onPlaybackStateChanged(playbackState: Int) {
            syncCurrentTrack()
        }
    }

    fun bindPlayer(context: Context) {
        appContext = context.applicationContext
    }

    fun connectPlayer(context: Context) {
        if (controllerFuture != null) {
            return
        }
        val token = SessionToken(context, ComponentName(context, PlaybackService::class.java))
        controllerFuture = MediaController.Builder(context, token).buildAsync()
        controllerFuture?.addListener(
            {
                mediaController = controllerFuture?.get()
                mediaController?.addListener(playerListener)
                _uiState.update { it.copy(playerReady = true) }
                syncCurrentTrack()
            },
            MoreExecutors.directExecutor(),
        )
    }

    fun disconnectPlayer() {
        mediaController?.removeListener(playerListener)
        controllerFuture?.let { MediaController.releaseFuture(it) }
        controllerFuture = null
        mediaController = null
        _uiState.update { it.copy(playerReady = false, isPlaying = false) }
    }

    fun loadTracks(context: Context) {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = true) }
            val tracks = repository.loadTracks(context)
            _uiState.update { it.copy(tracks = tracks, isLoading = false) }
        }
    }

    fun playTrack(track: Track) {
        val controller = mediaController ?: return
        val items = _uiState.value.tracks.map { it.toMediaItem() }
        val index = _uiState.value.tracks.indexOfFirst { it.id == track.id }.coerceAtLeast(0)
        controller.setMediaItems(items, index, 0L)
        controller.prepare()
        controller.play()
        _uiState.update { it.copy(currentTrack = track, isPlaying = true) }
    }

    fun togglePlayPause() {
        val controller = mediaController ?: return
        if (controller.isPlaying) {
            controller.pause()
        } else {
            if (controller.mediaItemCount == 0 && _uiState.value.tracks.isNotEmpty()) {
                playTrack(_uiState.value.tracks.first())
            } else {
                controller.play()
            }
        }
    }

    private fun syncCurrentTrack() {
        val controller = mediaController ?: return
        val index = controller.currentMediaItemIndex
        val tracks = _uiState.value.tracks
        val current = tracks.getOrNull(index)
        _uiState.update {
            it.copy(
                currentTrack = current,
                isPlaying = controller.isPlaying,
            )
        }
    }
}

private fun Track.toMediaItem(): MediaItem {
    return MediaItem.Builder()
        .setUri(uri)
        .setMediaId(id.toString())
        .setMediaMetadata(
            MediaMetadata.Builder()
                .setTitle(title)
                .setArtist(artist)
                .setAlbumTitle(album)
                .build(),
        )
        .build()
}
