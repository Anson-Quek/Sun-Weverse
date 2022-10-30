import base64
import hmac
import time
import urllib.parse
from hashlib import sha1

WEVERSE_KEY = "1b9cb6378d959b45714bec49971ade22e6e24e42"


def get_current_epoch_time() -> int:
    """Returns the current epoch time in milli seconds."""
    return int(time.time() * 1000)


def generate_message_digest(message: bytes) -> str:
    """Generates the message digest for Weverse.

    Parameters
    ----------
    message: :class:`bytes`
        The message to generate the digest for, in bytes.

    Returns
    -------
    :class:`str`
        The message digest made URL-compatible.
    """
    key = bytes(WEVERSE_KEY, "utf-8")
    hashed = hmac.new(key=key, msg=message, digestmod=sha1)
    message_digest = base64.b64encode(hashed.digest())
    return urllib.parse.quote_plus(message_digest)


class URLHandler:
    def __init__(self):
        self.login_url = (
            "https://accountapi.weverse.io/web/api/v2/auth/token/by-credentials"
        )
        self._base_url = "https://global.apis.naver.com/weverse/wevweb"
        self._parameters = (
            "?appId=be4d79eb8fc7bd008ee82c8ec4ff6fd4&language=en&platform=WEB&wpf=pc"
        )

    def _form_request_url(self, url: str) -> str:
        indexed_url = url[0:255]
        epoch_time = get_current_epoch_time()

        url_with_epoch = f"{indexed_url}{epoch_time}".encode("utf-8")

        message_digest = generate_message_digest(url_with_epoch)
        return f"{self._base_url}{url}&wmsgpad={epoch_time}&wmd={message_digest}"

    def joined_communities_url(self) -> str:
        """The endpoint for fetching the data from Weverse
        that contains the communities the user have joined.
        """
        url = "/noti/feed/v1.0/activities/community" + self._parameters
        return self._form_request_url(url)

    def community_url(self, community_id: int) -> str:
        """The endpoint for fetching the data of a specified Community from Weverse."""
        url = (
            f"/community/v1.0/community-{community_id}"
            + self._parameters
            + "&fieldSet=communityHomeV1"
        )
        return self._form_request_url(url)

    def artists_url(self, community_id: int) -> str:
        """The endpoint for fetching the data of the artists of a specified Community
        from Weverse."""
        url = (
            f"/member/v1.0/community-{community_id}/artistMembers"
            + self._parameters
            + "&fieldSet=artistMembersV1&fields=communityId"
            "%2CjoinedDate%2CprofileName%2CprofileImageUrl"
            "%2CprofileCoverImageUrl%2CprofileComment"
        )
        return self._form_request_url(url)

    def latest_notifications_url(self) -> str:
        """The endpoint for fetching the data of the latest notifications
        from Weverse."""
        url = "/noti/feed/v1.0/activities" + self._parameters
        return self._form_request_url(url)

    def notification_url(self, notification_id: int) -> str:
        """The endpoint for fetching the data of a specified Notification
        from Weverse."""
        url = (
            "/noti/feed/v1.0/activities"
            + self._parameters
            + f"&next={notification_id+1}"
        )
        return self._form_request_url(url)

    def post_url(self, post_id: str) -> str:
        """The endpoint for fetching the data of a specified Post from Weverse."""
        url = f"/post/v1.0/post-{post_id}" + self._parameters + "&fieldSet=postV1"
        return self._form_request_url(url)

    def latest_fan_posts_url(self, community_id: int) -> str:
        """The endpoint for fetching the data of the latest fan posts
        from Weverse."""
        url = (
            f"/post/v1.0/community-{community_id}/feedTab"
            + self._parameters
            + "&fields=feedTabPosts.fieldSet%28postsV1%29.limit%2820%29%2CcontentSlots."
            "fieldSet%28contentSlotV1%29&platform=WEB"
        )
        return self._form_request_url(url)

    def video_url(self, video_id: str) -> str:
        """The endpoint for fetching the URL of videos from Weverse."""
        url = f"/cvideo/v1.0/cvideo-{video_id}/downloadInfo" + self._parameters
        return self._form_request_url(url)

    def notice_url(self, notice_id: int) -> str:
        """The endpoint for fetching the data of a specified Notice from Weverse."""
        url = (
            f"/notice/v1.0/notice-{notice_id}" + self._parameters + "&fieldSet=noticeV1"
        )
        return self._form_request_url(url)

    def member_url(self, member_id: str) -> str:
        """The endpoint for fetching the data of a specified Member from Weverse."""
        url = (
            f"/member/v1.0/member-{member_id}"
            + self._parameters
            + "&fields=memberId%2CcommunityId%2Cjoined%2CjoinedDate%2CprofileType"
            "%2CprofileName%2CprofileImageUrl%2CprofileCoverImageUrl%2CprofileComment"
            "%2Chidden%2Cblinded%2CmemberJoinStatus%2CfollowCount"
            "%2ChasMembership%2ChasOfficialMark"
        )
        return self._form_request_url(url)

    def artist_comments_url(self, post_id: str) -> str:
        """The endpoint for fetching the data of the artist comments on a
        specified post from Weverse."""
        url = (
            f"/comment/v1.0/post-{post_id}/artistComments"
            + self._parameters
            + "&fieldSet=postArtistCommentsV1"
        )
        return self._form_request_url(url)

    def comment_url(self, comment_id: str) -> str:
        """The endpoint for fetching the data of a specified Comment from Weverse."""
        url = (
            f"/comment/v1.0/comment-{comment_id}"
            + self._parameters
            + "&fieldSet=commentV1"
        )
        return self._form_request_url(url)
