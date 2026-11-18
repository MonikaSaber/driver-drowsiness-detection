import cv2, time
import mediapipe as mp
from mediapipe.tasks import python as mpp
from mediapipe.tasks.python import vision
from collections import deque

# ---------- ESP32 Configuration ----------
PORT = "COM3"
try:
    import serial
    ser = serial.Serial(PORT, 115200, timeout=0.01)
    time.sleep(2)
except Exception as e:
    print("ESP32 not connected:", e)
    ser = None

# ---------- Model Setup ----------
opts = vision.FaceLandmarkerOptions(
    base_options=mpp.BaseOptions(model_asset_path="face_landmarker.task"),
    output_face_blendshapes=True, num_faces=1)
landmarker = vision.FaceLandmarker.create_from_options(opts)

# ---------- Thresholds & Settings (tune with the on-screen values) ----------
BLINK_THR = 0.4          # above this = eyes closed
YAWN_THR = 0.4           # above this = mouth wide open
T1, T2, T3 = 0.7, 1.2, 2.0       # seconds of eye closure for levels 1, 2, 3
GAP = 0.3                # tolerated "flicker" (seconds) before a timer resets
NO_FACE_L2, NO_FACE_L3 = 2.0, 4.0   # seconds without a face

cap = cv2.VideoCapture(0)
closed_since = yawn_since = no_face_since = None
last_closed = last_yawn = 0
hist = deque()
grace_until = 0
last_send = 0

while True:
    ok, frame = cap.read()
    if not ok:
        print("Camera not working")
        break
    now = time.time()

    # ESP32 Button Check
    if ser:
        while ser.in_waiting:
            if ser.readline().decode(errors="ignore").strip() == "BTN":
                grace_until = now + 5
                closed_since = yawn_since = None
                hist.clear()

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    res = landmarker.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb))

    level, blink, jaw, dur, ydur = 0, 0.0, 0.0, 0.0, 0.0
    if res.face_blendshapes:
        no_face_since = None
        b = {c.category_name: c.score for c in res.face_blendshapes[0]}
        blink = (b["eyeBlinkLeft"] + b["eyeBlinkRight"]) / 2
        jaw = b["jawOpen"]
        closed = blink > BLINK_THR
        yawning = jaw > YAWN_THR

        # eye closure timer (tolerates short flicker)
        if closed:
            closed_since = closed_since or now
            last_closed = now
        elif closed_since and now - last_closed > GAP:
            closed_since = None
        dur = (now - closed_since) if closed_since else 0

        # yawn timer (tolerates short flicker)
        if yawning:
            yawn_since = yawn_since or now
            last_yawn = now
        elif yawn_since and now - last_yawn > GAP:
            yawn_since = None
        ydur = (now - yawn_since) if yawn_since else 0

        # PERCLOS over the last 30 seconds
        hist.append((now, closed))
        while hist and now - hist[0][0] > 30:
            hist.popleft()
        perclos = sum(c for _, c in hist) / max(len(hist), 1)

        if dur >= T3:   level = 3
        elif dur >= T2: level = 2
        elif dur >= T1: level = 1
        if perclos > 0.30 or ydur > 1.5:
            level = max(level, 1)
        if ydur > 3.0:
            level = max(level, 2)
    else:
        # face lost (looking away, head down, or eyes shut hard)
        no_face_since = no_face_since or now
        lost = now - no_face_since
        if lost > NO_FACE_L3:   level = 3
        elif lost > NO_FACE_L2: level = 2

    if now < grace_until:
        level = 0

    if ser and now - last_send > 0.2:
        ser.write(f"{level}\n".encode())
        last_send = now

    color = (0, 255, 0) if level < 2 else (0, 0, 255)
    cv2.putText(frame, f"Level {level}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)
    cv2.putText(frame, f"blink {blink:.2f}  jaw {jaw:.2f}", (10, 60),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
    cv2.putText(frame, f"eyes closed {dur:.1f}s  yawn {ydur:.1f}s", (10, 85),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
    cv2.imshow("Drowsiness", frame)
    if cv2.waitKey(1) & 0xFF == 27:   # ESC
        break

if ser:
    ser.write(b"0\n")
cap.release()
cv2.destroyAllWindows()