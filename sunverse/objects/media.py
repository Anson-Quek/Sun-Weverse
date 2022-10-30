from typing import Optional

from sunverse.objects.attachments import Photo
from sunverse.objects.post import Postlike


class Medialike(Postlike):
    """Represents a Weverse Media.

    Inherits from :class:`sunverse.objects.Postlike`.

    Shares the same attributes with :class:`sunverse.objects.Postlike`.

    Inherited by:

    - :class:`sunverse.objects.ImageMedia`
    - :class:`sunverse.objects.YoutubeMedia`
    - :class:`sunverse.objects.WeverseMedia`
    - :class:`sunverse.objects.Live`

    .. container:: operations

        .. describe:: str(x)

            Returns the media's title.

    Attributes
    ----------
    title: :class:`str`
        The title of the media.
    thumbnail_url: :class:`str`
        The URL of the thumbnail of the media.
    """

    __slots__ = ("title", "thumbnail_url")

    def __init__(self, data: dict):
        super().__init__(data)
        self.title: str = data["title"]
        self.thumbnail_url: str = data["extension"]["mediaInfo"]["thumbnail"]["url"]

    def __repr__(self):
        return f"Media media_id={self.id}, title={self.title}"

    def __str__(self):
        return self.title


class ImageMedia(Medialike):
    """Represents a Weverse Media that contains images.

    Inherits from :class:`sunverse.objects.Medialike`.

    Shares the same attributes with :class:`sunverse.objects.Postlike` and
    :class:`sunverse.objects.Medialike`.
    """

    @property
    def photos(self) -> list[Photo]:
        """list[:class:`sunverse.objects.Photo`]: A list of
        :class:`sunverse.objects.Photo` objects in the media.
        """
        return [
            Photo(photo_data)
            for photo_data in self.data["extension"]["image"]["photos"]
        ]


class YoutubeMedia(Medialike):
    """Represents a Weverse Media that contains a YouTube video.

    Inherits from :class:`sunverse.objects.Medialike`.

    Shares the same attributes with :class:`sunverse.objects.Postlike` and
    :class:`sunverse.objects.Medialike`.

    Attributes
    ----------
    video_duration: :class:`int`
        The duration of the YouTube video, in seconds.
    youtube_url: :class:`str`
        The URL to the YouTube video.
    video_screen_orientation: :class:`str`
        The screen orientation of the video.
    """

    __slots__ = ("video_duration", "youtube_url", "video_screen_orientation")

    def __init__(self, data: dict):
        super().__init__(data)
        self.video_duration: int = data["extension"]["youtube"]["playTime"]
        self.youtube_url: str = data["extension"]["youtube"]["videoPath"]
        self.video_screen_orientation: str = data["extension"]["youtube"][
            "screenOrientation"
        ]


class WeverseMedia(Medialike):
    """Represents a Weverse Media that contains a Weverse video.

    Inherits from :class:`sunverse.objects.Medialike`.

    Shares the same attributes with :class:`sunverse.objects.Postlike` and
    :class:`sunverse.objects.Medialike`.

    Inherited by:

    - :class:`sunverse.objects.Live`

    Attributes
    ----------
    video_id: :class:`int`
        The ID of the Weverse video.
    internal_video_id: Optional[:class:`str`]
        The internal ID of the Weverse video. Returns `None`
        in the case of a live broadcast that is still broadcasting and not
        converted into a VOD yet.
    video_type: :class:`str`
        The type of Weverse video.
    aired_at: :class:`int`
        The time the Weverse video got aired at, in epoch time.
    paid_video: :class:`bool`
        Whether the Weverse video is a paid video.
    membership_only_video: :class:`bool`
        Whether the Weverse video is only accessible by users with a membership.
    video_screen_orientation: :class:`str`
        The screen orientation of the video.
    video_play_count: :class:`int`
        The number of views on the Weverse video.
    video_like_count: :class:`int`
        The number of likes on the Weverse video.
    video_duration: Optional[:class:`int`]
        The duration of the Weverse video, in seconds. Returns `None`
        in the case of a live broadcast that is still broadcasting and not
        converted into a VOD yet.
    """

    __slots__ = (
        "video_id",
        "internal_video_id",
        "video_type",
        "aired_at",
        "paid_video",
        "membership_only_video",
        "video_screen_orientation",
        "video_play_count",
        "video_like_count",
        "video_duration",
    )

    def __init__(self, data: dict):
        super().__init__(data)
        self.video_id: int = data["extension"]["video"]["videoId"]
        self.internal_video_id: Optional[str] = data["extension"]["video"].get(
            "infraVideoId"
        )
        self.video_type: str = data["extension"]["video"]["type"]
        self.aired_at: int = data["extension"]["video"]["onAirStartAt"]
        self.paid_video: bool = data["extension"]["video"]["paid"]
        self.membership_only_video: bool = data["extension"]["video"]["membershipOnly"]
        self.video_screen_orientation: str = data["extension"]["video"][
            "screenOrientation"
        ]
        self.video_play_count: int = data["extension"]["video"]["playCount"]
        self.video_like_count: int = data["extension"]["video"]["likeCount"]
        self.video_duration: Optional[int] = data["extension"]["video"].get("playTime")
