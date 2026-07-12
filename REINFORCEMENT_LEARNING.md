# Reinforcement Learning: cómo se mantiene parado el robot

Este documento explica, en términos simples, cómo funciona la política de Reinforcement
Learning (RL) que usamos en [simulate_g1_rl.py](simulate_g1_rl.py) para que el G1 se mantenga
de pie y camine, y en qué se diferencia del controlador manual de
[interactive_unitree.py](interactive_unitree.py).

## El problema que resuelve

Un robot humanoide de pie es físicamente **inestable**: es una torre alta y angosta parada
sobre dos pies chicos. Cualquier pequeño error de ángulo en una pierna, cualquier empuje,
lo puede tirar. Mantenerlo de pie (y caminando) requiere corregir constantemente el
equilibrio, muchas veces por segundo.

Hay dos formas de resolver esto:

1. **A mano** (lo que hace `interactive_unitree.py`): un humano diseña fórmulas fijas
   (amplitud de zancada, flexión de rodilla, fuerzas de corrección) y las ajusta por prueba
   y error. Funciona, pero es frágil: cualquier situación no anticipada por esas fórmulas
   (una caja en el piso, un piso irregular, un empujón) la puede romper.
2. **Con una política aprendida** (lo que hace `simulate_g1_rl.py`): en vez de que un humano
   escriba las fórmulas, una red neuronal **aprendió sola**, a base de millones de intentos
   en simulación, qué torque mandarle a cada motor para no caerse. Esa red es la "política".

## Qué es Reinforcement Learning, en corto

RL es una forma de entrenar un programa (la "política") por prueba y error, no mostrándole
ejemplos correctos (como en aprendizaje supervisado), sino dejándolo actuar y dándole un
premio o castigo según el resultado.

Los cuatro elementos básicos:

- **Agente**: la política (red neuronal) que decide qué hacer.
- **Entorno**: la simulación física del robot (MuJoCo / Isaac Gym durante el entrenamiento).
- **Acción**: lo que el agente decide en cada instante (en este caso, la posición objetivo
  de cada uno de los 12 motores de las piernas).
- **Recompensa**: un número que le dice al agente qué tan bien lo hizo (por ejemplo: +premio
  por seguir la velocidad pedida y mantenerse erguido, -castigo por caerse o gastar mucha
  energía).

El entrenamiento consiste en repetir este ciclo millones de veces, en miles de simulaciones
en paralelo, ajustando la red neuronal poco a poco para que las acciones que llevan a mayor
recompensa se vuelvan más probables.

```mermaid
flowchart LR
    Obs[Observacion: sensores del robot] --> Policy[Politica: red neuronal]
    Policy --> Action[Accion: 12 posiciones objetivo]
    Action --> Sim[Simulacion fisica]
    Sim --> Reward[Recompensa: de pie? avanzo? cayo?]
    Reward -->|ajusta pesos| Policy
    Sim --> Obs
```

Ese ciclo de entrenamiento **no ocurre en este repo**: la política ya viene entrenada por
Unitree (el archivo [motion.pt](third_party/unitree_rl_gym/deploy/pre_train/g1/motion.pt)).
Lo que hacemos en `simulate_g1_rl.py` es solo la mitad derecha del diagrama, en modo
"inferencia" (usar la política ya entrenada, no seguir entrenándola).

## Cómo se usa esa política ya entrenada (lo que corre en este repo)

En cada ciclo de control (50 Hz, cada 10 pasos de físca de 2ms), `simulate_g1_rl.py` hace:

1. **Lee el estado del robot** (la "observación", 47 números):
   - Velocidad angular de la pelvis (giroscopio).
   - Hacia dónde apunta la gravedad vista desde el robot (si está inclinado, hacia adelante,
     hacia atrás, etc.).
   - El comando actual (avance / lateral / giro que vos le mandás con W/A/S/D).
   - Posición y velocidad de cada uno de los 12 motores de las piernas.
   - La última acción que tomó (para que tenga "memoria" de qué estaba haciendo).
   - Una señal de fase (seno/coseno) que le indica en qué punto del ciclo de paso está.

2. **Le pasa esa observación a la red neuronal** (`policy(obs_tensor)` en el código), que
   devuelve 12 números: la posición objetivo para cada motor de las piernas.

3. **Un controlador PD clásico** (no aprendido, matemática simple) convierte esa posición
   objetivo en el torque real que hay que aplicarle a cada motor:

   ```
   torque = (posicion_objetivo - posicion_actual) * kp + (velocidad_objetivo - velocidad_actual) * kd
   ```

4. **MuJoCo avanza la física** con esos torques, y el ciclo vuelve a empezar leyendo el
   nuevo estado del robot.

```mermaid
sequenceDiagram
    participant Teclado as Teclado (W/A/S/D)
    participant Script as simulate_g1_rl.py
    participant Red as Politica (motion.pt)
    participant PD as Control PD
    participant Fisica as MuJoCo

    Teclado->>Script: cmd = avance/lateral/giro
    loop cada 50 Hz
        Script->>Script: arma observacion (47 numeros)
        Script->>Red: observacion
        Red-->>Script: accion (12 posiciones objetivo)
        Script->>PD: posicion objetivo vs posicion actual
        PD-->>Fisica: torque por motor
        Fisica-->>Script: nueva posicion/velocidad/orientacion
    end
```

## Por qué esto mantiene mejor el equilibrio que las fórmulas a mano

- Las fórmulas a mano (`interactive_unitree.py`) fueron ajustadas para **una situación
  esperada** (piso plano, sin objetos, marcha hacia adelante). Cuando la realidad se desvía
  un poco de eso, se cae, porque las fórmulas no "saben" reaccionar a algo que no
  anticipamos.
- La política de RL fue entrenada con **miles de variaciones** (empujones aleatorios, pisos
  irregulares, distintas velocidades pedidas, fallas de sensor simuladas) en paralelo durante
  el entrenamiento. Aprendió una estrategia de balance mucho más general, no una fórmula fija
  para un solo caso.
- Prueba real en este repo: con `advance=0.5` caminó **~3.65 metros sin caerse**, incluso con
  cajas en el piso ([g1_warehouse_scene.xml](third_party/unitree_rl_gym/resources/robots/g1_description/g1_warehouse_scene.xml)),
  algo que el controlador a mano nunca logró de forma confiable.

## Limitaciones importantes

- Esta política **solo controla las 12 piernas**. No tiene brazos/manos entrenados, así que
  no puede agarrar ni manipular objetos, solo caminar hacia ellos.
- Fue entrenada en un entorno específico (probablemente piso plano en simulación). Terrenos
  muy distintos a eso (escaleras, pendientes fuertes) pueden no funcionar bien.
- Es una "caja negra": no hay fórmulas legibles que uno pueda ajustar a mano como en
  `interactive_unitree.py`. Si el comportamiento no gusta, la única forma de cambiarlo es
  reentrenar la red (algo que no hacemos en este repo, solo la corremos ya entrenada).

## Dónde está el código relevante

- [simulate_g1_rl.py](simulate_g1_rl.py): loop de inferencia descrito arriba.
- [third_party/unitree_rl_gym/deploy/pre_train/g1/motion.pt](third_party/unitree_rl_gym/deploy/pre_train/g1/motion.pt): la política ya entrenada (TorchScript).
- [third_party/unitree_rl_gym/resources/robots/g1_description/g1_12dof.xml](third_party/unitree_rl_gym/resources/robots/g1_description/g1_12dof.xml): el modelo físico (solo piernas) que la política espera controlar.
