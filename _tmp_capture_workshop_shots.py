"""Descartable: corre cada etapa del workshop headless y guarda screenshots para la doc.

No abre viewer (no necesita mjpython). Usa mujoco.Renderer para renderizar offscreen
en puntos clave de cada etapa: caminata normal, caida (etapa 1) y contacto con objetos
(etapa 3).
"""
from __future__ import annotations

from pathlib import Path

import mujoco
import numpy as np
from PIL import Image

from simulate_unitree import resolve_scene_path, compile_model, apply_keyframe
from interactive_unitree import PassiveUnitreeSimulator
from simulate_g1_rl import G1RLWalker, ASSET_ROOT

ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "artifacts" / "workshop"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def render_tracking(model, data, pelvis_id, out_path, distance=3.35, elevation=-14, azimuth=145):
    # mjCAMERA_TRACKING no actualiza el lookat de forma confiable a traves de un
    # solo mujoco.Renderer.update_scene() (eso lo maneja frame a frame el viewer
    # interactivo). Usamos en cambio una camara libre con lookat = posicion actual
    # de la pelvis, que da el mismo encuadre "siguiendo al robot" de forma directa.
    renderer = mujoco.Renderer(model, height=480, width=640)
    cam = mujoco.MjvCamera()
    cam.lookat[:] = data.xpos[pelvis_id]
    cam.distance = distance
    cam.elevation = elevation
    cam.azimuth = azimuth
    renderer.update_scene(data, camera=cam)
    Image.fromarray(renderer.render()).save(out_path)
    renderer.close()
    print(f"guardado {out_path}")


def render_static(model, data, out_path, lookat, distance, elevation, azimuth):
    renderer = mujoco.Renderer(model, height=480, width=640)
    cam = mujoco.MjvCamera()
    cam.lookat[:] = lookat
    cam.distance = distance
    cam.elevation = elevation
    cam.azimuth = azimuth
    renderer.update_scene(data, camera=cam)
    Image.fromarray(renderer.render()).save(out_path)
    renderer.close()
    print(f"guardado {out_path}")


def stage1_step(sim: PassiveUnitreeSimulator, model, data) -> None:
    sim._update_drive_state()
    if sim._drive_active():
        sim._advance_phase(model.opt.timestep)
        snapshot = sim._read_sensor_snapshot(model.opt.timestep)
        sim._apply_walk_targets(snapshot)
        sim._apply_drive_assist(snapshot)
    else:
        data.ctrl[:] = sim._base_ctrl
        sim._clear_drive_assist()
        sim._read_sensor_snapshot(model.opt.timestep)
    mujoco.mj_step(model, data)


def capture_stage1() -> None:
    print("== Etapa 1: control heuristico ==")
    scene_path = resolve_scene_path("g1-hands", None)
    model, data = compile_model(scene_path)
    apply_keyframe(model, data, "home")
    sim = PassiveUnitreeSimulator(model, data, "home")

    # Comando de avance sostenido sin correccion humana (nadie ajusta giro/amplitud
    # en tiempo real, a diferencia del uso normal por teleop). Corremos continuo y
    # capturamos: (1) un instante caminando erguido, (2) el instante de la caida.
    sim._set_drive_targets(advance=0.5)
    log_every = int(0.2 / model.opt.timestep)
    walking_shot_taken = False
    fall_shot_taken = False
    max_seconds = 8.0
    for i in range(int(max_seconds / model.opt.timestep)):
        stage1_step(sim, model, data)
        height = sim._pelvis_height()
        if i % log_every == 0:
            print(f"  t={data.time:.2f}s altura={height:.3f}")

        if not walking_shot_taken and data.time >= 1.0:
            render_tracking(model, data, sim._pelvis_id, OUT_DIR / "01_heuristico_caminando.png")
            print(f"  -> shot 'caminando' en t={data.time:.2f}s altura={height:.3f}")
            walking_shot_taken = True

        if not fall_shot_taken and height < 0.5:
            render_tracking(model, data, sim._pelvis_id, OUT_DIR / "01_heuristico_caida.png")
            print(f"  -> shot 'caida' en t={data.time:.2f}s altura={height:.3f}")
            fall_shot_taken = True
            break

    if not fall_shot_taken:
        print(f"NO se detecto caida en {max_seconds}s. altura final={sim._pelvis_height():.3f}")
        render_tracking(model, data, sim._pelvis_id, OUT_DIR / "01_heuristico_caida.png")


def capture_stage2() -> None:
    print("== Etapa 2: RL ==")
    walker = G1RLWalker(control_host="127.0.0.1", control_port=None)
    walker.reset()
    walker.cmd[:] = (0.6, 0.0, 0.0)
    for i in range(int(1.0 / walker.cfg.simulation_dt)):
        walker._step_physics()
    render_tracking(
        walker.model, walker.data, walker._pelvis_id,
        OUT_DIR / "02_rl_caminando_inicio.png",
    )
    for i in range(int(6.0 / walker.cfg.simulation_dt)):
        walker._step_physics()
    x = walker.data.qpos[0]
    height = walker.data.xpos[walker._pelvis_id][2]
    print(f"t={walker.data.time:.2f}s x={x:.2f}m altura pelvis={height:.3f}")
    render_tracking(
        walker.model, walker.data, walker._pelvis_id,
        OUT_DIR / "02_rl_caminando_avanzado.png",
    )


def capture_stage3() -> None:
    print("== Etapa 3: RL + objetos ==")
    scene_path = (
        ASSET_ROOT
        / "resources"
        / "robots"
        / "g1_description"
        / "g1_warehouse_scene.xml"
    )
    walker = G1RLWalker(control_host="127.0.0.1", control_port=None, xml_path=scene_path)
    walker.reset()
    walker.cmd[:] = (0.6, 0.0, 0.0)

    static_cam = dict(lookat=[1.6, 0.0, 0.5], distance=5.0, elevation=-16, azimuth=-140)

    for i in range(int(1.5 / walker.cfg.simulation_dt)):
        walker._step_physics()
    print(f"t={walker.data.time:.2f}s x={walker.data.qpos[0]:.2f}m (acercandose)")
    render_static(walker.model, walker.data, OUT_DIR / "03_rl_objetos_acercandose.png", **static_cam)

    for i in range(int(4.5 / walker.cfg.simulation_dt)):
        walker._step_physics()
    height = walker.data.xpos[walker._pelvis_id][2]
    print(f"t={walker.data.time:.2f}s x={walker.data.qpos[0]:.2f}m altura pelvis={height:.3f} (despues del contacto)")
    render_static(walker.model, walker.data, OUT_DIR / "03_rl_objetos_despues.png", **static_cam)


if __name__ == "__main__":
    capture_stage1()
    capture_stage2()
    capture_stage3()
