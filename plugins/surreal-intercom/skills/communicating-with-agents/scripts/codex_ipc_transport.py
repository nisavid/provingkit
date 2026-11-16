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
        self.frame_boundary_eof = False

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
        except (ReceiveFailure, ValueError, RecursionError) as exc:
            # Supported receive failures have one terminal contract. Completed
            # messages belong to the exchange; this failure cannot erase them.
            reason = str(exc) if isinstance(exc, ReceiveFailure) else 'frame-decode-error'
            self.frame_boundary_eof = (
                reason == 'stream-eof-unknown' and self.acquired == started
            )
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
    def __init__(self, endpoint, limits, observation_seconds, connector=connect_unix, clock=time.monotonic,
                 *, network_seconds=None, io_seconds=None, cleanup_reserve_seconds=0,
                 max_writes=None, allowed_methods=None, receipt_clock=None):
        self.endpoint = endpoint
        self.limits = limits
        self.wait = observation_seconds
        self.connector = connector
        self.clock = clock
        self.started_at = clock() if network_seconds is not None else None
        self.network_deadline = (self.started_at + network_seconds
                                 if self.started_at is not None else None)
        self.io_seconds = io_seconds
        self.cleanup_reserve_seconds = cleanup_reserve_seconds
        self.max_writes = max_writes
        self.allowed_methods = allowed_methods
        self.receipt_clock = receipt_clock
        self.generation = str(uuid.uuid4())
        self.receiver = FrameReceiver(self.limits)
        self.stream = None
        self.outbound = []
        self.pending_path = None
        self.write_boundary = {}
        self.receive_status = []
        self.retained = []
        self.closed = False
        self.write_count = 0
    @property
    def acquired(self):
        return self.receiver.acquired
    @property
    def events(self):
        return self.receiver.events
    def _check_outgoing_frame(self, data):
        limit = self.receiver.limits.get("outgoingFrameBytes")
        if limit is not None and len(data) > limit:
            raise ReceiveFailure("outgoing-frame-limit")
    def _phase_deadline(self, *, reserve_cleanup):
        deadline = self.clock() + self.wait
        if self.network_deadline is None:
            return deadline
        network_deadline = self.network_deadline
        if reserve_cleanup:
            network_deadline -= self.cleanup_reserve_seconds
        deadline = min(deadline, network_deadline)
        if deadline <= self.clock():
            raise ReceiveFailure("network-deadline-unknown")
        return deadline
    def _io_timeout(self, deadline):
        remaining = deadline - self.clock()
        if remaining <= 0:
            raise ReceiveFailure("network-deadline-unknown")
        return min(remaining, self.io_seconds) if self.io_seconds is not None else remaining
    def _write(self, data, deadline, *, full_legacy_wait=False):
        if self.max_writes is not None and self.write_count >= self.max_writes:
            raise ReceiveFailure("outgoing-write-limit")
        self.write_count += 1
        timeout = (self.wait if full_legacy_wait and self.network_deadline is None
                   and self.io_seconds is None else self._io_timeout(deadline))
        self.stream.write(data, timeout)
    def send(self, envelope, *, reserve_cleanup=False):
        method = envelope.get("method")
        if self.allowed_methods is not None and method not in self.allowed_methods:
            raise ReceiveFailure("outgoing-method-forbidden")
        legacy_timing = self.network_deadline is None and self.io_seconds is None
        if self.stream is None:
            if legacy_timing:
                timeout = self.wait
            else:
                deadline = self._phase_deadline(reserve_cleanup=reserve_cleanup)
                timeout = self._io_timeout(deadline)
            self.stream = self.connector(self.endpoint, timeout)
        # Diagnostic mode keeps one constructor-owned network budget. Legacy
        # mode starts its response window after required pre-write work.
        if not legacy_timing:
            deadline = self._phase_deadline(reserve_cleanup=reserve_cleanup)
        if envelope['method'] in {'thread-follower-steer-turn', 'thread-follower-start-turn'}:
            if self.pending_path is None or not self.pending_path.is_file():
                raise ReceiveFailure('missing-pre-write-capture')
            self.write_boundary = {'pendingExistedBeforeWrite': True,
                                   'pendingSha256': hashlib.sha256(self.pending_path.read_bytes()).hexdigest()}
        data = json.dumps(envelope, separators=(',', ':')).encode()
        self._check_outgoing_frame(data)
        self.outbound.append(envelope)
        if legacy_timing:
            deadline = self._phase_deadline(reserve_cleanup=reserve_cleanup)
        self._write(struct.pack('<I', len(data)) + data, deadline, full_legacy_wait=True)
        if self.receiver.incomplete:
            self.receive_status.append('receive-disabled:' + self.receiver.incomplete)
            return []
        records = []
        try:
            while self.clock() < deadline:
                message = self.receiver.receive(
                    lambda maximum, timeout: self.stream.read(
                        maximum, min(timeout, self.io_seconds)
                        if self.io_seconds is not None else timeout),
                    self.clock, deadline,
                )
                record = {'at': self.clock(), 'generation': self.generation}
                if self.receipt_clock is not None:
                    record['receivedAtUnixNs'] = self.receipt_clock()
                records.append((record, message))
                self.retained.append((record, message))
                if message.get('type') == 'client-discovery-request':
                    if 'requestId' not in message:
                        self.receiver.incomplete = 'discovery-request-id-missing'
                        raise ReceiveFailure(self.receiver.incomplete)
                    answer = {'type': 'client-discovery-response', 'requestId': message['requestId'],
                              'response': {'canHandle': False}}
                    body = json.dumps(answer).encode()
                    self._check_outgoing_frame(body)
                    self._write(struct.pack('<I', len(body)) + body, deadline)
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


