# Workshop: de control manual a caminar con Reinforcement Learning

Esta guía es un recorrido práctico, paso a paso, para que cualquiera pueda repetir la
misma experiencia que fuimos teniendo mientras construíamos este proyecto: primero
intentar controlar el robot "a mano", ver que se cae fácil, después probar una política
de Reinforcement Learning (RL) ya entrenada y ver que se mantiene de pie mucho mejor, y
finalmente agregarle objetos al escenario para comprobar que sigue sin caerse aunque
choque con algo.

Requisito previo: seguir [INSTALL.md](INSTALL.md) para tener el entorno (`.venv`) y
`third_party/mujoco_menagerie` instalados.

## Etapa 1 — Control heurístico (a mano), motor por motor

**Objetivo de esta etapa:** entender que controlar un humanoide "motor por motor" con
fórmulas escritas a mano es posible, pero muy frágil.

1. Levantar el visor:

   ```bash
   ./run_viewer.sh
   ```

2. En otra terminal, mandarle un comando de avance por control remoto (UDP):

   ```bash
   .venv/bin/python send_unitree_command.py --advance 0.5
   ```

3. Observar: el robot camina unos pasos usando fórmulas fijas de cadera/rodilla/tobillo
   (ver [WALKING.md](WALKING.md)) más una fuerza de corrección aplicada a mano sobre la
   pelvis. Con comandos suaves se sostiene un rato, pero:

   - Si subís `--advance` a `1.0` y lo dejás correr, eventualmente se cae y el propio
     script lo detecta e imprime `caida detectada, reiniciando en stand`.
   - Si querés ver el intento de "marcha en el sitio" (levantar las piernas sin avanzar):

     ```bash
     .venv/bin/python send_unitree_command.py --march 1.0
     ```

   - También podés controlarlo con teclado en vez de comandos sueltos:

     ```bash
     .venv/bin/python teleop_unitree.py --host 127.0.0.1 --port 47001
     ```

4. Opcional — ver el problema "por dentro": activá el panel nativo de control y el modo
   motor crudo para mover cada actuador vos mismo con sliders, y confirmar que cada
   articulación individual funciona bien, pero que sostener el equilibrio de las 12+
   articulaciones juntas a mano es el verdadero problema:

   ```bash
   .venv/bin/python send_unitree_command.py --raw-mode
   ```

**Conclusión de la etapa 1:** cada motor responde bien por separado, pero coordinarlos
todos a mano para no caerse es muy difícil y frágil ante cualquier variación.

## Etapa 2 — La misma tarea, con una política de Reinforcement Learning

**Objetivo de esta etapa:** correr una política ya entrenada con RL (no escrita a mano)
para la misma tarea (pararse y caminar) y comparar la estabilidad.

Para entender qué es y cómo funciona esta política antes de correrla, leé
[REINFORCEMENT_LEARNING.md](REINFORCEMENT_LEARNING.md).

1. Levantar el visor con la política RL (mata automáticamente cualquier visor anterior):

   ```bash
   ./run_viewer_rl.sh
   ```

2. Controlarlo con teclado directo en la ventana del visor:

   - `W` / `S`: avanzar / retroceder
   - `A` / `D`: girar
   - Espacio: centrar (sigue de pie solo, no se cae por estar quieto)
   - `R`: reiniciar
   - `P` / `O`: pausar / reanudar

   O por UDP desde otra terminal, igual que en la etapa 1:

   ```bash
   .venv/bin/python send_unitree_command.py --advance 0.6
   ```

3. Comparar contra la etapa 1: probá `--advance 1.0` y dejalo caminar un rato largo.

**Resultado verificado:** con `advance=0.5` caminó **~3.65 metros sin caerse**, con la
pelvis estable en ~0.77 m todo el tiempo. La diferencia con la etapa 1 es la estabilidad
ante comandos sostenidos y variaciones — acá el equilibrio no lo escribimos nosotros,
lo aprendió la red neuronal (ver el "por qué" en
[REINFORCEMENT_LEARNING.md](REINFORCEMENT_LEARNING.md)).

## Etapa 3 — Agregar objetos al escenario: ¿sigue de pie si choca?

**Objetivo de esta etapa:** poner obstáculos reales en el camino (dos cajas sueltas y un
estante) y comprobar que el robot puede chocar contra ellos sin caerse.

1. Levantar el visor RL apuntando al escenario con objetos:

   ```bash
   .venv/bin/mjpython simulate_g1_rl.py --scene third_party/unitree_rl_gym/resources/robots/g1_description/g1_warehouse_scene.xml
   ```

2. Mandarlo a caminar derecho hacia las cajas:

   ```bash
   .venv/bin/python send_unitree_command.py --advance 0.6
   ```

3. Observar: el robot camina hacia las cajas rojas/azules y el estante. Si las toca, las
   empuja (son cuerpos físicos reales, con colisión), pero **la política sigue sosteniendo
   el equilibrio** — no es un choque scripteado, es una interacción física real resuelta
   por MuJoCo.

**Resultado verificado:** en una corrida de prueba, el robot avanzó de x=0 a x≈2.7 m en
6 segundos, empujando una de las cajas en el camino, sin perder la altura de la pelvis
(~0.77 m) en ningún momento.

## Resumen del recorrido

| Etapa | Qué probamos | Qué vimos |
|---|---|---|
| 1. Heurístico | Fórmulas a mano por motor + control remoto | Cada motor funciona, pero el conjunto se cae fácil |
| 2. RL | Política ya entrenada, misma tarea | Camina largas distancias sin caerse |
| 3. RL + objetos | Escenario con cajas y estante | Choca, empuja objetos, y sigue de pie |

## Para seguir profundizando

- [WALKING.md](WALKING.md): detalle del controlador heurístico de la etapa 1.
- [REINFORCEMENT_LEARNING.md](REINFORCEMENT_LEARNING.md): cómo funciona la política de la etapa 2 por dentro.
- [RUNBOOK.md](RUNBOOK.md): operación diaria del simulador en general.
