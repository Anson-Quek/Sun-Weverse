import asyncio
import logging

from aiohttp import (
    ClientConnectionError,
    ClientResponse,
    ClientSession,
)
from yarl import URL

from sunverse.objects.notification import Notification

from .enums import ObjectTypes, PostTypes
from .errors import InternalServerError, LoginError, NotFound, RequestFailed
from .objects.artist import Artist
from .objects.comment import Comment
from .objects.community import Community
from .objects.live import Live
from .objects.media import ImageMedia, WeverseMedia, YoutubeMedia
from .objects.member import Member
from .objects.moment import Moment, OldMoment
from .objects.notice import Notice
from .objects.post import Post
from .utils.urls import URLHandler, get_current_epoch_time
from .utils.utilities import MISSING

_LOGIN_HEADERS = {
    "content-type": "application/json",
    "x-acc-app-secret": "5419526f1c624b38b10787e5c10b2a7a",
    "x-acc-app-version": "abc",
    "x-acc-language": "en",
    "x-acc-service-id": "weverse",
    "x-acc-trace-id": "abc",
}

logger = logging.getLogger(__name__)


class SunverseClient:
    """Represents the client connection to Weverse."""

    def __init__(
        self,
        email: str,
        password: str,
        stream_delay: float = 20,
    ):
        self.email: str = email
        self.password: str = password
        self.stream_delay: float = stream_delay

        self._access_token: str = MISSING
        self._urls: URLHandler = URLHandler()
        self._cache: _SunverseCache = _SunverseCache()

        self.__task: asyncio.Task = MISSING
        self.__fetch_delay: float = 0.25

    @property
    def login_payload(self) -> dict:
        """:class:`dict`: Returns the login payload used to login to Weverse."""
        return {"email": self.email, "password": self.password}

    @property
    def api_headers(self) -> dict:
        """:class:`dict`: Returns the API headers used to communicate with Weverse."""
        return {
            "referer": "https://weverse.io",
            "authorization": f"Bearer {self._access_token}",
        }

    async def _fetch_access_token_by_credentials(self) -> None:
        """Fetches and stores the access token using the credentials
        provided by the user. This access token is essential in
        interacting with the Weverse API when pulling data from it.

        Raises
        ------
        ~sunverse.LoginError
            Unable to login successfully.
        """
        async with ClientSession() as client, client.post(
            self._urls.login_url, headers=_LOGIN_HEADERS, json=self.login_payload
        ) as resp:
            if resp.status != 200:
                raise LoginError(resp.status, (await resp.json()).get("message"))

            data = await resp.json()
            self._access_token = data["accessToken"]
            logger.debug(
                "LOGIN SUCCESSFUL\nData: %s\nAccess Token: %s", data, self._access_token
            )

    async def _fetcher(self, url: str) -> dict:
        """Fetches the data from the specified URL provided by the user.

        Parameters
        ----------
        url: :class:`str`
            The URL to fetch the data from.

        Returns
        -------
        :class:`dict`
            A dictionary that contains the raw data of the response provided by
            the Weverse API.
        """
        try:
            async with ClientSession() as sess, sess.get(
                URL(url, encoded=True), headers=self.api_headers
            ) as resp:
                await self._check_response_status(resp)
                return await resp.json()

        except (asyncio.exceptions.TimeoutError, ClientConnectionError):
            logger.warning(
                "CLIENT CONNECTION ERROR IGNORED SILENTLY. "
                "RETRYING TO RETURN REQUESTED RESOURCE."
            )
            return await self._fetcher(url)

        except InternalServerError:
            logger.warning(
                "WEVERSE API ENCOUNTERED TEMPORARY INTERNAL SERVER ERROR. "
                "RETRYING TO RETURN REQUESTED RESOURCE."
            )
            return await self._fetcher(url)

    async def _check_response_status(self, resp: ClientResponse) -> None:
        """Checks the HTTP status code for the response received from Weverse's API.

        Also automatically updates the access token if it is suspected to be
        expired.

        Raises
        ------
        ~sunverse.RequestFailed
            The request failed to get an "OK" or 200 response from the Weverse API.
        ~sunverse.NotFound
            The request received a "NOT FOUND" or 404 response from the Weverse API.
        """
        if resp.status == 401:  # This usually means that the access token is expired.
            return await self._fetch_access_token_by_credentials()

        if resp.status == 404:
            raise NotFound(resp.url)

        if resp.status == 500:
            raise InternalServerError(resp.url)

        if resp.status != 200:  # Raises this exception if other HTTP codes encountered.
            raise RequestFailed(resp.url, resp.status, await resp.text("utf-8"))

    async def _object_creator(self, object_type: str, data: dict, retry_url: str):
        """Responsible for creating all the Sunverse Objects based on the
        specified object type.

        Parameters
        ----------
        object_type: :class:`str`
            The type of Sunverse Object to create.
        data: :class:`dict`
            The raw data used for the Sunverse Object's creation.
        retry_url: :class:`str`
            The URL that will be used when retrying due to potentially
            incomplete data provided by the Weverse API.

        Returns
        -------
        :module:`sunverse.objects`
            The Sunverse Objects that are contained in the
            :module:`sunverse.objects` module.

        Notes
        -----
        In an attempt to ensure the data received from the Weverse API is complete,
        this method will also attempt to retry fetching the data from Weverse up to
        3 times should the Sunverse Object creation fail. This is because the Sunverse
        Objects have been tailored to ensure that the data received from the
        Weverse API is complete. As such, if :exception:`KeyError` is encountered
        for whatever reason, it would mean that the data provided by the Weverse API
        is incomplete, and should be retried in an attempt to receive complete data.
        """
        retry_count = 0
        max_retries = 3
        object_mapping = {
            ObjectTypes.COMMUNITY: Community,
            ObjectTypes.ARTIST: Artist,
            ObjectTypes.NOTIFICATION: Notification,
            ObjectTypes.POST: Post,
            ObjectTypes.IMAGE_MEDIA: ImageMedia,
            ObjectTypes.WEVERSE_MEDIA: WeverseMedia,
            ObjectTypes.YOUTUBE_MEDIA: YoutubeMedia,
            ObjectTypes.LIVE: Live,
            ObjectTypes.NEW_MOMENT: Moment,
            ObjectTypes.OLD_MOMENT: OldMoment,
            ObjectTypes.NOTICE: Notice,
            ObjectTypes.MEMBER: Member,
            ObjectTypes.COMMENT: Comment,
        }

        while retry_count < max_retries:
            try:
                # It's basically doing something like Community(data)
                sunverse_object = object_mapping[object_type](data)
                return sunverse_object

            except KeyError:
                data = await self._fetcher(retry_url)
                retry_count += 1

    def _log(self, names_tuple: tuple[str], data: dict, sunverse_object) -> None:
        """A general logger that logs debug fetching messages."""
        first_name, second_name = names_tuple
        logger.debug(
            "%s FETCHED\nData: %s\n%s: %s",
            first_name,
            data,
            second_name,
            sunverse_object,
        )

    async def fetch_new_notification(self) -> tuple[list[Notification], list[Comment]]:
        """Fetches the list of new Weverse Notifications from all
        communities that the signed-in account has access to.

        Returns
        -------
        :class:`list[sunverse.objects.Notification]`:
            A list of :class:`sunverse.objects.Notification` objects the
            signed-in account has access to.

        tuple[list[:class:`sunverse.objects.Notification`],
        list[:class:`sunverse.objects.Comment`]]
            A tuple that contains a list of new :class:`sunverse.objects.Notification`
            objects and a list of new :class:`sunverse.objects.Comment` objects.

        Notes
        -----
        The reason why :class:`sunverse.objects.Comment` objects are returned for
        comment-related notifications and not :class:`sunverse.objects.Notification`
        objects is because Weverse does not provide an easy way to determine which
        comment-related notifications are new. As such, in the post-processing of
        comment-related notifications, the actual :class:`sunverse.objects.Comment`
        objects have to be fetched so that we know which comments are new.
        """
        old_non_comment_noti = dict(self._cache.notification_cache)
        old_comment_noti = dict(self._cache.comment_noti_cache)
        (
            latest_non_comment_noti,
            latest_comment_noti,
        ) = await self.fetch_latest_notifications()

        new_non_comment_noti = self._get_new_non_comment_noti(
            old_non_comment_noti, latest_non_comment_noti
        )

        new_artist_comments = await self._get_new_comment(
            old_comment_noti, latest_comment_noti
        )

        return new_non_comment_noti, new_artist_comments

    @staticmethod
    def _get_new_non_comment_noti(
        old_cache: dict[int, Notification], notifications: list[Notification]
    ) -> list[Notification]:
        """Returns a list of new non-comment notifications that do not exist in
        the cache.

        Parameters
        ----------
        old_cache: dict[:class:`int`, :class:`sunverse.objects.Notificiation`]
            The old notification cache used to check which notifications are new.
        notifications: list[:class:`sunverse.objects.Notification`]
            The list that contains the latest notifications the user has access to.

        Returns
        -------
        list[:class:`sunverse.objects.Notification`]
            A list of new notifications.
        """
        current_epoch_time = get_current_epoch_time()
        epoch_time_difference = 600000  # Equivalent to 10 minutes.
        return [
            notification
            for notification in notifications
            if notification.id not in old_cache
            and current_epoch_time - notification.time_created <= epoch_time_difference
        ]

    async def _get_new_comment(
        self, old_cache: dict[str, int], notifications: list[Notification]
    ) -> list[Comment]:
        """Returns a list of new artist comments.

        Parameters
        ----------
        old_cache: dict[:class:`str`, :class:`int`]
            The old notification cache used to check which notifications are new.
        notifications: list[:class:`sunverse.objects.Notification`]
            The list that contains the latest notifications the user has access to.

        Returns
        -------
        list[:class:`sunverse.objects.Comment`]
            A list of :class:`sunverse.objects.Comment` objects of the new
            artist comments.
        """
        new_artist_comments = []
        current_epoch_time = get_current_epoch_time()
        epoch_time_difference = 60000  # Equivalent to 1 minute

        for notification in notifications:
            await asyncio.sleep(self.__fetch_delay)

            try:
                artist_comments = await self.fetch_artist_comments(notification.post_id)

            except NotFound:  # This is because the Post has been deleted.
                continue

            if not old_cache.get(notification.post_id + notification.author_id):
                for artist_comment in artist_comments:
                    if (
                        current_epoch_time - artist_comment.created_at
                        <= epoch_time_difference
                    ):
                        new_artist_comments.insert(0, artist_comment)

            else:
                # This is done because there can be different artists that
                # have written on a post. As such, a new list is created
                # to contain only comments written by the author provided in
                # the notification data.
                artist_comments = [
                    artist_comment
                    for artist_comment in artist_comments
                    if artist_comment.author.id == notification.author_id
                ]
                comment_count = old_cache[notification.post_id + notification.author_id]
                new_comment_count = notification.count - comment_count

                for artist_comment in artist_comments[0:new_comment_count]:
                    new_artist_comments.insert(0, artist_comment)

        return new_artist_comments

    async def fetch_latest_notifications(self) -> tuple[list, list]:
        """Fetches a tuple that contains a list of the latest non-comment
        notifications and a list of the latest comment notifications from all
        communities that the signed-in account has access to.

        Returns
        -------
        tuple[:class:`list`, :class:`list`]
            A tuple that contains a list of :class:`sunverse.objects.Notification`
            non-comment notification objects and a list of
            :class:`sunverse.objects.Notification` comment notifications objects
            the signed-in account has access to.
        """
        url = self._urls.latest_notifications_url()
        data = await self._fetcher(url)
        (
            non_comment_notifications,
            comment_notifications,
        ) = await self._sort_notifications(data, url)
        self._log(
            ("LATEST NON-COMMENT NOTIFICATIONS", "Non-Comment Notifications"),
            data,
            non_comment_notifications,
        )
        self._log(
            ("LATEST COMMENT NOTIFICATIONS", "Comment Notifications"),
            data,
            comment_notifications,
        )
        return non_comment_notifications, comment_notifications

    async def _sort_notifications(
        self, notification_data: dict, url: str
    ) -> tuple[list, list]:
        """Sorts a dictionary containing notification data into
        comment notifications and non-comment notifications.

        Parameters
        ----------
        notification_data: :class:`dict`
            The dictionary that contains the data of the notifications to sort.
        url: :class:`str`
            The retry URL in case of errors.

        Returns
        -------
        tuple[:class:`list`, :class:`list`]
            A tuple that contains a list of non-comment notifications and
            a list of comment notifications.
        """
        comment_notification_types = [
            PostTypes.USER_POST_COMMENT,
            PostTypes.MEDIA_COMMENT,
            PostTypes.MOMENT_COMMENT,
            PostTypes.ARTIST_POST_COMMENT,
        ]
        non_comment_notifications = []
        comment_notifications = []

        for data in notification_data["data"]:
            if not data.get("community"):
                continue

            notification = await self._object_creator(
                ObjectTypes.NOTIFICATION, data, url
            )

            if notification.post_type in comment_notification_types:
                self._cache.cache_comment_noti(notification)
                comment_notifications.append(notification)

            else:
                self._cache.limitless_cache(ObjectTypes.NOTIFICATION, notification)
                non_comment_notifications.append(notification)

        return non_comment_notifications, comment_notifications

    async def fetch_notification(self, notification_id: int) -> Notification:
        """Fetches a Weverse Notification by its ID.

        Parameters
        ----------
        notification_id: :class:`int`
            The ID of the notification to fetch.

        Returns
        -------
        :class:`sunverse.objects.Notification`
            The Notification object requested by the user.

        Raises
        ------
        ~sunverse.NotFound
            The request received a "NOT FOUND" or 404 response from the Weverse API.
        """
        url = self._urls.notification_url(notification_id)
        data = (await self._fetcher(url))["data"]

        if not data or not data[0].get("community"):
            raise NotFound(url)

        notification = await self._object_creator(
            ObjectTypes.NOTIFICATION, data[0], url
        )

        self._cache.limitless_cache(ObjectTypes.NOTIFICATION, notification)
        self._log(("NOTIFICATION", "Notification"), data, notification)
        return notification

    async def fetch_joined_communities(self) -> list[Community]:
        """Fetches the list of Weverse Communities that the signed-in account
        has access to.

        Returns
        -------
        :class:`list[sunverse.objects.Community]`
        A list of :class:`sunverse.objects.Community` objects the signed-in account
        has access to.
        """
        communities = []
        data = await self._fetcher(self._urls.joined_communities_url())

        for community_data in data["data"]:
            await asyncio.sleep(self.__fetch_delay)
            community = await self.fetch_community(community_data["communityId"])
            communities.append(community)

        self._log(("JOINED COMMUNITIES", "Communities"), data, communities)
        return communities

    async def fetch_community(self, community_id: int) -> Community:
        """Fetches a Weverse Community by its ID.

        Parameters
        ----------
        community_id: :class:`int`
            The ID of the community to fetch.

        Returns
        -------
        :class:`sunverse.objects.Community`
            The Community object requested by the user.
        """
        url = self._urls.community_url(community_id)
        data = await self._fetcher(url)
        community = await self._object_creator(ObjectTypes.COMMUNITY, data, url)
        self._cache.limitless_cache(ObjectTypes.COMMUNITY, community)
        self._log(("COMMUNITY", "Community"), data, community)
        return community

    async def fetch_artists(self, community_id: int) -> dict[str, Artist]:
        """Fetches the Artists that belong to a Weverse Community by the community ID.

        Parameters
        ----------
        community_id: :class:`int`
            The ID of the community that the artists are part of to fetch.

        Returns
        -------
        dict[:class:`str`, :class:`sunverse.objects.Artist`]
            The dictionary that contains the Artist objects requested
            by the user. The keys of the dictionary are the artist ID of artists.
        """
        data = await self._fetcher(self._urls.artists_url(community_id))
        artists: dict[str, Artist] = {
            artist_data["memberId"]: await self._object_creator(
                ObjectTypes.ARTIST,
                artist_data,
                self._urls.artists_url(community_id),
            )
            for artist_data in data
        }

        self._cache.limitless_cache(ObjectTypes.ARTIST, artists)
        self._log(("ARTISTS", "Artists"), data, artists)
        return artists

    async def fetch_post(self, post_id: str) -> Post:
        """Fetches a Weverse Post by its ID.

        Parameters
        ----------
        post_id: :class:`str`
            The ID of the post to fetch.

        Returns
        -------
        :class:`sunverse.objects.Post`
            The Post object requested by the user.
        """
        url = self._urls.post_url(post_id)
        data = await self._fetcher(url)
        post = await self._object_creator(ObjectTypes.POST, data, url)
        self._log(("POST", "Post"), data, post)
        return post

    async def fetch_video_url(self, video_id: str) -> str:
        """Fetches a Weverse Post Video URL by its ID.

        Parameters
        ----------
        video_id: :class:`str`
            The ID of the video to fetch.

        Returns
        -------
        :class:`str`
            The URL of the video.

        Notes
        -----
        An additional API call has to be made because unlike images,
        Weverse does include the URL to videos in the response for posts.
        """
        data = await self._fetcher(self._urls.video_url(video_id))
        url_mapping = {}

        for video_data in data["downloadInfo"]:
            url_mapping[int(video_data["resolution"].replace("P", ""))] = video_data[
                "url"
            ]

        return url_mapping[max(url_mapping)]

    async def fetch_media(
        self, media_id: str
    ) -> ImageMedia | WeverseMedia | YoutubeMedia:
        """Fetches a Weverse Media by its ID.

        Parameters
        ----------
        media_id: :class:`str`
            The ID of the media to fetch.

        Returns
        -------
        Union[:class:`sunverse.objects.ImageMedia`,
        :class:`sunverse.objects.WeverseMedia`, :class:`sunverse.objects.YoutubeMedia`]
            The Media object requested by the user.
        """
        url = self._urls.post_url(media_id)

        try:  # This catches error 403 because the media is paid content.
            data = await self._fetcher(url)

        except RequestFailed:
            logger.warning(
                "FETCHING MEDIA FAILED\nCode: 403\n"
                "Reason: The requested resource is a paid content."
            )
            return

        if "image" in data["extension"]:
            media = await self._object_creator(ObjectTypes.IMAGE_MEDIA, data, url)

        elif "youtube" in data["extension"]:
            media = await self._object_creator(ObjectTypes.YOUTUBE_MEDIA, data, url)

        elif "video" in data["extension"]:
            media = await self._object_creator(ObjectTypes.WEVERSE_MEDIA, data, url)

        self._log(("MEDIA", "Media"), data, media)
        return media

    async def fetch_live(self, live_id: str) -> Live:
        """Fetches a Weverse Live Broadcast by its ID.

        Parameters
        ----------
        live_id: :class:`str`
            The ID of the live broadcast to fetch.

        Returns
        -------
        :class:`sunverse.objects.Live`
            The Live object requested by the user.
        """
        url = self._urls.post_url(live_id)
        data = await self._fetcher(url)
        live = await self._object_creator(ObjectTypes.LIVE, data, url)
        self._log(("LIVE", "Live"), data, live)
        return live

    async def fetch_moment(self, moment_id: str) -> Moment | OldMoment:
        """Fetches a Weverse Moment by its ID.

        Parameters
        ----------
        moment_id: :class:`str`
            The ID of the moment to fetch.

        Returns
        -------
        Union[:class:`sunverse.objects.Moment`, :class:`sunverse.objects.OldMoment`]
            The Moment object requested by the user.
        """
        url = self._urls.post_url(moment_id)
        data = await self._fetcher(url)

        if "moment" in data["extension"]:
            moment = await self._object_creator(ObjectTypes.NEW_MOMENT, data, url)

        elif "momentW1" in data["extension"]:
            moment = await self._object_creator(ObjectTypes.OLD_MOMENT, data, url)

        self._log(("MOMENT", "Moment"), data, moment)
        return moment

    async def fetch_notice(self, notice_id: int) -> Notice:
        """Fetches a Weverse Notice by its ID.

        Parameters
        ----------
        notice_id: :class:`int`
            The ID of the notice to fetch.

        Returns
        -------
        :class:`sunverse.objects.Notice`
            The Notice object requested by the user.
        """
        url = self._urls.notice_url(notice_id)
        data = await self._fetcher(url)
        notice = await self._object_creator(ObjectTypes.NOTICE, data, url)
        self._log(("NOTICE", "Notice"), data, notice)
        return notice

    async def fetch_member(self, member_id: str) -> Member:
        """Fetches a Weverse Member by its ID.

        Parameters
        ----------
        member_id: :class:`str`
            The ID of the member to fetch.

        Returns
        -------
        :class:`sunverse.objects.Member`
            The Member object requested by the user.
        """
        url = self._urls.member_url(member_id)
        data = await self._fetcher(url)
        member = await self._object_creator(ObjectTypes.MEMBER, data, url)
        self._log(("MEMBER", "Member"), data, member)
        return member

    async def fetch_artist_comments(self, post_id: str) -> list[Comment]:
        """Fetches a list of artist comments that belong to a
        post by the post ID.

        Parameters
        ----------
        post_id: :class:`str`
            The ID of the post that the artist comments are part of to fetch.

        Returns
        -------
        list[:class:`sunverse.objects.Comment`]
            The list that contains the Comment objects requested by the user.
        """
        artist_comments = []
        url = self._urls.artist_comments_url(post_id)
        data = await self._fetcher(url)

        for comment_data in data["data"]:
            artist_comment = await self._object_creator(
                ObjectTypes.COMMENT, comment_data, url
            )
            artist_comments.append(artist_comment)

        self._log(("ARTIST COMMENTS", "Artist Comments"), data, artist_comments)
        return artist_comments

    async def fetch_comment(self, comment_id: str) -> Comment:
        """Fetches a Weverse Comment by its ID.

        Parameters
        ----------
        comment_id: :class:`str`
            The ID of the comment to fetch.

        Returns
        -------
        :class:`sunverse.objects.Comment`
            The Comment object requested by the user.
        """
        url = self._urls.comment_url(comment_id)
        data = await self._fetcher(url)
        comment = await self._object_creator(ObjectTypes.COMMENT, data, url)
        self._log(("COMMENT", "Comment"), data, comment)
        return comment

    async def start(self) -> asyncio.Task:
        """Starts the Sunverse Client."""
        await self._fetch_access_token_by_credentials()
        await self.fetch_latest_notifications()
        logger.info(
            "Started listening for Weverse Notifications. "
            "You will be updated every %s seconds.",
            self.stream_delay,
        )
        self.__task = asyncio.create_task(self.__notification_stream())
        return self.__task

    def stop(self) -> None:
        """Disconnects the Sunverse Client."""
        self.__task.cancel()
        self.__task = None
        logger.info("The Weverse client has been stopped.")

    async def __notification_stream(self) -> None:
        while True:
            try:
                await asyncio.sleep(self.stream_delay)
                notifications, comments = await self.fetch_new_notification()

                for notification in notifications:
                    await self.on_new_notification(notification)

                    if notification.post_type == PostTypes.POST:
                        post = await self.fetch_post(notification.post_id)
                        await self.on_new_post(post)

                    elif notification.post_type == PostTypes.MOMENT:
                        moment = await self.fetch_moment(notification.post_id)
                        await self.on_new_moment(moment)

                    elif notification.post_type == PostTypes.MEDIA:
                        media = await self.fetch_media(notification.post_id)
                        if media:  # Don't call this method when the media is paid.
                            await self.on_new_media(media)

                    elif notification.post_type == PostTypes.LIVE:
                        live = await self.fetch_live(notification.post_id)
                        await self.on_new_live(live)

                    elif notification.post_type == PostTypes.NOTICE:
                        notice = await self.fetch_notice(notification.post_id)
                        if notice:  # Don't call this method for non-artist notice.
                            await self.on_new_notice(notice)

                for comment in comments:
                    await self.on_new_comment(comment)

            except Exception as exception:
                await self.on_exception(exception)

    async def on_new_notification(self, notification: Notification) -> None:
        """This method is called when a new notification is detected.
        You can overwrite this method to do what you want with the new
        notification.
        """

    async def on_new_post(self, post: Post) -> None:
        """This method is called when a new post is detected.
        You can overwrite this method to do what you want with the new post.
        """

    async def on_new_moment(self, moment: Moment | OldMoment) -> None:
        """This method is called when a new moment is detected.
        You can overwrite this method to do what you want with the new moment.
        """

    async def on_new_media(
        self, media: ImageMedia | WeverseMedia | YoutubeMedia
    ) -> None:
        """This method is called when a new media is detected.
        You can overwrite this method to do what you want with the new media.
        """

    async def on_new_live(self, live: Live) -> None:
        """This method is called when a new live is detected.
        You can overwrite this method to do what you want with the new live.
        """

    async def on_new_notice(self, notice: Notice) -> None:
        """This method is called when a new notice is detected.
        You can overwrite this method to do what you want with the new notice.
        """

    async def on_new_comment(self, comment: Comment) -> None:
        """This method is called when a new comment is detected.
        You can overwrite this method to do what you want with the new comment.
        """

    async def on_exception(self, exception: Exception) -> None:
        """This method is called when an unhandled exception occurs.
        You can overwrite this method to do what you want with the exception.

        By default, an exception message is logged.
        """
        logger.exception(exception)


