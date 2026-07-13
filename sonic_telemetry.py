from __future__ import annotations

from dataclasses import dataclass
import threading
import time
from typing import Any

import msgpack
import numpy as np
import zmq


@dataclass(frozen=True)
class SonicPose:
    received_at: float
    index: int
    base_position: np.ndarray
    base_quaternion: np.ndarray
    body_q: np.ndarray
    left_hand_q: np.ndarray
    right_hand_q: np.ndarray
    target_base_position: np.ndarray
    target_base_quaternion: np.ndarray
    target_body_q: np.ndarray


@dataclass(frozen=True)
class SonicPhysicalPose:
    received_at: float
    tick: int
    position: np.ndarray
    quaternion: np.ndarray
    linear_velocity: np.ndarray
    angular_velocity: np.ndarray


def decode_pose(payload: bytes) -> SonicPose:
    message: dict[str, Any] = msgpack.unpackb(payload, raw=False)

    body_q = np.asarray(message["body_q_measured"], dtype=np.float64)
    left_hand_q = np.asarray(message["left_hand_q_measured"], dtype=np.float64)
    right_hand_q = np.asarray(message["right_hand_q_measured"], dtype=np.float64)
    base_quaternion = np.asarray(message["base_quat_measured"], dtype=np.float64)
    target_base_position = np.asarray(message["base_trans_target"], dtype=np.float64)
    target_base_quaternion = np.asarray(message["base_quat_target"], dtype=np.float64)
    target_body_q = np.asarray(message["body_q_target"], dtype=np.float64)

    expected_shapes = {
        "body_q_measured": (body_q, (29,)),
        "left_hand_q_measured": (left_hand_q, (7,)),
        "right_hand_q_measured": (right_hand_q, (7,)),
        "base_quat_measured": (base_quaternion, (4,)),
        "base_trans_target": (target_base_position, (3,)),
        "base_quat_target": (target_base_quaternion, (4,)),
        "body_q_target": (target_body_q, (29,)),
    }
    for field, (value, expected_shape) in expected_shapes.items():
        if value.shape != expected_shape:
            raise ValueError(f"{field} tiene forma {value.shape}; se esperaba {expected_shape}")

    return SonicPose(
        received_at=time.monotonic(),
        index=int(message["index"]),
        base_position=target_base_position.copy(),
        base_quaternion=base_quaternion,
        body_q=body_q,
        left_hand_q=left_hand_q,
        right_hand_q=right_hand_q,
        target_base_position=target_base_position,
        target_base_quaternion=target_base_quaternion,
        target_body_q=target_body_q,
    )


class SonicTelemetrySubscriber:
    def __init__(self, url: str, topic: str = "g1_debug"):
        self._url = url
        self._topic = topic.encode("ascii")
        self._context = zmq.Context()
        self._socket = self._context.socket(zmq.SUB)
        self._socket.setsockopt(zmq.SUBSCRIBE, self._topic)
        self._socket.setsockopt(zmq.RCVHWM, 1)
        self._socket.setsockopt(zmq.CONFLATE, 1)
        self._socket.connect(url)
        self._lock = threading.Lock()
        self._latest: SonicPose | None = None
        self._error: Exception | None = None
        self._stopping = threading.Event()
        self._thread = threading.Thread(target=self._receive, name="sonic-telemetry", daemon=True)

    def start(self) -> None:
        self._thread.start()

    def latest(self) -> SonicPose | None:
        with self._lock:
            return self._latest

    def error(self) -> Exception | None:
        with self._lock:
            return self._error

    def close(self) -> None:
        self._stopping.set()
        self._thread.join(timeout=1.0)
        self._socket.close(linger=0)
        self._context.term()

    def _receive(self) -> None:
        poller = zmq.Poller()
        poller.register(self._socket, zmq.POLLIN)
        try:
            while not self._stopping.is_set():
                if self._socket not in dict(poller.poll(100)):
                    continue
                packet = self._socket.recv()
                if not packet.startswith(self._topic):
                    continue
                pose = decode_pose(packet[len(self._topic) :])
                with self._lock:
                    self._latest = pose
        except Exception as exc:
            with self._lock:
                self._error = exc


class SonicPhysicalPoseSubscriber:
    def __init__(self, url: str, topic: str = "physical_pose"):
        self._url = url
        self._topic = topic.encode("ascii")
        self._context = zmq.Context()
        self._socket = self._context.socket(zmq.SUB)
        self._socket.setsockopt(zmq.SUBSCRIBE, self._topic)
        self._socket.setsockopt(zmq.RCVHWM, 1)
        self._socket.setsockopt(zmq.CONFLATE, 1)
        self._socket.connect(url)
        self._lock = threading.Lock()
        self._latest: SonicPhysicalPose | None = None
        self._error: Exception | None = None
        self._stopping = threading.Event()
        self._thread = threading.Thread(target=self._receive, name="sonic-physical-pose", daemon=True)

    def start(self) -> None:
        self._thread.start()

    def latest(self) -> SonicPhysicalPose | None:
        with self._lock:
            return self._latest

    def error(self) -> Exception | None:
        with self._lock:
            return self._error

    def close(self) -> None:
        self._stopping.set()
        self._thread.join(timeout=1.0)
        self._socket.close(linger=0)
        self._context.term()

    def _receive(self) -> None:
        poller = zmq.Poller()
        poller.register(self._socket, zmq.POLLIN)
        try:
            while not self._stopping.is_set():
                if self._socket not in dict(poller.poll(100)):
                    continue
                packet = self._socket.recv()
                if not packet.startswith(self._topic):
                    continue
                message: dict[str, Any] = msgpack.unpackb(packet[len(self._topic) :], raw=False)
                values = {
                    name: np.asarray(message[name], dtype=np.float64)
                    for name in ("position", "orientation", "linear_velocity", "angular_velocity")
                }
                expected_shapes = {
                    "position": (3,),
                    "orientation": (4,),
                    "linear_velocity": (3,),
                    "angular_velocity": (3,),
                }
                for name, expected_shape in expected_shapes.items():
                    if values[name].shape != expected_shape:
                        raise ValueError(f"{name} tiene forma {values[name].shape}; se esperaba {expected_shape}")
                pose = SonicPhysicalPose(
                    received_at=time.monotonic(),
                    tick=int(message["tick"]),
                    position=values["position"],
                    quaternion=values["orientation"],
                    linear_velocity=values["linear_velocity"],
                    angular_velocity=values["angular_velocity"],
                )
                with self._lock:
                    self._latest = pose
        except Exception as exc:
            with self._lock:
                self._error = exc


def receive_one(url: str, topic: str = "g1_debug", timeout_seconds: float = 5.0) -> SonicPose:
    subscriber = SonicTelemetrySubscriber(url, topic)
    subscriber.start()
    deadline = time.monotonic() + timeout_seconds
    try:
        while time.monotonic() < deadline:
            error = subscriber.error()
            if error is not None:
                raise error
            pose = subscriber.latest()
            if pose is not None:
                return pose
            time.sleep(0.02)
    finally:
        subscriber.close()
    raise TimeoutError(f"No se recibio {topic!r} desde {url} en {timeout_seconds:.1f} s")