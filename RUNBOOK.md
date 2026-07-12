# Runbook

*[Versión en español](RUNBOOK.es.md)*

This guide explains how to run the simulator and how to operate it in the normal workflow.

## Entry point

The main launcher is [simulate_unitree.py](simulate_unitree.py).

Main functions:

- Loads Unitree scenes.
- Applies the initial keyframe.
- Runs in `headless` or `viewer` mode.
- Exposes external UDP control if `--control-port` is not `0`.

## Quick start

### Headless

```bash
cd /path/to/repo/dafo-human
.venv/bin/python simulate_unitree.py --robot g1-hands --mode headless --steps 300
```

### Viewer with UDP control

```bash
cd /path/to/repo/dafo-human
.venv/bin/mjpython simulate_unitree.py --robot g1-hands --mode viewer
```

By default it listens on `127.0.0.1:47001`.

### Viewer without UDP control

```bash
cd /path/to/repo/dafo-human
.venv/bin/mjpython simulate_unitree.py --robot g1-hands --mode viewer --control-port 0
```

## Supported robots

- `h1`
- `g1`
- `g1-hands`

Example:

```bash
cd /path/to/repo/dafo-human
.venv/bin/python simulate_unitree.py --robot h1 --mode headless --steps 300
```

## Keyframes

By default the launcher uses the `home` keyframe.

Change keyframe:

```bash
cd /path/to/repo/dafo-human
.venv/bin/mjpython simulate_unitree.py --robot g1-hands --mode viewer --keyframe home
```

Disable keyframe:

```bash
cd /path/to/repo/dafo-human
.venv/bin/python simulate_unitree.py --robot g1-hands --mode headless --keyframe ''
```

## Teleoperation

The expected flow is:

1. Open the viewer.
2. In another terminal, launch teleop.

```bash
cd /path/to/repo/dafo-human
.venv/bin/python teleop_unitree.py --host 127.0.0.1 --port 47001
```

Equivalent wrapper:

```bash
cd /path/to/repo/dafo-human
.venv/bin/python teleop_unitree.pyw --host 127.0.0.1 --port 47001
```

Controls:

- `W/S`: forward and backward
- `A/D`: turn
- `Space`: center forward and turn
- `R`: reset
- `P`: pause
- `O`: resume
- `J/K`: decrease/increase amplitude
- `N/M`: decrease/increase frequency
- `Q`: quit

## One-shot command sending

For quick tests, use [send_unitree_command.py](send_unitree_command.py).

Examples:

```bash
cd /path/to/repo/dafo-human
.venv/bin/python send_unitree_command.py --host 127.0.0.1 --port 47001 --advance 0.8
```

```bash
cd /path/to/repo/dafo-human
.venv/bin/python send_unitree_command.py --host 127.0.0.1 --port 47001 --turn 0.4
```

```bash
cd /path/to/repo/dafo-human
.venv/bin/python send_unitree_command.py --host 127.0.0.1 --port 47001 --center
```

```bash
cd /path/to/repo/dafo-human
.venv/bin/python send_unitree_command.py --host 127.0.0.1 --port 47001 --reset
```

## Grasp demo

The available demo is [reach_grasp_demo.py](reach_grasp_demo.py).

Without video:

```bash
cd /path/to/repo/dafo-human
.venv/bin/python reach_grasp_demo.py --no-video
```

With video:

```bash
cd /path/to/repo/dafo-human
.venv/bin/python reach_grasp_demo.py
```

Default output:

- `artifacts/g1_reach_grasp.mp4`

## Daily operation

Recommended sequence:

1. Validate the model in `headless` if you changed physics or the controller.
2. Open the `viewer` with `mjpython`.
3. Connect `teleop_unitree.py` from another terminal.
4. Test first with `advance=0.2` or `0.4` and increase gradually.
5. If the robot falls, use `R` or resend `--reset`.

## Common failures

### Port in use

```bash
lsof -nP -iUDP:47001
```

### Viewer opens fine, but the robot doesn't move

Check:

- That the viewer is listening on `47001`.
- That teleop points to the same host and port.
- That there's no previous instance still consuming the port.

### The viewer resets due to a fall

That's currently part of the recovery logic in the controller in [interactive_unitree.py](interactive_unitree.py).

## Main operational files

- [simulate_unitree.py](simulate_unitree.py)
- [interactive_unitree.py](interactive_unitree.py)
- [external_control.py](external_control.py)
- [teleop_unitree.py](teleop_unitree.py)
- [send_unitree_command.py](send_unitree_command.py)
