from __future__ import annotations

import argparse
from pathlib import Path
import time

import mujoco
import mujoco.viewer
import numpy as np

from sonic_telemetry import SonicPhysicalPoseSubscriber, SonicPose, SonicTelemetrySubscriber


ROOT = Path(__file__).resolve().parent
DEFAULT_MODEL = ROOT / "third_party/unitree_rl_gym/resources/robots/g1_description/g1_29dof_with_hand_rev_1_0.xml"

BODY_JOINTS = (
    "left_hip_pitch_joint", "left_hip_roll_joint", "left_hip_yaw_joint",
    "left_knee_joint", "left_ankle_pitch_joint", "left_ankle_roll_joint",
    "right_hip_pitch_joint", "right_hip_roll_joint", "right_hip_yaw_joint",
    "right_knee_joint", "right_ankle_pitch_joint", "right_ankle_roll_joint",
    "waist_yaw_joint", "waist_roll_joint", "waist_pitch_joint",
    "left_shoulder_pitch_joint", "left_shoulder_roll_joint", "left_shoulder_yaw_joint",
    "left_elbow_joint", "left_wrist_roll_joint", "left_wrist_pitch_joint", "left_wrist_yaw_joint",
    "right_shoulder_pitch_joint", "right_shoulder_roll_joint", "right_shoulder_yaw_joint",
    "right_elbow_joint", "right_wrist_roll_joint", "right_wrist_pitch_joint", "right_wrist_yaw_joint",
)
LEFT_HAND_JOINTS = (
    "left_hand_thumb_0_joint", "left_hand_thumb_1_joint", "left_hand_thumb_2_joint",
    "left_hand_middle_0_joint", "left_hand_middle_1_joint",
    "left_hand_index_0_joint", "left_hand_index_1_joint",
)
RIGHT_HAND_JOINTS = tuple(name.replace("left_", "right_", 1) for name in LEFT_HAND_JOINTS)


def joint_qpos_addresses(model: mujoco.MjModel, names: tuple[str, ...]) -> np.ndarray:
    addresses = []
    for name in names:
        joint_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, name)
        if joint_id < 0:
            raise ValueError(f"El modelo no contiene {name}")
        addresses.append(model.jnt_qposadr[joint_id])
    return np.asarray(addresses, dtype=np.int32)


def apply_pose(
    data: mujoco.MjData,
    pose: SonicPose,
    body_addresses: np.ndarray,
    left_hand_addresses: np.ndarray,
    right_hand_addresses: np.ndarray,
    physical_position: np.ndarray,
    physical_quaternion: np.ndarray,
) -> None:
    data.qpos[:3] = physical_position
    data.qpos[3:7] = physical_quaternion
    data.qpos[body_addresses] = pose.body_q
    data.qpos[left_hand_addresses] = pose.left_hand_q
    data.qpos[right_hand_addresses] = pose.right_hand_q


def main() -> None:
    parser = argparse.ArgumentParser(description="Visor local para telemetria NVIDIA GEAR-SONIC")
    parser.add_argument("--url", default="tcp://127.0.0.1:5557")
    parser.add_argument("--topic", default="g1_debug")
    parser.add_argument("--physical-url", default="tcp://127.0.0.1:5558")
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--timeout", type=float, default=5.0)
    args = parser.parse_args()

    model = mujoco.MjModel.from_xml_path(str(args.model))
    data = mujoco.MjData(model)
    body_addresses = joint_qpos_addresses(model, BODY_JOINTS)
    left_hand_addresses = joint_qpos_addresses(model, LEFT_HAND_JOINTS)
    right_hand_addresses = joint_qpos_addresses(model, RIGHT_HAND_JOINTS)

    subscriber = SonicTelemetrySubscriber(args.url, args.topic)
    physical_subscriber = SonicPhysicalPoseSubscriber(args.physical_url)
    subscriber.start()
    physical_subscriber.start()
    deadline = time.monotonic() + args.timeout
    while (subscriber.latest() is None or physical_subscriber.latest() is None) and time.monotonic() < deadline:
        error = subscriber.error() or physical_subscriber.error()
        if error is not None:
            subscriber.close()
            raise error
        time.sleep(0.02)
    if subscriber.latest() is None or physical_subscriber.latest() is None:
        subscriber.close()
        physical_subscriber.close()
        raise TimeoutError(f"No llego toda la telemetria desde {args.url} y {args.physical_url}")

    print("SONIC conectado. Posicion global, orientacion y joints provienen del estado fisico medido.")
    try:
        with mujoco.viewer.launch_passive(model, data, show_left_ui=False, show_right_ui=False) as viewer:
            viewer.cam.distance = 3.0
            viewer.cam.azimuth = 135.0
            viewer.cam.elevation = -15.0
            initial_physical_pose = physical_subscriber.latest()
            if initial_physical_pose is not None:
                viewer.cam.lookat[:] = initial_physical_pose.position
            last_index = -1
            while viewer.is_running():
                frame_start = time.monotonic()
                error = subscriber.error() or physical_subscriber.error()
                if error is not None:
                    raise error
                pose = subscriber.latest()
                physical_pose = physical_subscriber.latest()
                if pose is not None and physical_pose is not None:
                    apply_pose(
                        data,
                        pose,
                        body_addresses,
                        left_hand_addresses,
                        right_hand_addresses,
                        physical_pose.position,
                        physical_pose.quaternion,
                    )
                    mujoco.mj_forward(model, data)
                    last_index = pose.index
                viewer.sync()
                if pose is not None and time.monotonic() - pose.received_at > args.timeout:
                    print(f"Telemetria detenida despues del frame {last_index}")
                    break
                remaining = 1.0 / 60.0 - (time.monotonic() - frame_start)
                if remaining > 0:
                    time.sleep(remaining)
    finally:
        subscriber.close()
        physical_subscriber.close()


if __name__ == "__main__":
    main()