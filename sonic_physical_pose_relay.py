from __future__ import annotations

import argparse
import signal
import threading

import msgpack
import zmq
from unitree_sdk2py.core.channel import ChannelFactoryInitialize, ChannelSubscriber
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import OdoState_


def main() -> None:
    parser = argparse.ArgumentParser(description="Relay de odometria fisica MuJoCo para el visor SONIC")
    parser.add_argument("--interface", default="lo")
    parser.add_argument("--domain", type=int, default=0)
    parser.add_argument("--bind", default="tcp://127.0.0.1:5558")
    args = parser.parse_args()

    context = zmq.Context()
    publisher = context.socket(zmq.PUB)
    publisher.setsockopt(zmq.SNDHWM, 1)
    publisher.setsockopt(zmq.LINGER, 0)
    publisher.bind(args.bind)

    ChannelFactoryInitialize(args.domain, args.interface)

    def publish(message: OdoState_) -> None:
        payload = msgpack.packb(
            {
                "tick": int(message.tick),
                "position": list(message.position),
                "orientation": list(message.orientation),
                "linear_velocity": list(message.linear_velocity),
                "angular_velocity": list(message.angular_velocity),
            },
            use_bin_type=True,
        )
        publisher.send(b"physical_pose" + payload)

    subscriber = ChannelSubscriber("rt/odostate", OdoState_)
    subscriber.Init(publish, 1)

    stopping = threading.Event()
    signal.signal(signal.SIGINT, lambda *_: stopping.set())
    signal.signal(signal.SIGTERM, lambda *_: stopping.set())
    print(f"Odometria fisica publicada en {args.bind}", flush=True)
    stopping.wait()
    publisher.close()
    context.term()


if __name__ == "__main__":
    main()