class _SunverseCache:
    def __init__(self):
        self.comment_noti_cache: dict[str, int] = {}
        self.community_cache: dict[int, Community] = {}
        self.artist_cache: dict[str, Artist] = {}
        self.notification_cache: dict[int, Notification] = {}

    def cache_comment_noti(self, comment_notification: Notification) -> None:
        """Caches comment notifications so that they can be used
        to determine how many and which comment notifications are new.

        Parameters
        ----------
        comment_notification: :class:`sunverse.objects.Notification`
            The comment notification to cache.
        """
        self.comment_noti_cache[
            comment_notification.post_id + comment_notification.author_id
        ] = comment_notification.count

    def limitless_cache(self, object_type: str, sunverse_object) -> None:
        """Responsible for caching objects that are not limited by
        the defined limit. See the notes below for more details
        regarding which objects are cached using this method.

        Parameters
        ----------
        object_type: :class:`str`
            The type of object to cache.
        sunverse_object: :class:`Any`
            The actual Sunverse Object to cache.

        Notes
        -----
        Limitless caching is applied to :class:`sunverse.objects.Community`,
        :class:`sunverse.objects.Artist` and :class:`sunverse.objects.Notification`.
        """
        cache_mapping = {
            ObjectTypes.COMMUNITY: self.community_cache,
            ObjectTypes.ARTIST: self.artist_cache,
            ObjectTypes.NOTIFICATION: self.notification_cache,
        }
        if object_type == ObjectTypes.ARTIST:
            for artist in sunverse_object:
                cache_mapping[object_type][artist] = sunverse_object[artist]

        else:
            cache_mapping[object_type][sunverse_object.id] = sunverse_object
