import io
import logging
import random
import time
from typing import Any, Mapping, BinaryIO, List, Union, Sequence
from abc import abstractproperty, abstractmethod
from collections import deque, defaultdict

import inspect

try:
    from abc import ABC
except ImportError:
    #  3.3 compatibility
    from abc import ABCMeta

    class ABC(metaclass=ABCMeta):
        """Helper class that provides a standard way to create an ABC using
        inheritance.
        """
        pass


from errbot.utils import compat_str, deprecated

# Can't use __name__ because of Yapsy
log = logging.getLogger('errbot.backends.base')


class Identifier(ABC):
    """This is just use for type hinting representing the Identifier contract,
    NEVER TRY TO SUBCLASS IT OUTSIDE OF A BACKEND, it is just here to show you what you can expect from an Identifier.
    To get an instance of a real identifier, always use the properties from Message (to, from) or self.build_identifier
     to make an identifier from a String.

     The semantics is anything you can talk to: Person, Room, RoomOccupant etc.
    """
    pass


class Person(Identifier):
    """This is just use for type hinting representing the Identifier contract,
    NEVER TRY TO SUBCLASS IT OUTSIDE OF A BACKEND, it is just here to show you what you can expect from an Identifier.
    To get an instance of a real identifier, always use the properties from Message (to, from) or self.build_identifier
     to make an identifier from a String.
    """

    @abstractproperty
    def person(self) -> str:
        """
        :return: a backend specific unique identifier representing the person you are talking to.
        """
        pass

    @abstractproperty
    def client(self) -> str:
        """
        :return: a backend specific unique identifier representing the device or client the person is using to talk.
        """
        pass

    @abstractproperty
    def nick(self) -> str:
        """
        :return: a backend specific nick returning the nickname of this person if available.
        """
        pass

    @abstractproperty
    def aclattr(self) -> str:
        """
        :return: returns the unique identifier that will be used for ACL matches.
        """
        pass

    @abstractproperty
    def fullname(self) -> str:
        """
        Some backends have the full name of a user.
        :return: the fullname of this user if available.
        """
        pass


class RoomOccupant(Identifier):
    @abstractproperty
    def room(self) -> Any:  # this is oom defined below
        """
        Some backends have the full name of a user.
        :return: the fullname of this user if available.
        """
        pass


class Room(Identifier):
    """
    This class represents a Multi-User Chatroom.
    """

    def join(self, username: str=None, password: str=None) -> None:
        """
        Join the room.

        If the room does not exist yet, this will automatically call
        :meth:`create` on it first.
        """
        raise NotImplementedError("It should be implemented specifically for your backend")

    def leave(self, reason: str=None) -> None:
        """
        Leave the room.

        :param reason:
            An optional string explaining the reason for leaving the room.
        """
        raise NotImplementedError("It should be implemented specifically for your backend")

    def create(self) -> None:
        """
        Create the room.

        Calling this on an already existing room is a no-op.
        """
        raise NotImplementedError("It should be implemented specifically for your backend")

    def destroy(self) -> None:
        """
        Destroy the room.

        Calling this on a non-existing room is a no-op.
        """
        raise NotImplementedError("It should be implemented specifically for your backend")

    @property
    def exists(self) -> bool:
        """
        Boolean indicating whether this room already exists or not.

        :getter:
            Returns `True` if the room exists, `False` otherwise.
        """
        raise NotImplementedError("It should be implemented specifically for your backend")

    @property
    def joined(self) -> bool:
        """
        Boolean indicating whether this room has already been joined.

        :getter:
            Returns `True` if the room has been joined, `False` otherwise.
        """
        raise NotImplementedError("It should be implemented specifically for your backend")

    @property
    def topic(self) -> str:
        """
        The room topic.

        :getter:
            Returns the topic (a string) if one is set, `None` if no
            topic has been set at all.

            .. note::
                Back-ends may return an empty string rather than `None`
                when no topic has been set as a network may not
                differentiate between no topic and an empty topic.
        :raises:
            :class:`~MUCNotJoinedError` if the room has not yet been joined.

        """
        raise NotImplementedError("It should be implemented specifically for your backend")

    @topic.setter
    def topic(self, topic: str) -> None:
        """
        Set the room's topic.

        :param topic:
            The topic to set.
        """
        raise NotImplementedError("It should be implemented specifically for your backend")

    @property
    def occupants(self) -> List[RoomOccupant]:
        """
        The room's occupants.

        :getter:
            Returns a list of occupant identities.
        :raises:
            :class:`~MUCNotJoinedError` if the room has not yet been joined.
        """
        raise NotImplementedError("It should be implemented specifically for your backend")

    def invite(self, *args) -> None:
        """
        Invite one or more people into the room.

        :*args:
            One or more identifiers to invite into the room.
        """
        raise NotImplementedError("It should be implemented specifically for your backend")


