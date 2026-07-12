# Walking Guide

*[Versión en español](WALKING.es.md)*

This guide summarizes the current state of the walking controller and how best to test it.

## What controls the gait today

The controller is implemented in [interactive_unitree.py](interactive_unitree.py).

Main gait variables:

- `advance`: forward intent in `[-1, 1]`
- `turn`: turning intent in `[-1, 1]`
- `amplitude_scale`: stride amplitude
- `frequency_hz`: cycle frequency

The current gait combines:

- Hip, knee, and ankle movement.
- Lateral sway for support.
- Physical assistance applied to the pelvis with `xfrc_applied`.

It does not use direct `qpos` translation to move the base.

## Current state

Goal of this iteration:

- Remove skating caused by artificially dragging the base.
- Make forward motion come from the leg pattern plus consistent physical assistance.

State validated headless:

- `advance=0.8` gives net forward motion and stays standing.
- `advance=1.0` gives net forward motion and stays standing in the short test.

State observed in the viewer:

- Holding `+1.0` for a long time can still end in a fall and reset.
- Behavior in the viewer is still less stable than headless.

## How to test the gait

First open the viewer:

```bash
cd /path/to/repo/dafo-human
.venv/bin/mjpython simulate_unitree.py --robot g1-hands --mode viewer
```

Then open teleop:

```bash
cd /path/to/repo/dafo-human
.venv/bin/python teleop_unitree.py --host 127.0.0.1 --port 47001
```

## Recommended test range

To avoid saturating the controller from the first second:

1. Start at `advance=0.2`.
2. Increase to `0.4`.
3. Try `0.6` and `0.8`.
4. Use `1.0` only for short tests.

Current practical recommendation:

- For controlled forward motion: `0.4` to `0.8`.
- For stress testing: `1.0`.

## What the gait controls mean

- `W/S`: changes `advance`.
- `A/D`: changes `turn`.
- `J/K`: changes `amplitude_scale`.
- `N/M`: changes `frequency_hz`.

In practice:

- More amplitude: bigger stride, but more risk of losing stability.
- More frequency: faster steps, but more prone to falls.

## Quick validation without the viewer

If you change the controller, the minimum recommended validation is:

```bash
cd /path/to/repo/dafo-human
.venv/bin/python simulate_unitree.py --robot g1-hands --mode headless --steps 300
```

And then a focused test similar to the ones used during this session:

- measure `pelvis_delta`
- measure `pelvis_min_height`
- verify skating doesn't reappear

## Current limitations

- Walking is still not robust full-body locomotion.
- The viewer and headless don't behave exactly the same under long commands.
- The current controller is meant for fast iteration, not a full dynamic policy.

## Next logical technical improvement

If work on the gait continues, the next steps should be:

1. separate support and swing control per foot
2. measure actual slip of the foot in contact
3. limit maximum advance when support drops to a single foot
4. better decouple advance and turn
