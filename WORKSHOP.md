# Workshop: de control manual a caminar con Reinforcement Learning

Recorrido práctico, paso a paso, para repetir la misma experiencia que fuimos teniendo
mientras construíamos este proyecto: primero intentar controlar el robot "a mano" y ver
que se cae fácil, después probar una política de Reinforcement Learning (RL) ya entrenada
y ver que se mantiene de pie mucho mejor, y finalmente agregarle objetos al escenario para
comprobar que sigue sin caerse aunque choque con algo.

Requisito previo: seguir [INSTALL.md](INSTALL.md) para tener el entorno (`.venv`) y
`third_party/mujoco_menagerie` instalados.

Cada etapa tiene su propia página, con cómo ejecutarla, en qué consiste, qué mirar, cómo
se resuelve el problema de esa etapa, y qué problemas reales encontramos armándola:

1. **[Control heurístico](workshop/01-control-heuristico.md)** — fórmulas a mano por
   motor + control remoto. Se cae fácil.
2. **[Reinforcement Learning](workshop/02-reinforcement-learning.md)** — misma tarea, con
   una política ya entrenada. Camina largas distancias sin caerse.
3. **[Objetos en el escenario](workshop/03-objetos-en-el-escenario.md)** — cajas y estante
   en el camino. Choca, empuja objetos, y sigue de pie.

## Resumen rápido: qué ejecutar en cada etapa

Si solo querés los comandos para probar ya mismo, son estos (el detalle de cada uno está
en la página de su etapa).

**Etapa 1 — heurístico:**
```bash
./run_viewer.sh
```
```bash
.venv/bin/python send_unitree_command.py --advance 0.5
```

**Etapa 2 — RL:**
```bash
./run_viewer_rl.sh
```
```bash
.venv/bin/python send_unitree_command.py --advance 0.6
```
(o directamente `W/A/S/D` en la ventana del visor, sin necesitar la segunda terminal)

**Etapa 3 — RL + objetos:**
```bash
.venv/bin/mjpython simulate_g1_rl.py --scene third_party/unitree_rl_gym/resources/robots/g1_description/g1_warehouse_scene.xml
```
```bash
.venv/bin/python send_unitree_command.py --advance 0.6
```

## Para seguir profundizando

- [WALKING.md](WALKING.md): detalle técnico del controlador heurístico de la etapa 1.
- [REINFORCEMENT_LEARNING.md](REINFORCEMENT_LEARNING.md): cómo funciona por dentro la política de la etapa 2 (qué es RL, cuántos motores, cuántos valores de observación, qué significan los paneles del visor).
- [RUNBOOK.md](RUNBOOK.md): operación diaria del simulador en general.