class RoomError(Exception):
    """General exception class for MUC-related errors"""


class RoomNotJoinedError(RoomError):
    """Exception raised when performing MUC operations
    that require the bot to have joined the room"""


class RoomDoesNotExistError(RoomError):
    """Exception that is raised when performing an operation
    on a room that doesn't exist"""


class UserDoesNotExistError(Exception):
    """Exception that is raised when performing an operation
    on a user that doesn't exist"""


class Message(object):
    """
    A chat message.

    This class represents chat messages that are sent or received by
    the bot. It is modeled after XMPP messages so not all methods
    make sense in the context of other back-ends.
    """

    def __init__(self,
                 body: str='',
                 frm: Identifier=None,
                 to: Identifier=None,
                 delayed: bool=False,
                 extras: Mapping=None):
        """
        :param body:
            The plaintext body of the message.
        :param extras:
            Extra data attached by a backend
        """
        self._body = compat_str(body)
        self._from = frm
        self._to = to
        self._delayed = delayed
        self._extras = extras or dict()

    def clone(self):
        return Message(self._body, self._from, self._to, self._delayed, self.extras)

    @property
    def to(self) -> Identifier:
        """
        Get the recipient of the message.

        :returns:
            A backend specific identifier representing the recipient.
        """
        return self._to

    @to.setter
    def to(self, to: Identifier):
        """
        Set the recipient of the message.

        :param to:
            An identifier from for example build_identifier().
        """
        self._to = to

    @property
    def frm(self) -> Identifier:
        """
        Get the sender of the message.

        :returns:
            An :class:`~errbot.backends.base.Identifier` identifying
            the sender.
        """
        return self._from

    @frm.setter
    def frm(self, from_: Identifier):
        """
        Set the sender of the message.

        :param from_:
            An identifier from build_identifier.
        """
        self._from = from_

    @property
    def body(self) -> str:
        """
        Get the plaintext body of the message.

        :returns:
            The body as a string.
        """
        return self._body

    @body.setter
    def body(self, body: str):
        self._body = body

    @property
    def delayed(self) -> bool:
        return self._delayed

    @delayed.setter
    def delayed(self, delayed: bool):
        self._delayed = delayed

    @property
    def extras(self) -> Mapping:
        return self._extras

    def __str__(self):
        return self._body

    @property
    def is_direct(self) -> bool:
        return isinstance(self.to, Person)

    @property
    def is_group(self) -> bool:
        return isinstance(self.to, Room)

    @property
    def type(self):
        msg = ' {0.filename}:{0.lineno} : '.format(inspect.getframeinfo(inspect.currentframe().f_back))
        log.warn(msg + 'msg.type is deprecated and will be removed soon ! Use msg.is_direct or msg.is_group.')
        return 'chat' if self.is_direct else 'groupchat'

ONLINE = 'online'
OFFLINE = 'offline'
AWAY = 'away'
DND = 'dnd'


class Presence(object):
    """
       This class represents a presence change for a user or a user in a chatroom.

       Instances of this class are passed to :meth:`~errbot.botplugin.BotPlugin.callback_presence`
       when the presence of people changes.
    """

    def __init__(self,
                 identifier: Identifier,
                 status: str=None,
                 message: str=None):
        if identifier is None:
            raise ValueError('Presence: identifiers is None')
        if status is None and message is None:
            raise ValueError('Presence: at least a new status or a new status message mustbe present')
        self._identifier = identifier
        self._status = status
        self._message = message

    @property
    def nick(self) -> str:
        """ Returns a plain string of the presence nick.
            (In some chatroom implementations, you cannot know the real identifier
            of a person in it).
            Can return None but then identifier won't be None.
        """
        return self._identifier.nick

    @property
    def occupant(self) -> RoomOccupant:
        """ Returns the identifier of the event.
            Can be None *only* if chatroom is not None
        """
        return self._identifier

    @property
    def status(self) -> str:
        """ Returns the status of the presence change.
            It can be one of the constants ONLINE, OFFLINE, AWAY, DND, but
            can also be custom statuses depending on backends.
            It can be None if it is just an update of the status message (see get_message)
        """
        return self._status

    @property
    def message(self) -> str:
        """ Returns a human readable message associated with the status if any.
            like : "BRB, washing the dishes"
            It can be None if it is only a general status update (see get_status)
        """
        return self._message

    def __str__(self):
        response = ''
        if self._nick:
            response += 'Nick:%s ' % self._nick
        if self._identifier:
            response += 'Idd:%s ' % self._identifier
        if self._status:
            response += 'Status:%s ' % self._status
        if self._message:
            response += 'Msg:%s ' % self._message
        return response

    def __unicode__(self):
        return str(self.__str__())

