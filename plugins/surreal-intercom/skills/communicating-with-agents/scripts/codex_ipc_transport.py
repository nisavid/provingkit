"""Connection-capable CLI framing. Activation requires separate live authority.

The connector returns read(maximum, timeout), write(bytes, timeout), close().
Both production and invented IO use FrameReceiver; no background reader exists.
"""
# Extracted from retained native_cli_transport.py, SHA-256
# 259cea2f440065c77a07436c40a23387eda3d4679237736ae92ada62e1dbe0c1.
import hashlib
import json
import struct
import time
import uuid

class ReceiveFailure(Exception):
    pass

class ReceivePrefixFailure(ReceiveFailure):
    """Completed exchange records and the terminal acquisition failure."""
    def __init__(self, reason, records):
        super().__init__(reason)
        self.records = records

class FrameReceiver:
    def __init__(self, limits):
        self.limits = limits
        self.acquired = 0
        self.events = 0
        self.incomplete = None
        self.rejected_frame = None

    def receive(self, read, clock, deadline):
        # Every header (including cleanup) must fit before any acquisition.
        if self.acquired + 4 > self.limits['incomingBytes']:
            raise ReceiveFailure('incoming-byte-limit')
        if self.events >= self.limits['events']:
            raise ReceiveFailure('event-limit')
        def exact(count):
            data = bytearray()
            while len(data) < count:
                remaining = deadline - clock()
                if remaining <= 0:
                    raise ReceiveFailure('observation-deadline-unknown')
                try:
                    part = read(count - len(data), remaining)
                except TimeoutError as exc:
                    raise ReceiveFailure('observation-deadline-unknown') from exc
                except OSError as exc:
                    raise ReceiveFailure('stream-read-error') from exc
                if not part:
                    raise ReceiveFailure('stream-eof-unknown')
                if len(part) > count - len(data):
                    raise ReceiveFailure('stream-contract-overread')
                self.acquired += len(part)
                data.extend(part)
            return bytes(data)
        started = self.acquired
        try:
            length = struct.unpack('<I', exact(4))[0]
            if not 0 < length <= self.limits['frameBytes']:
                if self.rejected_frame is None:
                    self.rejected_frame = {'announcedLength': length,
                                           'frameBytes': self.limits['frameBytes'],
                                           'wireOffset': started}
                raise ReceiveFailure('frame-byte-limit')
            if self.acquired + length > self.limits['incomingBytes']:
                raise ReceiveFailure('incoming-byte-limit')
            body = exact(length)
            self.events += 1
            message = json.loads(body)
            if not isinstance(message, dict):
                raise ReceiveFailure('frame-object-required')
            return message
        except (ReceiveFailure, ValueError) as exc:
            # Supported receive failures have one terminal contract. Completed
            # messages belong to the exchange; this failure cannot erase them.
            reason = str(exc) if isinstance(exc, ReceiveFailure) else 'frame-decode-error'
            if self.acquired != started or reason != 'observation-deadline-unknown':
                self.incomplete = reason
            if isinstance(exc, ReceiveFailure):
                raise
            raise ReceiveFailure(reason) from exc

class UnixStream:
    def __init__(self, connection):
        self.connection = connection
    def read(self, maximum, timeout):
        self.connection.settimeout(timeout)
        return self.connection.recv(maximum)
    def write(self, data, timeout):
        self.connection.settimeout(timeout)
        self.connection.sendall(data)
    def close(self):
        self.connection.close()

def connect_unix(endpoint, timeout):
    # Importing this module opens no socket. The command uses this connector
    # only when its caller explicitly invokes the genuine operation.
    import socket
    connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        connection.settimeout(timeout)
        connection.connect(endpoint)
        return UnixStream(connection)
    except BaseException:
        connection.close()
        raise