def discover_owner(transport, binding, *, text, refusal, record_consumer=None, exchange=None):
    """Initialize and bind the exact target's owner on this connection.

    Populate binding["owner"] as soon as the correlated discovery proves it,
    preserving that acquired prefix even if an incomplete frame then refuses.
    Caller-supplied text validation and refusal keep its diagnostic contract.
    This does not select a turn operation or establish authenticated identity.
    """
    send = exchange or transport.send
    records = send({
        "type": "request", "requestId": "initialize", "version": 0,
        "method": "initialize", "params": {"clientType": "cli"},
    })
    matches = [message for _, message in records
               if message.get("type") == "response"
               and message.get("requestId") == "initialize"
               and message.get("method") == "initialize"
               and message.get("resultType") == "success"]
    result = matches[0].get("result") if len(matches) == 1 else None
    if len(matches) != 1 or not isinstance(result, dict):
        if record_consumer is not None:
            record_consumer(records)
        raise refusal("initialize-unavailable")
    client_error = None
    try:
        client = text(result.get("clientId"), "native-client")
    except Exception as error:
        if record_consumer is None:
            raise
        client = None
        client_error = error
    if record_consumer is not None:
        if client is not None:
            binding["client"] = client
        try:
            record_consumer(records)
        finally:
            binding.pop("client", None)
    if client_error is not None:
        raise client_error
    records = send({
        "type": "request", "requestId": "owner", "sourceClientId": client,
        "version": 1, "method": "thread-owner-discovery",
        "params": {"hostId": binding.get("host", "local"), "conversationId": binding["target"]},
    })
    matches = [message for _, message in records
               if message.get("type") == "response"
               and message.get("requestId") == "owner"
               and message.get("method") == "thread-owner-discovery"
               and message.get("resultType") == "success"]
    owner = matches[0].get("handledByClientId") if len(matches) == 1 else None
    if isinstance(owner, str) and owner.strip():
        binding["owner"] = owner
    if record_consumer is not None:
        binding["client"] = client
        try:
            record_consumer(records)
        finally:
            binding.pop("client", None)
    if len(matches) != 1:
        raise refusal("owner-unavailable")
    binding["owner"] = text(owner, "native-owner")
    if transport.receiver.incomplete is not None:
        raise refusal("connection-incomplete-before-write")
    return client
