# Driver Drowsiness Detection

A prototype that detects driver drowsiness using the laptop camera and sends an alert level (0-3) to an ESP32 (buzzer, LEDs, motor).

## How it works
- A pre-trained MediaPipe Face Landmarker model (by Google) outputs blendshape scores for the face, such as eye closure and mouth opening.
- Our Python code adds time-based logic on top of those scores:
  - how long the eyes stay closed
  - PERCLOS (fraction of time the eyes are closed in the last 30 seconds)
  - yawning duration
  - loss of the face from the frame (looking away or head down)
- The result is an alert level sent to the ESP32 over USB serial.

## Alert levels
| Level | Meaning | Trigger |
|---|---|---|
| 0 | Awake | normal |
| 1 | Warning | eyes closed for 0.7 s, high PERCLOS, or yawning |
| 2 | Strong warning | eyes closed for 1.2 s, long yawn, or no face for 2 s |
| 3 | Danger | eyes closed for 2 s, or no face for 4 s |

## Run
```bash
pip install -r requirements.txt
python drowsy.py
```
Press ESC to quit. Keep `face_landmarker.task` in the same folder as `drowsy.py`.

## Hardware (ESP32)
The ESP32 side (buzzer, red/green LEDs, push button, L293D motor driver with a motor) is designed but has not yet been built or tested together with the AI part. Without a board connected, the Python program still runs and shows the alert level on screen.

## Limitations
- Thresholds were tuned by testing on one person with a laptop camera.
- Lighting, glasses, and camera angle affect accuracy.
- Educational prototype, not a certified safety system.