class CliTransport:
    production = True
    def __init__(self, endpoint, limits, observation_seconds, connector=connect_unix, clock=time.monotonic):
        self.endpoint = endpoint
        self.limits = limits
        self.wait = observation_seconds
        self.connector = connector
        self.clock = clock
        self.generation = str(uuid.uuid4())
        self.receiver = FrameReceiver(self.limits)
        self.stream = None
        self.outbound = []
        self.pending_path = None
        self.write_boundary = {}
        self.receive_status = []
        self.retained = []
        self.closed = False
    @property
    def acquired(self):
        return self.receiver.acquired
    @property
    def events(self):
        return self.receiver.events
    def send(self, envelope):
        if self.stream is None:
            self.stream = self.connector(self.endpoint, self.wait)
        if envelope['method'] in {'thread-follower-steer-turn', 'thread-follower-start-turn'}:
            if self.pending_path is None or not self.pending_path.is_file():
                raise ReceiveFailure('missing-pre-write-capture')
            self.write_boundary = {'pendingExistedBeforeWrite': True,
                                   'pendingSha256': hashlib.sha256(self.pending_path.read_bytes()).hexdigest()}
        data = json.dumps(envelope, separators=(',', ':')).encode()
        self.outbound.append(envelope)
        deadline = self.clock() + self.wait
        self.stream.write(struct.pack('<I', len(data)) + data, self.wait)
        if self.receiver.incomplete:
            self.receive_status.append('receive-disabled:' + self.receiver.incomplete)
            return []
        records = []
        try:
            while self.clock() < deadline:
                message = self.receiver.receive(self.stream.read, self.clock, deadline)
                record = {'at': self.clock(), 'generation': self.generation}
                records.append((record, message))
                self.retained.append((record, message))
                if message.get('type') == 'client-discovery-request':
                    if 'requestId' not in message:
                        self.receiver.incomplete = 'discovery-request-id-missing'
                        raise ReceiveFailure(self.receiver.incomplete)
                    answer = {'type': 'client-discovery-response', 'requestId': message['requestId'],
                              'response': {'canHandle': False}}
                    body = json.dumps(answer).encode()
                    self.stream.write(struct.pack('<I', len(body)) + body, max(0.001, deadline - self.clock()))
                    self.outbound.append(answer)
                if (envelope['method'] in {'initialize', 'thread-owner-discovery'}
                        and message.get('type') == 'response'
                        and message.get('requestId') == envelope.get('requestId')):
                    return records
        except (ReceiveFailure, OSError) as exc:
            reason = str(exc) if isinstance(exc, ReceiveFailure) else 'stream-write-error'
            if isinstance(exc, OSError):
                self.receiver.incomplete = reason
            self.receive_status.append(reason)
            if (reason in {'observation-deadline-unknown', 'stream-eof-unknown'}
                    or (records and reason in {'incoming-byte-limit', 'event-limit'}
                        and self.receiver.incomplete is None)):
                return records
            raise ReceivePrefixFailure(reason, records) from exc
        self.receive_status.append('observation-deadline-unknown')
        return records
    def close(self):
        if self.stream is not None:
            self.stream.close()
        self.closed = True


def discover_owner(transport, binding, *, text, refusal):
    """Initialize and bind the exact target's owner on this connection.

    Populate binding["owner"] as soon as the correlated discovery proves it,
    preserving that acquired prefix even if an incomplete frame then refuses.
    Caller-supplied text validation and refusal keep its diagnostic contract.
    This does not select a turn operation or establish authenticated identity.
    """
    records = transport.send({
        "type": "request", "requestId": "initialize", "version": 0,
        "method": "initialize", "params": {"clientType": "cli"},
    })
    matches = [message for _, message in records
               if message.get("type") == "response"
               and message.get("requestId") == "initialize"
               and message.get("method") == "initialize"
               and message.get("resultType") == "success"]
    if len(matches) != 1 or not isinstance(matches[0].get("result"), dict):
        raise refusal("initialize-unavailable")
    client = text(matches[0].get("result", {}).get("clientId"), "native-client")
    records = transport.send({
        "type": "request", "requestId": "owner", "sourceClientId": client,
        "version": 1, "method": "thread-owner-discovery",
        "params": {"hostId": "local", "conversationId": binding["target"]},
    })
    matches = [message for _, message in records
               if message.get("type") == "response"
               and message.get("requestId") == "owner"
               and message.get("method") == "thread-owner-discovery"
               and message.get("resultType") == "success"]
    if len(matches) != 1:
        raise refusal("owner-unavailable")
    binding["owner"] = text(matches[0].get("handledByClientId"), "native-owner")
    if transport.receiver.incomplete is not None:
        raise refusal("connection-incomplete-before-write")
    return client
