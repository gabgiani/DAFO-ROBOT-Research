# Stage 2 — The same task, with a Reinforcement Learning policy

*[Versión en español](02-reinforcement-learning.es.md)*

## Objective of this stage

Repeat exactly the same task from stage 1 — advance without falling — but replacing
the hand-written formulas with an already-trained Reinforcement Learning policy, and
comparing objectively (same commands, same metrics: pelvis height and distance
traveled) how much more stable one is than the other.

By the end of this stage you'll be able to reproduce the same sustained-advance test as
in stage 1, but seeing that here the robot doesn't fall — and you'll have the concrete
numbers (meters traveled, pelvis height) to verify it yourself.

## How to run it

Start the viewer with the already-trained RL policy (kills any previous viewer,
heuristic or RL):

```bash
./run_viewer_rl.sh
```

Control it with direct keyboard input in the viewer window — `W/S` advance/retreat,
`A/D` turn, space centers, `R` resets, `P/O` pause/resume — or via UDP from another
terminal, same as in stage 1:

```bash
.venv/bin/python send_unitree_command.py --advance 0.6
```

## What it consists of

Instead of writing walking formulas by hand, here we run a neural network already
trained by Unitree with Reinforcement Learning
([unitree_rl_gym](https://github.com/unitreerobotics/unitree_rl_gym)), which decides
what target position to give each of the 12 leg motors, 500 times per second, based on
how the robot is standing at that instant. The full detail — what RL is, how the
observation is built, how torque is computed — is in
[REINFORCEMENT_LEARNING.md](../REINFORCEMENT_LEARNING.md); this page is the practical
experience of running it and comparing it with stage 1.

Technically this lives in [simulate_g1_rl.py](../simulate_g1_rl.py), which
reimplements unitree_rl_gym's official `deploy_mujoco.py` script without depending on
`legged_gym`/`isaacgym` (which don't run on macOS), reusing our own
[external_control.py](../external_control.py) so that `advance/lateral/turn` work the
same way as in stage 1.

## What we're looking at

- The same viewer window, but with a 12-motor model (legs only, no articulated
  arms/hands).
- The native "Joint" panel (measured angle of each motor) and "Control" (torque
  currently being applied) — see the section below, because here they mean something
  different than in stage 1.
- The status messages in the terminal (`[rl] avance=... giro=...`, `[rl] control
  externo UDP en ...`).

## How we look at it

- **Direct comparison with stage 1**: same commands (`--advance`; `--march` doesn't
  apply here because there's no explicit "march in place" mode, but sustained
  `--advance` can be left running much longer without falling).
- **Headless test** (no window, for a cold measurement): a disposable script was
  instrumented that runs physics for 8 seconds with `cmd=(0.5, 0, 0)` and logs pelvis
  height every 0.4s. Real measured result:

  ```
  pelvis heights: [0.793, 0.77, 0.771, 0.77, 0.773, 0.767, 0.772, 0.768, ...]
  final position: x=3.65m
  ```

  The robot advanced **3.65 meters without falling**, with the pelvis always between
  0.76 and 0.79m.
- **"Stay still" test**: with `cmd=(0,0,0)` for 8 seconds, the pelvis stayed stable
  (~0.78m) with only ~0.17m of drift — confirming that centering the joystick is not
  the same as pausing: the policy keeps holding balance on its own.

## How we solve it

- The 12 motors in this model are **torque** motors (`<motor>`), not position ones. The
  policy provides a target position, and a classic PD controller (simple math, not
  learned) computes the actual torque: `torque = (target - current) * kp + (target_vel
  - current_vel) * kd`.
- The observation the network receives (47 numbers: angular velocity, orientation
  relative to gravity, command, position/velocity of the 12 legs, previous action, step
  phase) summarizes "how the robot is standing right now", and the network directly
  returns what to do — balance isn't in a formula we wrote, it's encoded in the
  network's weights, learned by trial and error in simulation during training (which we
  don't do here, we only use the already-trained result).
- **Important**: in this viewer, dragging a "Control" panel slider by hand **does
  nothing persistent** — our own code recalculates and overwrites each motor's torque
  on every physics step (every 2ms). Real control is always through `cmd`.

## Real screenshots

Same headless test, with `cmd=(0.6, 0, 0)` sustained with no human correction:

| Start (t=1.00s) | After walking (t=7.00s, x=3.77m, pelvis height 0.769m) |
|---|---|
| ![Robot with RL policy at the start of the walk](../artifacts/workshop/02_rl_caminando_inicio.png) | ![Robot with RL policy after advancing several meters](../artifacts/workshop/02_rl_caminando_avanzado.png) |

Unlike stage 1, here 6 additional seconds of sustained advance cause no fall at all:
pelvis height stays practically the same (0.769m) while the robot advanced 3.77 meters
in a straight line.

## Problems we ran into

- **Heavy dependencies that weren't needed.** Unitree's official script
  (`deploy_mujoco.py`) imports the `legged_gym` package, which in turn depends on
  `isaacgym` — which doesn't work on macOS. Solved by reimplementing the same loop
  (PD + observation + policy) without that dependency, using `torch.jit.load` directly
  on the already-trained policy file (`motion.pt`, TorchScript format, doesn't need the
  training code to run).
- **The robot left the frame while walking.** The viewer's camera didn't follow the
  robot by default. Solved with MuJoCo's native "tracking" camera (same as in stage 1).
- **Confusion between the "Joint" and "Control" panels.** At first glance they look
  like editable sliders as in stage 1, but here "Control" shows **torque**, not a
  target angle — moving one by hand has no lasting effect. Documented in detail in
  [REINFORCEMENT_LEARNING.md](../REINFORCEMENT_LEARNING.md#what-the-joint-and-control-viewer-panels-mean).
- **Publishing the assets to GitHub almost broke the repo.** When cloning
  `unitree_rl_gym` with a normal `git clone`, a nested `.git` ended up inside
  `third_party/unitree_rl_gym`; when committing, git registered it as a broken
  submodule (with no `.gitmodules`) — anyone cloning the repo would have found an empty
  folder. Solved by deleting the nested `.git` and re-adding the real files before
  publishing.

## Next stage

The policy only walks on an empty floor so far. [Stage 3](03-objetos-en-el-escenario.md)
adds real obstacles (boxes and a shelf) to see whether balance holds up when it also
hits something.
