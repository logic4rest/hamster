---
name: hamster-entertainment
description: >-
  Use this skill when the user asks to play music, play a song, perform a dance, wiggle, or control the gripper of the Hamster robot.
---

# 🐹 Hamster Robot Entertainment Skill

This workspace skill teaches the agent how to play music, control the buzzer, choreograph body dances (wiggling/shaking butt), and actuate the gripper concurrently on the Hamster robot.

---

## 🎵 Available Entertainment Scripts

These scripts are located in the `tools/` folder and can be run directly:

1. **Beethoven - Für Elise (엘리제를 위하여)**:
   - File: [play_furelise.py](file:///C:/Users/User/Desktop/hamster/tools/play_furelise.py)
   - Plays the main melody of Beethoven's famous piano piece.

2. **Grandfather's Clock (할아버지의 낡은 시계)**:
   - File: [play_grandfathers_clock.py](file:///C:/Users/User/Desktop/hamster/tools/play_grandfathers_clock.py)
   - Plays the full song with a synchronized left/right LED ticking animation and a terminal console ticking clock indicator.

3. **JayM - Toy Forest (장난감 숲)**:
   - File: [play_toy_forest.py](file:///C:/Users/User/Desktop/hamster/tools/play_toy_forest.py)
   - Plays the main theme of "Toy Forest" with green/yellow LED flashing and random forest emoji terminal animations.

4. **Super Mario Bros Theme + Wiggling (제자리 엉덩이 흔들기)**:
   - File: [play_mario_wiggle.py](file:///C:/Users/User/Desktop/hamster/tools/play_mario_wiggle.py)
   - Plays the theme song and wiggles the wheels left/right on every note, stopping on rests.

5. **Super Mario Bros Theme + Wiggling + Gripper Clapping (집게 댄스)**:
   - File: [play_mario_gripper.py](file:///C:/Users/User/Desktop/hamster/tools/play_mario_gripper.py)
   - Synthesizes the theme song, body wiggling, and gripper opening/closing. It controls the gripper asynchronously using direct register writes (`OUTPUT_A` and `OUTPUT_B`) to avoid motor blocking delays, toggling the gripper state every 1.0 beat (400 ms) for a clean tempo.

---

## 🛠️ Choreography & Development Guidelines

When creating new songs or dances, follow these guidelines to keep the motion and music synchronized:

### 1. Asynchronous Buzzer Playback
Call `hamster.note(note_name)` **without** the `beats` parameter. This starts the tone asynchronously in the background and returns control to the script immediately, allowing the wheels and grippers to move while the note is playing.

### 2. Direct Register Gripper Control
Do **NOT** use `hamster.open_gripper()` or `hamster.close_gripper()` inside real-time music loops because they block execution for `500 ms` to let the motors finish. Instead, use direct asynchronous register writes:
*   **Open Gripper**:
    ```python
    hamster.write(Hamster.IO_MODE_A, Hamster.IO_MODE_DIGITAL_OUTPUT)
    hamster.write(Hamster.IO_MODE_B, Hamster.IO_MODE_DIGITAL_OUTPUT)
    hamster.write(Hamster.OUTPUT_A, 1)
    hamster.write(Hamster.OUTPUT_B, 0)
    ```
*   **Close Gripper**:
    ```python
    hamster.write(Hamster.IO_MODE_A, Hamster.IO_MODE_DIGITAL_OUTPUT)
    hamster.write(Hamster.IO_MODE_B, Hamster.IO_MODE_DIGITAL_OUTPUT)
    hamster.write(Hamster.OUTPUT_A, 0)
    hamster.write(Hamster.OUTPUT_B, 1)
    ```
*   **Release Gripper**:
    ```python
    hamster.write(Hamster.IO_MODE_A, Hamster.IO_MODE_DIGITAL_OUTPUT)
    hamster.write(Hamster.IO_MODE_B, Hamster.IO_MODE_DIGITAL_OUTPUT)
    hamster.write(Hamster.OUTPUT_A, 0)
    hamster.write(Hamster.OUTPUT_B, 0)
    ```

### 3. Windows Emoji Encoding Protection
Always force UTF-8 output encoding at the start of any script that prints emojis or unicode characters to prevent CP949 runtime crashes:
```python
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
```
