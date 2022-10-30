from typing import Optional
from sunverse.objects.attachments import Photo, Video
from sunverse.objects.post import Postlike


class Momentlike(Postlike):
    """Represents a Weverse Moment-Like Object.

    Inherits from :class:`sunverse.objects.Postlike`.

    Shares the same attributes with :class:`sunverse.objects.Postlike`.

    Inherited by:

    - :class:`sunverse.objects.Moment`
    - :class:`sunverse.objects.OldMoment`

    .. container:: operations

        .. describe:: str(x)

            Returns the moment's plain body.

    Attributes
    ----------
    expire_at: :class:`int`
        The time the moment expires at, in epoch.
    """

    __slots__ = ("expire_at",)

    def __init__(self, data: dict):
        super().__init__(data)

        if "moment" in data["extension"]:
            self.expire_at: int = data["extension"]["moment"]["expireAt"]

        else:
            self.expire_at: int = data["extension"]["momentW1"]["expireAt"]

    def __repr__(self):
        return f"Moment moment_id={self.id}, plain_body={self.plain_body}"

    def __str__(self):
        return self.plain_body


class Moment(Momentlike):
    """Represents a Weverse Moment that has been created after their rework.

    Inherits from :class:`sunverse.objects.Momentlike`.

    Shares the same attributes with :class:`sunverse.objects.Postlike` and
    :class:`sunverse.objects.Moment`.

    Attributes
    ----------
    video: :class:`sunverse.objects.Video`
        The :class:`sunverse.objects.Video` object of the video in the moment.
    """

    __slots__ = ("video",)

    def __init__(self, data: dict):
        super().__init__(data)
        self.video: Video = Video(data["extension"]["moment"]["video"])


class OldMoment(Momentlike):
    """Represents a Weverse Moment that has been created before their rework.

    Inherits from :class:`sunverse.objects.Momentlike`.

    Shares the same attributes with :class:`sunverse.objects.Postlike` and
    :class:`sunverse.objects.Moment`.

    Attributes
    ----------
    photo: Optional[:class:`sunverse.objects.Photo`]
        The :class:`sunverse.objects.Photo` object of the photo in the moment,
        if the image used in the moment is not a default Weverse background image.
    background_image_url: Optional[:class:`str`]
        The URL of the default Weverse background image if it is used.
    """

    __slots__ = ("photo", "background_image_url")

    def __init__(self, data: dict):
        super().__init__(data)
        self.photo: Optional[Photo] = (
            Photo(data["extension"]["momentW1"]["photo"])
            if "photo" in data["extension"]["momentW1"]
            else None
        )
        self.background_image_url: Optional[str] = (
            data["extension"]["momentW1"]["backgroundImageUrl"]
            if "backgroundImageUrl" in data["extension"]["momentW1"]
            else None
        )
