from __future__ import annotations

import argparse
import math
import time
import tkinter as tk
from tkinter import ttk

import zmq

from sonic_remote_control import IDLE, SLOW_WALK, command_message, planner_message


PUBLISH_INTERVAL_MS = 50
FACING_ANGLE = math.pi / 6
ARM_SWING_AMPLITUDE = 0.35
ARM_SWING_FREQUENCY = 0.85
ARM_TRANSITION_SPEED = 1.2
CARRY_POSITION = (
    0.0, 0.0, 0.0,
    -0.75, -0.75,
    0.15, -0.15,
    0.0, 0.0,
    1.20, 1.20,
    0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
)


class SonicTeleop:
    def __init__(self, root: tk.Tk, bind: str, initial_speed: float) -> None:
        self.root = root
        self.speed = tk.DoubleVar(value=initial_speed)
        self.arm_mode = tk.StringVar(value="normal")
        self.status = tk.StringVar(value="Detenido")
        self.pressed: set[str] = set()
        self.active = False
        self.activation_frames = 0
        self.closed = False
        self.arm_position = [0.0] * 17
        self.arm_update_time = time.monotonic()
        self.arm_mode_started_at = self.arm_update_time

        self.context = zmq.Context()
        self.publisher = self.context.socket(zmq.PUB)
        self.publisher.setsockopt(zmq.LINGER, 0)
        self.publisher.bind(bind)

        self._build_ui()
        self.root.bind_all("<KeyPress>", self._on_key_press)
        self.root.bind_all("<KeyRelease>", self._on_key_release)
        self.root.bind("<FocusOut>", self._on_focus_out)
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.after(600, self._publish_loop)

    def _build_ui(self) -> None:
        self.root.title("Telecomando SONIC")
        self.root.geometry("640x570")
        self.root.minsize(600, 540)

        outer = ttk.Frame(self.root, padding=20)
        outer.pack(fill="both", expand=True)

        title = ttk.Label(outer, text="Telecomando SONIC", font=("Sans", 20, "bold"))
        title.pack(anchor="w")
        ttk.Label(outer, textvariable=self.status, font=("Sans", 12)).pack(anchor="w", pady=(2, 16))

        actions = ttk.Frame(outer)
        actions.pack(fill="x", pady=(0, 16))
        ttk.Button(actions, text="Activar", command=self.activate).pack(side="left")
        ttk.Button(actions, text="Detener", command=self.stop).pack(side="left", padx=8)
        ttk.Button(actions, text="Desactivar", command=self.deactivate).pack(side="left")

        controls = ttk.Frame(outer)
        controls.pack(fill="both", expand=True)

        movement = ttk.LabelFrame(controls, text="Movimiento", padding=12)
        movement.pack(side="left", fill="both", expand=True, padx=(0, 8))
        self._motion_button(movement, "Avanzar\nW / ↑", "forward", 0, 1)
        self._motion_button(movement, "Izquierda\nQ", "left", 1, 0)
        self._motion_button(movement, "PARAR\nEspacio", "stop", 1, 1)
        self._motion_button(movement, "Derecha\nE", "right", 1, 2)
        self._motion_button(movement, "Retroceder\nS / ↓", "backward", 2, 1)

        turning = ttk.LabelFrame(controls, text="Giro", padding=12)
        turning.pack(side="left", fill="both", expand=True, padx=(8, 0))
        self._motion_button(turning, "Girar izquierda\nA / ←", "turn-left", 0, 0)
        self._motion_button(turning, "Girar derecha\nD / →", "turn-right", 0, 1)

        speed_frame = ttk.LabelFrame(outer, text="Velocidad", padding=12)
        speed_frame.pack(fill="x", pady=(16, 0))
        ttk.Scale(speed_frame, from_=0.1, to=0.8, variable=self.speed, orient="horizontal").pack(
            side="left", fill="x", expand=True
        )
        ttk.Label(speed_frame, textvariable=self.speed, width=5).pack(side="left", padx=(12, 0))

        arms = ttk.LabelFrame(outer, text="Posición de brazos", padding=12)
        arms.pack(fill="x", pady=(12, 0))
        for text, value in (
            ("Brazos abajo", "normal"),
            ("Cargar", "carry"),
            ("Caminar natural", "natural"),
        ):
            ttk.Radiobutton(
                arms,
                text=text,
                value=value,
                variable=self.arm_mode,
                command=self._set_arm_mode,
            ).pack(side="left", expand=True)

        ttk.Label(
            outer,
            text="Mantén pulsado para moverte. Al soltar o perder foco, el robot se detiene.",
        ).pack(anchor="w", pady=(14, 0))

    def _motion_button(self, parent: ttk.LabelFrame, text: str, motion: str, row: int, column: int) -> None:
        button = ttk.Button(parent, text=text)
        button.grid(row=row, column=column, padx=5, pady=5, sticky="nsew")
        parent.columnconfigure(column, weight=1)
        parent.rowconfigure(row, weight=1)
        if motion == "stop":
            button.configure(command=self.stop)
            return
        button.bind("<ButtonPress-1>", lambda _event: self._press(motion))
        button.bind("<ButtonRelease-1>", lambda _event: self._release(motion))
        button.bind("<Leave>", lambda _event: self._release(motion))

    def activate(self) -> None:
        self.active = True
        self.activation_frames = 10
        self.status.set("Activo · detenido")

    def deactivate(self) -> None:
        self.stop()
        message = command_message(start=False, stop=True)
        for _ in range(5):
            self.publisher.send(message)
        self.active = False
        self.activation_frames = 0
        self.status.set("Desactivado")

    def stop(self) -> None:
        self.pressed.clear()
        for _ in range(5):
            self.publisher.send(self._idle_message())
        self.status.set("Activo · detenido" if self.active else "Detenido")

    def _press(self, motion: str) -> None:
        if not self.active:
            self.status.set("Activa SONIC antes de moverte")
            return
        self.pressed.add(motion)

    def _release(self, motion: str) -> None:
        self.pressed.discard(motion)
        if not self.pressed:
            self.publisher.send(self._idle_message())

    def _on_key_press(self, event: tk.Event) -> None:
        key = event.keysym.lower()
        if key == "space":
            self.stop()
            return
        motion = {
            "w": "forward",
            "up": "forward",
            "s": "backward",
            "down": "backward",
            "q": "left",
            "e": "right",
            "a": "turn-left",
            "left": "turn-left",
            "d": "turn-right",
            "right": "turn-right",
        }.get(key)
        if motion is not None:
            self._press(motion)

    def _on_key_release(self, event: tk.Event) -> None:
        motion = {
            "w": "forward",
            "up": "forward",
            "s": "backward",
            "down": "backward",
            "q": "left",
            "e": "right",
            "a": "turn-left",
            "left": "turn-left",
            "d": "turn-right",
            "right": "turn-right",
        }.get(event.keysym.lower())
        if motion is not None:
            self._release(motion)

    def _on_focus_out(self, _event: tk.Event) -> None:
        if self.pressed:
            self.stop()

    def _idle_message(self) -> bytes:
        position, velocity = self._arm_targets(moving=False)
        return planner_message(
            IDLE,
            (0.0, 0.0, 0.0),
            (1.0, 0.0, 0.0),
            -1.0,
            position,
            velocity,
        )

    def _set_arm_mode(self) -> None:
        self.arm_mode_started_at = time.monotonic()
        for _ in range(5):
            self.publisher.send(self._idle_message())
        labels = {"normal": "brazos abajo", "carry": "cargar", "natural": "caminar natural"}
        self.status.set(f"Brazos: {labels[self.arm_mode.get()]}")

    def _arm_targets(self, *, moving: bool) -> tuple[tuple[float, ...], tuple[float, ...]]:
        now = time.monotonic()
        elapsed = max(now - self.arm_update_time, 1e-6)
        desired = [0.0] * 17
        if self.arm_mode.get() == "carry":
            desired[:] = CARRY_POSITION
        elif self.arm_mode.get() == "natural" and moving:
            omega = 2.0 * math.pi * ARM_SWING_FREQUENCY
            phase = omega * (now - self.arm_mode_started_at)
            swing = ARM_SWING_AMPLITUDE * math.sin(phase)
            desired[3] = swing
            desired[4] = -swing

        max_step = ARM_TRANSITION_SPEED * elapsed
        velocity = [0.0] * 17
        for index, target in enumerate(desired):
            delta = max(-max_step, min(max_step, target - self.arm_position[index]))
            self.arm_position[index] += delta
            velocity[index] = delta / elapsed
        self.arm_update_time = now
        return tuple(self.arm_position), tuple(velocity)

    def _motion_message(self) -> tuple[bytes, str]:
        forward = float("forward" in self.pressed) - float("backward" in self.pressed)
        lateral = float("left" in self.pressed) - float("right" in self.pressed)
        turn = float("turn-left" in self.pressed) - float("turn-right" in self.pressed)
        magnitude = math.hypot(forward, lateral)
        movement = (forward / max(1.0, magnitude), lateral / max(1.0, magnitude), 0.0)
        facing = (math.cos(turn * FACING_ANGLE), math.sin(turn * FACING_ANGLE), 0.0)
        upper_body_position, upper_body_velocity = self._arm_targets(moving=True)
        labels = sorted(self.pressed)
        return planner_message(
            SLOW_WALK,
            movement,
            facing,
            self.speed.get(),
            upper_body_position,
            upper_body_velocity,
        ), " + ".join(labels)

    def _publish_loop(self) -> None:
        if self.closed:
            return
        if self.activation_frames:
            self.publisher.send(command_message(start=True, stop=False))
            self.activation_frames -= 1
        if self.active and self.pressed:
            message, description = self._motion_message()
            self.publisher.send(message)
            self.status.set(f"Activo · {description} · {self.speed.get():.2f} m/s")
        elif self.active:
            self.publisher.send(self._idle_message())
        self.root.after(PUBLISH_INTERVAL_MS, self._publish_loop)

    def close(self) -> None:
        if self.closed:
            return
        self.stop()
        self.closed = True
        self.publisher.close()
        self.context.term()
        self.root.destroy()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Telecomando grafico para SONIC")
    parser.add_argument("--bind", default="tcp://127.0.0.1:5556")
    parser.add_argument("--speed", type=float, default=0.3)
    args = parser.parse_args()
    if not 0.1 <= args.speed <= 0.8:
        parser.error("--speed debe estar entre 0.1 y 0.8 m/s")
    return args


def main() -> None:
    args = parse_args()
    root = tk.Tk()
    SonicTeleop(root, args.bind, args.speed)
    root.mainloop()


if __name__ == "__main__":
    main()