STREAM_WAITING_TO_START = 'pending'
STREAM_TRANSFER_IN_PROGRESS = 'in progress'
STREAM_SUCCESSFULLY_TRANSFERED = 'success'
STREAM_PAUSED = 'paused'
STREAM_ERROR = 'error'
STREAM_REJECTED = 'rejected'

DEFAULT_REASON = 'unknown'


class Stream(io.BufferedReader):
    """
       This class represents a stream request.

       Instances of this class are passed to :meth:`~errbot.botplugin.BotPlugin.callback_stream`
       when an incoming stream is requested.
    """

    def __init__(self,
                 identifier: Identifier,
                 fsource: BinaryIO,
                 name: str=None,
                 size: int=None,
                 stream_type: str=None):
        super().__init__(fsource)
        self._identifier = identifier
        self._name = name
        self._size = size
        self._stream_type = stream_type
        self._status = STREAM_WAITING_TO_START
        self._reason = DEFAULT_REASON
        self._transfered = 0

    @property
    def identifier(self) -> Identifier:
        """
           The identity the stream is coming from if it is an incoming request
           or to if it is an outgoing request.
        """
        return self._identifier

    @property
    def name(self) -> str:
        """
            The name of the stream/file if it has one or None otherwise.
            !! Be carefull of injections if you are using this name directly as a filename.
        """
        return self._name

    @property
    def size(self) -> int:
        """
            The expected size in bytes of the stream if it is known or None.
        """
        return self._size

    @property
    def transfered(self) -> int:
        """
            The currently transfered size.
        """
        return self._transfered

    @property
    def stream_type(self) -> str:
        """
            The mimetype of the stream if it is known or None.
        """
        return self._stream_type

    @property
    def status(self) -> str:
        """
            The status for this stream.
        """
        return self._status

    def accept(self) -> None:
        """
            Signal that the stream has been accepted.
        """
        if self._status != STREAM_WAITING_TO_START:
            raise ValueError("Invalid state, the stream is not pending.")
        self._status = STREAM_TRANSFER_IN_PROGRESS

    def reject(self) -> None:
        """
            Signal that the stream has been rejected.
        """
        if self._status != STREAM_WAITING_TO_START:
            raise ValueError("Invalid state, the stream is not pending.")
        self._status = STREAM_REJECTED

    def error(self, reason=DEFAULT_REASON) -> None:
        """
            An internal plugin error prevented the transfer.
        """
        self._status = STREAM_ERROR
        self._reason = reason

    def success(self) -> None:
        """
            The streaming finished normally.
        """
        if self._status != STREAM_TRANSFER_IN_PROGRESS:
            raise ValueError("Invalid state, the stream is not in progress.")
        self._status = STREAM_SUCCESSFULLY_TRANSFERED

    def clone(self, new_fsource: BinaryIO) -> Any:  # this is obviously a Stream but the compiler doesn't like it.
        """
            Creates a clone and with an alternative stream
        """
        return Stream(self._identifier, new_fsource, self._name, self._size, self._stream_type)

    def ack_data(self, length: int) -> None:
        """ Acknowledge data has been transfered. """
        self._transfered = length


