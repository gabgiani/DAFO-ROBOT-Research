# Etapa 3 — Agregar objetos al escenario: ¿sigue de pie si choca?

## Cómo se ejecuta

Levantar el visor RL apuntando al escenario con objetos (dos cajas y un estante):

```bash
.venv/bin/mjpython simulate_g1_rl.py --scene third_party/unitree_rl_gym/resources/robots/g1_description/g1_warehouse_scene.xml
```

Mandarlo a caminar derecho hacia las cajas:

```bash
.venv/bin/python send_unitree_command.py --advance 0.6
```

## En qué consiste

Hasta la etapa 2, el robot caminaba en un piso vacío. Acá le agregamos un escenario con
objetos físicos reales — dos cajas sueltas (no ancladas, con `<freejoint/>`, se pueden
empujar) y un estante fijo de dos niveles — para comprobar si la política de RL sigue
sosteniendo el equilibrio cuando además tiene que lidiar con colisiones no anticipadas en
el entrenamiento original.

El escenario es un archivo MJCF nuevo,
[g1_warehouse_scene.xml](../third_party/unitree_rl_gym/resources/robots/g1_description/g1_warehouse_scene.xml),
que se le pasa a `simulate_g1_rl.py` con `--scene`.

## Qué estamos mirando

- El robot caminando hacia dos cajas (roja y azul) y un estante ubicados adelante de su
  punto de partida.
- Si al tocarlas las empuja (colisión física real, no un choque "de mentira"), y si
  después de empujarlas sigue de pie o se cae.
- La altura de la pelvis a lo largo del recorrido, igual que en la etapa 2.

## Cómo lo miramos

Se instrumentó una prueba headless (sin ventana) que:

1. Carga el modelo con el escenario de objetos.
2. Manda `cmd=(0.5, 0, 0)` (avanzar).
3. Corre 6 segundos de física, registrando la altura de la pelvis cada 0.4s y la posición
   final de cada caja.

Resultado real medido:

```
nq total (robot+cajas): 33   nv total: 30
alturas pelvis: [0.793, 0.77, 0.771, 0.77, 0.773, 0.767, 0.772, 0.768, ...]
posición xy final robot: [2.70, -0.16]
caja A pos: [2.20, 0.35, 0.10]      -> casi no se movió
caja B pos: [2.92, -0.41, 0.10]     -> se corrió desde [2.80, -0.35], el robot la empujó
```

El robot avanzó de x=0 a x≈2.7m en 6 segundos, empujó la caja B en el camino, y la pelvis
nunca bajó de ~0.77m — no hubo caída.

## Cómo lo resolvemos

- Las cajas se agregan como `<body>` con `<freejoint/>` (cuerpos libres, con física real de
  colisión y gravedad), no como decoración fija — por eso se pueden empujar.
- El estante es geometría estática (sin `freejoint`), pensado como obstáculo/destino fijo
  al que caminar, no para empujarlo.
- La política no sabe nada de estos objetos específicos (no fueron parte de su
  entrenamiento), pero su estrategia de balance es lo bastante general como para absorber
  el impacto de chocar contra algo sin perder el equilibrio, al menos con objetos livianos
  (0.5 kg) y velocidades moderadas.

## Capturas reales

Misma prueba headless con el escenario `g1_warehouse_scene.xml`, `cmd=(0.6, 0, 0)`:

| Acercándose (t=1.50s, x=0.66m) | Después de pasar las cajas (t=6.00s, x=3.21m, altura pelvis 0.768m) |
|---|---|
| ![Robot acercándose a las cajas y el estante](../artifacts/workshop/03_rl_objetos_acercandose.png) | ![Robot de pie después de pasar junto a las cajas](../artifacts/workshop/03_rl_objetos_despues.png) |

El robot llega hasta la caja azul, la desplaza al pasar junto a ella, y sigue de
pie con la pelvis en la misma altura de siempre (~0.77m) — ninguna caída pese al
contacto físico no anticipado por el entrenamiento original.

## Qué problemas encontramos

- **Las mallas (STL) no se encontraban al cargar la escena.** El `meshdir` relativo que
  usa MuJoCo (declarado en `g1_12dof.xml` como `meshdir="meshes/"`) no resuelve de forma
  confiable cuando el archivo de escena que hace `<include>` vive en una carpeta distinta
  a la del robot. Se probó:
  1. Poner la escena en `scenes/` con una ruta relativa `../third_party/...` — falló,
     buscaba el archivo sin el subdirectorio `meshes/`.
  2. Agregar un `<compiler meshdir="...">` explícito en el archivo de escena — también
     falló, con un mesh distinto cada vez.

  La solución que funcionó al 100%: poner el archivo de escena **en la misma carpeta**
  que `g1_12dof.xml` (exactamente el mismo patrón que usa el `scene.xml` oficial de
  Unitree), con `<include file="g1_12dof.xml"/>` sin ningún prefijo de ruta. Por eso
  `g1_warehouse_scene.xml` vive dentro de `third_party/unitree_rl_gym/...` en vez de
  `scenes/`.

- **El vector de observación se hubiera corrompido silenciosamente.** El código original
  leía `data.qpos[7:]` y `data.qvel[6:]` sin límite superior, asumiendo que el robot era
  el único cuerpo con grados de libertad. En cuanto se agregan las cajas (cada una suma 7
  valores de `qpos` y 6 de `qvel` por su `freejoint`), ese slice hubiera incluido también
  la posición de las cajas, dándole a la política un vector de tamaño y contenido
  incorrecto. Se corrigió acotando explícitamente el slice a los 12 valores de las piernas
  (`slice(7, 7+12)` y `slice(6, 6+12)`), calculado una sola vez y reusado en todo el
  script.

## Resumen de las 3 etapas

| Etapa | Qué probamos | Qué vimos |
|---|---|---|
| [1. Heurístico](01-control-heuristico.md) | Fórmulas a mano por motor + control remoto | Cada motor funciona, pero el conjunto se cae fácil |
| [2. RL](02-reinforcement-learning.md) | Política ya entrenada, misma tarea | Camina largas distancias sin caerse |
| [3. RL + objetos](03-objetos-en-el-escenario.md) | Escenario con cajas y estante | Choca, empuja objetos, y sigue de pie |
