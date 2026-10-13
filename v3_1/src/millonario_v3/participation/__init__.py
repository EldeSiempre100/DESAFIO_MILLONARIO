"""Sala local, protocolo HTTP/WebSocket y pulsadores de la V3.1."""

from .room import RoomError, RoomManager
from .service import ParticipationService

__all__ = ["ParticipationService", "RoomError", "RoomManager"]