class Backend(ABC):
    """
    Implements the basic Bot logic (logic independent from the backend) and leaves
    you to implement the missing parts.
    """

    cmd_history = defaultdict(lambda: deque(maxlen=10))  # this will be a per user history

    MSG_ERROR_OCCURRED = 'Sorry for your inconvenience. ' \
                         'An unexpected error occurred.'

    def __init__(self, _):
        """ Those arguments will be directly those put in BOT_IDENTITY
        """
        log.debug("Backend init.")
        self._reconnection_count = 0          # Increments with each failed (re)connection
        self._reconnection_delay = 1          # Amount of seconds the bot will sleep on the
        #                                     # next reconnection attempt
        self._reconnection_max_delay = 600    # Maximum delay between reconnection attempts
        self._reconnection_multiplier = 1.75  # Delay multiplier
        self._reconnection_jitter = (0, 3)    # Random jitter added to delay (min, max)

    @abstractmethod
    def send_message(self, mess: Message) -> None:
        """Should be overridden by backends with a super().send_message() call."""

    @abstractmethod
    def change_presence(self, status: str=ONLINE, message: str='') -> None:
        """Signal a presence change for the bot. Should be overridden by backends with a super().send_message() call."""

    @abstractmethod
    def build_reply(self, mess: Message, text: str=None, private: bool=False):
        """ Should be implemented by the backend """

    @abstractmethod
    def callback_presence(self, presence: Presence) -> None:
        """ Implemented by errBot. """
        pass

    @abstractmethod
    def callback_room_joined(self, room: Room) -> None:
        """ See :class:`~errbot.errBot.ErrBot` """
        pass

    @abstractmethod
    def callback_room_left(self, room: Room) -> None:
        """ See :class:`~errbot.errBot.ErrBot` """
        pass

    @abstractmethod
    def callback_room_topic(self, room: Room) -> None:
        """ See :class:`~errbot.errBot.ErrBot` """
        pass

    def serve_forever(self) -> None:
        """
        Connect the back-end to the server and serve forever.

        Back-ends MAY choose to re-implement this method, in which case
        they are responsible for implementing reconnection logic themselves.

        Back-ends SHOULD trigger :func:`~connect_callback()` and
        :func:`~disconnect_callback()` themselves after connection/disconnection.
        """
        while True:
            try:
                if self.serve_once():
                    break  # Truth-y exit from serve_once means shutdown was requested
            except KeyboardInterrupt:
                log.info("Interrupt received, shutting down..")
                break
            except:
                log.exception("Exception occurred in serve_once:")

            log.info(
                "Reconnecting in {delay} seconds ({count} attempted reconnections so far)".format(
                    delay=self._reconnection_delay, count=self._reconnection_count)
            )
            try:
                self._delay_reconnect()
                self._reconnection_count += 1
            except KeyboardInterrupt:
                log.info("Interrupt received, shutting down..")
                break

        log.info("Trigger shutdown")
        self.shutdown()

    def _delay_reconnect(self):
        """Delay next reconnection attempt until a suitable back-off time has passed"""
        time.sleep(self._reconnection_delay)

        self._reconnection_delay *= self._reconnection_multiplier
        if self._reconnection_delay > self._reconnection_max_delay:
            self._reconnection_delay = self._reconnection_max_delay
        self._reconnection_delay += random.uniform(*self._reconnection_jitter)

    def reset_reconnection_count(self) -> None:
        """
        Reset the reconnection count. Back-ends should call this after
        successfully connecting.
        """
        self._reconnection_count = 0
        self._reconnection_delay = 1

    def build_message(self, text: str) -> Message:
        """ You might want to override this one depending on your backend """
        return Message(body=text)

    # ##### HERE ARE THE SPECIFICS TO IMPLEMENT PER BACKEND

    @abstractmethod
    def prefix_groupchat_reply(self, message: Message, identifier: Identifier):
        """ Patches message with the conventional prefix to ping the specific contact
        For example:
        @gbin, you forgot the milk !
        """

    @abstractmethod
    def build_identifier(self, text_representation: str) -> Identifier:
        pass

    def serve_once(self) -> None:
        """
        Connect the back-end to the server and serve a connection once
        (meaning until disconnected for any reason).

        Back-ends MAY choose not to implement this method, IF they implement a custom
        :func:`~serve_forever`.

        This function SHOULD raise an exception or return a value that evaluates
        to False in order to signal something went wrong. A return value that
        evaluates to True will signal the bot that serving is done and a shut-down
        is requested.
        """
        raise NotImplementedError("It should be implemented specifically for your backend")

    def connect(self) -> Any:
        """Connects the bot to server or returns current connection """

    @abstractmethod
    def query_room(self, room: str) -> Room:
        """
        Query a room for information.

        :param room:
            The room to query for.
        :returns:
            An instance of :class:`~Room`.
        """

    @abstractmethod
    def connect_callback(self) -> None:
        pass

    @abstractmethod
    def disconnect_callback(self) -> None:
        pass

    @abstractproperty
    def mode(self) -> str:
        pass

    @abstractproperty
    def rooms(self) -> Sequence[Room]:
        """
        Return a list of rooms the bot is currently in.

        :returns:
            A list of :class:`~errbot.backends.base.Room` instances.
        """
