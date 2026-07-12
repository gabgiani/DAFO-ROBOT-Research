# Etapa 1 — Control heurístico (a mano), motor por motor

## Cómo se ejecuta

Levantar el visor (mata cualquier instancia previa automáticamente):

```bash
./run_viewer.sh
```

En otra terminal, mandar comandos por control remoto (UDP):

```bash
.venv/bin/python send_unitree_command.py --advance 0.5
```

Otras variantes útiles:

```bash
# marcha en el sitio (levantar piernas sin avanzar)
.venv/bin/python send_unitree_command.py --march 1.0

# control por teclado en vez de comandos sueltos
.venv/bin/python teleop_unitree.py --host 127.0.0.1 --port 47001

# mover cada motor a mano desde el panel nativo del visor
.venv/bin/python send_unitree_command.py --raw-mode
```

## En qué consiste

El controlador ([interactive_unitree.py](../interactive_unitree.py)) traduce un comando de
alto nivel (`avance`, `giro`, `marcha en el sitio`) en ángulos objetivo para 12+ motores de
posición (cadera, rodilla, tobillo, cintura, hombros), usando fórmulas escritas a mano:
amplitud de zancada, frecuencia, transferencia de peso lateral, y una fuerza de corrección
aplicada directamente sobre el cuerpo de la pelvis (`data.xfrc_applied`) para intentar
mantenerlo erguido. El detalle matemático completo está en [WALKING.md](../WALKING.md).

Es el enfoque "clásico": nadie entrenó nada, un humano ajustó los números por prueba y
error hasta que el robot caminara unos pasos sin caerse.

## Qué estamos mirando

- La ventana del visor de MuJoCo, con el robot G1 parado sobre el piso a cuadros.
- Los mensajes que imprime el script en la terminal (`[viewer] avance=... giro=...`,
  `[viewer] caida detectada, reiniciando en stand`).
- Opcionalmente, el panel nativo "Control" con un slider por motor (ver más abajo).

## Cómo lo miramos

- **Visualmente**: la cámara sigue automáticamente a la pelvis (`mujoco.mjtCamera.mjCAMERA_TRACKING`),
  así el robot no se sale de cuadro mientras camina o se cae.
- **Por consola**: cada cambio de comando o caída se imprime como texto (`[viewer] ...`),
  así se puede confirmar sin mirar la ventana si el robot se mantuvo de pie durante una
  prueba larga.
- **Motor por motor**: activando `--raw-mode`, el bucle de control deja de escribir sobre
  los actuadores y el panel "Control" del visor pasa a mandar directamente sobre cada
  motor de posición. Sirve para verificar, moviendo un slider a la vez, hacia qué lado
  gira cada articulación — en vez de adivinarlo mirando una captura de pantalla.

## Cómo lo resolvemos

- Cada articulación se controla con un actuador de **posición** (no de torque): el valor
  que se manda es el ángulo objetivo, y MuJoCo aplica automáticamente la fuerza necesaria
  para acercarse a ese ángulo.
- Caminar se arma combinando, en fase, cadera + rodilla + tobillo de la pierna que
  "vuela" y de la que "apoya", más una transferencia de peso lateral para que el pie que
  se levanta no resbale.
- Para no caerse, se suma una asistencia de balance: un torque correctivo (roll/pitch)
  aplicado directo sobre la pelvis a partir de la orientación e giroscopio (IMU), y una
  fuerza vertical proporcional al error de altura. Es, literalmente, una mano invisible
  ayudando al robot — no es cómo se sostiene en pie un robot real.

## Qué problemas encontramos

- **El robot se cae con comandos sostenidos.** Con `advance=1.0` durante mucho tiempo,
  eventualmente cae y el propio script lo detecta y reinicia (`caida detectada,
  reiniciando en stand`). El control a mano nunca llegó a ser confiable en el largo plazo.
- **Confusión de signos en la marcha.** Al subir la amplitud de flexión de cadera para que
  el muslo subiera más, visualmente el muslo se iba **hacia atrás** (como una patada), no
  hacia adelante. Cambiar el signo arregló la dirección pero hizo que el robot se cayera
  repetidamente con esa magnitud — hubo que bajar la amplitud a un valor intermedio y
  volver a probar.
- **Notas contradictorias entre sesiones.** Una sesión anterior había concluido que
  "positivo ya es hacia adelante" y que el problema era otro (la rodilla dominando sobre
  la cadera). Confiar en una nota vieja sin volver a verificar casi generó un error
  repetido — la lección: siempre reverificar el signo real con `--raw-mode` en vez de
  asumir.
- **Visores duplicados.** Cada prueba abría una ventana nueva sin cerrar la anterior,
  generando confusión sobre cuál mirar. Se resolvió haciendo que `run_viewer.sh` mate
  cualquier instancia previa (`pkill -f simulate_unitree.py`) antes de abrir una nueva.
- **La cámara se quedaba fija** mientras el robot caminaba y se salía del cuadro. Se
  resolvió activando la cámara de "tracking" nativa de MuJoCo, que sigue automáticamente
  a la pelvis.

## Siguiente etapa

Con este enfoque, mantener el equilibrio depende 100% de fórmulas y fuerzas artificiales
ajustadas a mano. La [Etapa 2](02-reinforcement-learning.md) prueba la misma tarea con una
política entrenada, sin trucos externos.
