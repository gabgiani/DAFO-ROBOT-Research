from __future__ import annotations

import argparse
import json
import math
import struct
import time

import zmq


HEADER_SIZE = 1280
IDLE = 0
SLOW_WALK = 1

MOVEMENTS = {
    "forward": (1.0, 0.0, 0.0),
    "backward": (-1.0, 0.0, 0.0),
    "left": (0.0, 1.0, 0.0),
    "right": (0.0, -1.0, 0.0),
}


def pack_message(topic: str, fields: list[dict[str, object]], payload: bytes) -> bytes:
    header = json.dumps({"v": 1, "endian": "le", "count": 1, "fields": fields}).encode("utf-8")
    if len(header) > HEADER_SIZE:
        raise ValueError("El encabezado ZMQ excede el limite de SONIC")
    return topic.encode("ascii") + header.ljust(HEADER_SIZE, b"\0") + payload


def command_message(*, start: bool, stop: bool) -> bytes:
    fields = [
        {"name": "start", "dtype": "u8", "shape": [1]},
        {"name": "stop", "dtype": "u8", "shape": [1]},
        {"name": "planner", "dtype": "u8", "shape": [1]},
    ]
    return pack_message("command", fields, struct.pack("BBB", start, stop, True))


def planner_message(
    mode: int,
    movement: tuple[float, float, float],
    facing: tuple[float, float, float],
    speed: float,
    upper_body_position: tuple[float, ...] | None = None,
    upper_body_velocity: tuple[float, ...] | None = None,
) -> bytes:
    fields = [
        {"name": "mode", "dtype": "i32", "shape": [1]},
        {"name": "movement", "dtype": "f32", "shape": [3]},
        {"name": "facing", "dtype": "f32", "shape": [3]},
        {"name": "speed", "dtype": "f32", "shape": [1]},
        {"name": "height", "dtype": "f32", "shape": [1]},
    ]
    if upper_body_position is not None:
        if len(upper_body_position) != 17:
            raise ValueError("upper_body_position debe contener 17 valores")
        fields.append({"name": "upper_body_position", "dtype": "f32", "shape": [17]})
    if upper_body_velocity is not None:
        if len(upper_body_velocity) != 17:
            raise ValueError("upper_body_velocity debe contener 17 valores")
        fields.append({"name": "upper_body_velocity", "dtype": "f32", "shape": [17]})
    payload = struct.pack("<i3f3f2f", mode, *movement, *facing, speed, -1.0)
    if upper_body_position is not None:
        payload += struct.pack("<17f", *upper_body_position)
    if upper_body_velocity is not None:
        payload += struct.pack("<17f", *upper_body_velocity)
    return pack_message("planner", fields, payload)


def main() -> None:
    parser = argparse.ArgumentParser(description="Envia controles al planner SONIC remoto")
    parser.add_argument("command", choices=("activate", "deactivate", "stop", "forward", "backward", "left", "right", "turn-left", "turn-right"))
    parser.add_argument("--bind", default="tcp://127.0.0.1:5556")
    parser.add_argument("--duration", type=float, default=1.0)
    parser.add_argument("--speed", type=float, default=0.3)
    args = parser.parse_args()

    if args.duration <= 0:
        parser.error("--duration debe ser mayor que cero")
    if not 0.1 <= args.speed <= 0.8:
        parser.error("--speed debe estar entre 0.1 y 0.8 m/s para SLOW_WALK")

    context = zmq.Context()
    publisher = context.socket(zmq.PUB)
    publisher.setsockopt(zmq.LINGER, 0)
    publisher.bind(args.bind)
    time.sleep(0.6)

    if args.command == "deactivate":
        message = command_message(start=False, stop=True)
        for _ in range(5):
            publisher.send(message)
            time.sleep(0.05)
    elif args.command == "activate":
        message = command_message(start=True, stop=False)
        idle = planner_message(IDLE, (0.0, 0.0, 0.0), (1.0, 0.0, 0.0), -1.0)
        for _ in range(10):
            publisher.send(message)
            publisher.send(idle)
            time.sleep(0.05)
    else:
        movement = MOVEMENTS.get(args.command, (0.0, 0.0, 0.0))
        facing = (1.0, 0.0, 0.0)
        if args.command == "turn-left":
            facing = (math.cos(math.pi / 6), math.sin(math.pi / 6), 0.0)
        elif args.command == "turn-right":
            facing = (math.cos(-math.pi / 6), math.sin(-math.pi / 6), 0.0)
        mode = IDLE if args.command == "stop" else SLOW_WALK
        speed = -1.0 if mode == IDLE else args.speed
        active = planner_message(mode, movement, facing, speed)
        deadline = time.monotonic() + (0.4 if mode == IDLE else args.duration)
        while time.monotonic() < deadline:
            publisher.send(active)
            time.sleep(0.05)
        idle = planner_message(IDLE, (0.0, 0.0, 0.0), facing, -1.0)
        for _ in range(5):
            publisher.send(idle)
            time.sleep(0.05)

    publisher.close()
    context.term()
    print(f"SONIC: {args.command}")


if __name__ == "__main__":
    main()