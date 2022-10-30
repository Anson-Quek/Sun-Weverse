from sunverse.objects.media import WeverseMedia


class Live(WeverseMedia):
    """Represents a Weverse Live Broadcast.
    Inherits from :class:`sunverse.objects.WeverseMedia`.

    Shares the same attributes with :class:`sunverse.objects.Postlike`,
    :class:`sunverse.objects.Medialike` and :class:`sunverse.objects.WeverseMedia`.

    Attributes
    ----------
    message_count: :class:`int`
        The number of messages in the live broadcast.
    """

    __slots__ = ("message_count",)

    def __init__(self, data: dict):
        super().__init__(data)
        self.message_count: int = data["extension"]["mediaInfo"]["chat"]["messageCount"]

    def __repr__(self):
        return f"Live live_id={self.id}, title={self.title}"
