"""
Possible errors robot ports, objects and interface might face.
"""


class ReceivePacketError(Exception):
    """Failed to parse a packet from serial"""


class LoopSignalledError(Exception):
    """Loop method threw an exception"""


class StartSignalledError(Exception):
    """User's start method threw an exception"""


class CloseSignalledExitError(Exception):
    """Loop method threw an exception"""


class PacketReceivedError(Exception):
    """packet_received method threw an exception"""


class PacketReceiveError(Exception):
    """robot_object.receive method threw an exception"""

    def __init__(self, whoiam, packet):
        super(PacketReceiveError, self).__init__("Input packet from '%s': %s" % (whoiam, repr(packet)))


class InitializationError(Exception):
    """Object passed isn't a RobotObject"""


class DeviceUnassignedError(Exception):
    """Port was open successfully but no objects use it"""


class DeviceWhoiamIdTaken(Exception):
    """whoiam ID is already being used by another port"""


class DeviceNotConfiguredError(Exception):
    """Port was not opened successfully"""


class DeviceNotFoundError(Exception):
    """Failed to assign a robot object to a port"""


class DeviceClosedPrematurelyError(Exception):
    """serial object signalled it wasn't open"""


class DeviceReadPacketError(Exception):
    """A port failed to call read_packets successfully"""


class DeviceWritePacketError(Exception):
    """A port failed to call write_packets successfully"""


class DeviceSignalledExitError(Exception):
    """Port signalled to exit"""


class DeviceFailedToStopError(Exception):
    """Port didn't stop"""
