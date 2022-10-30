from enum import Enum


class PostTypes(Enum):
    POST = "post"
    ARTIST_POST_COMMENT = "artist_post_comment"
    USER_POST_COMMENT = "user_post_comment"
    MEDIA_COMMENT = "media_comment"
    MOMENT_COMMENT = "moment_comment"
    MOMENT = "moment"
    LIVE = "live"
    NOTICE = "notice"
    MEDIA = "media"
    BIRTHDAY = "birthday"

    def __repr__(self):
        return self.value


class ObjectTypes(Enum):
    COMMUNITY = "community"
    ARTIST = "artist"
    NOTIFICATION = "notification"
    POST = "post"
    MEDIA = "media"
    IMAGE_MEDIA = "image_media"
    WEVERSE_MEDIA = "weverse_media"
    YOUTUBE_MEDIA = "youtube_media"
    LIVE = "live"
    MOMENT = "moment"
    NEW_MOMENT = "new_moment"
    OLD_MOMENT = "old_moment"
    NOTICE = "notice"
    MEMBER = "member"
    COMMENT = "comment"

    def __repr__(self):
        return self.value
