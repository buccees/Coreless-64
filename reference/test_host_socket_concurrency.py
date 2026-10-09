import threading

from host_socket import SocketNetworkTransport


class BlockingSendSocket:
    """A socket double that exposes concurrent sendall entry deterministically."""

    def __init__(self):
        self.first_entered = threading.Event()
        self.release_first = threading.Event()
        self.second_entered = threading.Event()
        self.frames = []
        self._lock = threading.Lock()
        self._calls = 0

    def sendall(self, data):
        with self._lock:
            self._calls += 1
            call_number = self._calls
        if call_number == 1:
            self.first_entered.set()
            if not self.release_first.wait(timeout=2):
                raise TimeoutError("test did not release the first send")
        elif call_number == 2:
            self.second_entered.set()
        with self._lock:
            self.frames.append(bytes(data))

    def recv(self, size):
        raise AssertionError("recv should not be called")

    def close(self):
        pass


def test_concurrent_sends_serialize_complete_packet_frames():
    sock = BlockingSendSocket()
    transport = SocketNetworkTransport(sock)
    errors = []

    def send(packet):
        try:
            transport.send_packet(packet)
        except BaseException as exc:
            errors.append(exc)

    first = threading.Thread(target=send, args=(b"first-frame",))
    second = threading.Thread(target=send, args=(b"second-frame",))
    first.start()
    assert sock.first_entered.wait(timeout=2), "first send did not start"
    second.start()

    try:
        # The second caller must not enter socket.sendall while the first
        # complete frame is still being written.
        assert not sock.second_entered.wait(timeout=0.05)
    finally:
        sock.release_first.set()
        first.join(timeout=2)
        second.join(timeout=2)
        transport.close()

    assert not first.is_alive()
    assert not second.is_alive()
    assert errors == []
    assert sock.frames == [
        b"\x00\x00\x00\x0bfirst-frame",
        b"\x00\x00\x00\x0csecond-frame",
    ]
