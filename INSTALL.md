# Installation

*[Versión en español](INSTALL.es.md)*

This guide covers local installation of the simulator and its dependencies.

## Requirements

- macOS or Linux.
- Python 3.
- A virtual environment in `.venv`.
- The `third_party/mujoco_menagerie` folder with the Unitree models.
- Optional: `ffmpeg` to export video from the grasp demo.

## Python dependencies

Create the environment and install dependencies:

```bash
cd /path/to/repo/dafo-human
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Dependencies installed from [requirements.txt](requirements.txt):

- `mujoco==3.2.7`
- `glfw==2.10.0`
- `numpy==2.5.1`
- `PyOpenGL==3.1.10`

## MuJoCo models

The launcher expects to find Unitree scenes in `third_party/mujoco_menagerie`.

Expected paths:

- `third_party/mujoco_menagerie/unitree_h1/scene.xml`
- `third_party/mujoco_menagerie/unitree_g1/scene.xml`
- `third_party/mujoco_menagerie/unitree_g1/scene_with_hands.xml`

If that folder doesn't exist, the simulator fails to resolve the model.

## Quick validation

Check that MuJoCo loads the model without opening the viewer:

```bash
cd /path/to/repo/dafo-human
.venv/bin/python simulate_unitree.py --robot g1-hands --mode headless --steps 300
```

If that works, the base installation is ready.

## Interactive viewer

To open the viewer use `mjpython`, not `python`:

```bash
cd /path/to/repo/dafo-human
.venv/bin/mjpython simulate_unitree.py --robot g1-hands --mode viewer
```

That avoids failures observed when opening the MuJoCo viewer with the standard interpreter.

## Common installation issues

### The scene doesn't exist

Symptom:

```text
No encontre el modelo en ...
```

Cause:

- Missing `third_party/mujoco_menagerie`.
- Or the custom scene passed with `--xml` doesn't exist.

### The viewer doesn't open properly

Use:

```bash
.venv/bin/mjpython simulate_unitree.py --robot g1-hands --mode viewer
```

Don't use:

```bash
.venv/bin/python simulate_unitree.py --robot g1-hands --mode viewer
```

### UDP port in use

The viewer listens by default on `127.0.0.1:47001`.

See which process is using it:

```bash
lsof -nP -iUDP:47001
```

## Next step

After installing, follow [RUNBOOK.md](RUNBOOK.md) to operate the simulator and [WALKING.md](WALKING.md) for the current state of walking.
