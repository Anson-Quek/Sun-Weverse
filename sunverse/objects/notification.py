import re
from typing import Optional

from sunverse.enums import PostTypes


class Notification:
    """Represents a Weverse Notification.

    .. container:: operations

        .. describe:: x == y

            Checks if two notifications are equal.

        .. describe:: x != y

            Checks if two notifications are not equal.

        .. describe:: hash(x)

            Returns the notification's hash.

        .. describe:: str(x)

            Returns the notification's message.

    Attributes
    ----------
    data: :class:`dict`
        The raw data directly taken from the response generated by Weverse's API.
    id: :class:`int`
        The ID of the notification.
    is_read: :class:`bool`
        Whether the user has read the notification.
    title: :class:`str`
        Usually the name of the group the notification belongs to.
        However, if it's an admin notification, it would be a proper title.
    message_ko: :class:`str`
        The message of the notification in Korean.
    message_ja: :class:`str`
        The message of the notification in Japanese.
    message_en: :class:`str`
        The message of the notification in English.
    logo_image_url: :class:`str`
        The URL to the logo image of the artist profile
        picture displayed on the notification.
    image_url: Optional[:class:`str`]
        The URL to the preview image displayed on the notification, if any.
    web_url: :class:`str`
        The URL that leads to the actual post.
    time_created: :class:`int`
        The time the notification got created at, in epoch.
    count: :class:`int`
        The number of artist comments on the post the notification
        leads to.
    community_id: :class:`int`
        The community ID of the community the notification belongs to.
        This can be used to fetch the actual :class:`sunverse.objects.Community`
        object if needed using the :method:`fetch_community` method.
    """

    __slots__ = (
        "data",
        "id",
        "is_read",
        "title",
        "message_ko",
        "message_ja",
        "message_en",
        "logo_image_url",
        "image_url",
        "web_url",
        "time_created",
        "count",
        "community_id",
    )

    def __init__(self, data: dict):
        self.data: dict = data
        self.id: int = data["activityId"]
        self.is_read: bool = data["read"]
        self.title: str = data["title"]
        self.message_ko: str = data["message"]["values"]["ko"]
        self.message_ja: str = data["message"]["values"]["ja"]
        self.message_en: str = data["message"]["values"]["en"]
        self.logo_image_url: str = data["logoImageUrl"]
        self.image_url: Optional[str] = data.get("imageUrl")
        self.web_url: str = data["webUrl"]
        self.time_created: int = data["time"]
        self.count: int = data["count"]
        self.community_id: int = data["community"]["communityId"]

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.id == other.id

        raise NotImplementedError

    def __repr__(self):
        return f"Notification notification_id={self.id}, message={self.message_en}"

    def __str__(self):
        return self.message_en

    def __hash__(self):
        return hash(self.id)

    @property
    def post_id(self) -> str:
        """:class:`str`: Returns the post ID of the post the notification leads to."""
        pattern = re.compile(r"([\d]-\d+)")
        match = re.search(pattern, self.data["messageId"])

        if not match:  # This happens when the notification type is Notice.
            match = re.search(r"\d+", self.data["messageId"])

        return match.group(0)

    @property
    def post_type(self) -> str:
        """:class:`str`: Returns the post type of the post the notification
        leads to.
        """
        post_types = {
            "T_FEED_COMMENT": PostTypes.USER_POST_COMMENT,
            "ST_FEED_COMMENT": PostTypes.USER_POST_COMMENT,
            "_MEDIA_COMMENT": PostTypes.MEDIA_COMMENT,
            "_MOMENT_COMMENT": PostTypes.MOMENT_COMMENT,
            "MOMENT_COMMENT": PostTypes.MOMENT_COMMENT,
            "ARTIST_COMMENT": PostTypes.ARTIST_POST_COMMENT,
            "ARTIST_POST": PostTypes.POST,
            "ARTIST_MOMENT": PostTypes.MOMENT,
            "ARTIST_LIVE_ON_AIR": PostTypes.LIVE,
            "COMMUNITY_MEDIA": PostTypes.MEDIA,
            "NOTICE": PostTypes.NOTICE,
            "COMMUNITY_ANNIVERSARY": PostTypes.BIRTHDAY,
        }

        for key, value in post_types.items():
            if key in self.data["messageId"]:
                return value

        return "NOT IMPLEMENTED"

    @property
    def author_id(self) -> Optional[str]:
        """Optional[:class:`str`]: Returns the artist ID of the artist who
        created the post the notification leads to.

        Will always return `None` for posts that are not
        comment-related. This can be used together with the
        :method:`fetch_artists` method to fetch the dictionary that contains
        the :class:`sunverse.objects.Artist` objects, and then accessing the
        specific artist object using this author ID as the key.
        """
        if self.data.get("authors"):
            return self.data["authors"][0]["memberId"]

        return None
