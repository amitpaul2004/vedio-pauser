import tkinter as tk
from tkinter import filedialog
import cv2
from PIL import Image, ImageTk
import threading
import time
import mediapipe as mp
import math # Needed for distance calculation

class GestureVideoPlayer:
    def __init__(self, window, title):
        self.window = window
        self.window.title(title)

        # --- Video Player State ---
        self.video_source = ""
        self.cap = None
        self.paused = True
        self.is_muted = False # New state for mute
        self.video_thread = None
        
        # --- Gesture Control State ---
        self.gesture_thread = None
        self.webcam_cap = None
        self.last_gesture_time = 0
        self.gesture_cooldown = 2

        # --- MediaPipe Hand Tracking Setup ---
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(min_detection_confidence=0.7, min_tracking_confidence=0.7)
        self.mp_draw = mp.solutions.drawing_utils

        # --- GUI Setup ---
        self.canvas = tk.Canvas(window, width=800, height=600, bg='black')
        self.canvas.pack()
        btn_frame = tk.Frame(window)
        btn_frame.pack(fill=tk.X, expand=True)
        self.btn_open = tk.Button(btn_frame, text="Open Video", command=self.open_file)
        self.btn_open.pack(side=tk.LEFT, padx=5, pady=5)
        self.btn_play_pause = tk.Button(btn_frame, text="Play", command=self.toggle_play_pause)
        self.btn_play_pause.pack(side=tk.LEFT, padx=5, pady=5)

        self.start_gesture_control()
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)

    def open_file(self):
        self.video_source = filedialog.askopenfilename(filetypes=[("Video files", "*.mp4 *.avi *.mkv")])
        if not self.video_source: return
        if self.cap: self.cap.release()
        self.cap = cv2.VideoCapture(self.video_source)
        self.paused = False
        self.btn_play_pause.config(text="Pause")
        if self.video_thread is None:
            self.video_thread = threading.Thread(target=self.stream_video)
            self.video_thread.daemon = True
            self.video_thread.start()

    def stream_video(self):
        while True:
            if self.cap and self.cap.isOpened() and not self.paused:
                ret, frame = self.cap.read()
                if ret:
                    img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    img = Image.fromarray(img)
                    canvas_width = self.canvas.winfo_width()
                    canvas_height = self.canvas.winfo_height()
                    img.thumbnail((canvas_width, canvas_height), Image.Resampling.LANCZOS)
                    self.photo = ImageTk.PhotoImage(image=img)
                    self.canvas.create_image(0, 0, image=self.photo, anchor=tk.NW)
                else:
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    self.paused = True
                    self.btn_play_pause.config(text="Play")
            time.sleep(1 / 30)

    def toggle_play_pause(self):
        if not self.cap or not self.cap.isOpened(): return
        if self.paused: self.play_video()
        else: self.pause_video()
            
    def play_video(self):
        self.paused = False
        self.btn_play_pause.config(text="Pause")
        print("Action: Play")

    def pause_video(self):
        self.paused = True
        self.btn_play_pause.config(text="Play")
        print("Action: Pause")

    def seek(self, seconds):
        if self.cap and self.cap.isOpened():
            current_frame = self.cap.get(cv2.CAP_PROP_POS_FRAMES)
            fps = self.cap.get(cv2.CAP_PROP_FPS)
            if fps > 0:
                new_frame = current_frame + (seconds * fps)
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, new_frame)
                print(f"Action: Seek {seconds}s")
    
    # --- New Action Methods ---
    def toggle_mute(self):
        self.is_muted = not self.is_muted
        status = "Muted" if self.is_muted else "Unmuted"
        print(f"Action: {status}")

    def restart_video(self):
        if self.cap and self.cap.isOpened():
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            print("Action: Restart Video")

    def start_gesture_control(self):
        self.webcam_cap = cv2.VideoCapture(0)
        if not self.webcam_cap.isOpened():
            print("❌ Error: Could not open webcam. Gesture control is disabled.")
            return
        self.gesture_thread = threading.Thread(target=self.run_gesture_control)
        self.gesture_thread.daemon = True
        self.gesture_thread.start()

    def run_gesture_control(self):
        while self.webcam_cap.isOpened():
            success, image = self.webcam_cap.read()
            if not success:
                continue
            image = cv2.cvtColor(cv2.flip(image, 1), cv2.COLOR_BGR2RGB)
            results = self.hands.process(image)
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    self.mp_draw.draw_landmarks(image, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)
                    self.recognize_gesture(hand_landmarks)
            cv2.imshow('Gesture Control', image)
            if cv2.waitKey(5) & 0xFF == 27:
                break
        self.webcam_cap.release()
        cv2.destroyWindow('Gesture Control')

    def recognize_gesture(self, landmarks):
        if time.time() - self.last_gesture_time < self.gesture_cooldown: return

        lm = landmarks.landmark
        
        # Define finger states (True if extended, False if curled)
        index_extended = lm[self.mp_hands.HandLandmark.INDEX_FINGER_TIP].y < lm[self.mp_hands.HandLandmark.INDEX_FINGER_PIP].y
        middle_extended = lm[self.mp_hands.HandLandmark.MIDDLE_FINGER_TIP].y < lm[self.mp_hands.HandLandmark.MIDDLE_FINGER_PIP].y
        ring_extended = lm[self.mp_hands.HandLandmark.RING_FINGER_TIP].y < lm[self.mp_hands.HandLandmark.RING_FINGER_PIP].y
        pinky_extended = lm[self.mp_hands.HandLandmark.PINKY_FINGER_TIP].y < lm[self.mp_hands.HandLandmark.PINKY_FINGER_PIP].y
        thumb_extended = lm[self.mp_hands.HandLandmark.THUMB_TIP].y < lm[self.mp_hands.HandLandmark.THUMB_IP].y
        
        # --- Gesture 1: Fist (Pause) ---
        if not any([index_extended, middle_extended, ring_extended, pinky_extended]):
            self.pause_video()
            self.last_gesture_time = time.time()
            return

        # --- Gesture 2: Thumbs Up (Play) ---
        if thumb_extended and not any([index_extended, middle_extended, ring_extended, pinky_extended]):
            self.play_video()
            self.last_gesture_time = time.time()
            return

        # --- NEW Gesture 3: Peace Sign (Mute/Unmute) ---
        if index_extended and middle_extended and not ring_extended and not pinky_extended:
            self.toggle_mute()
            self.last_gesture_time = time.time()
            return
            
        # --- NEW Gesture 4: Okay Sign (Restart) ---
        # Check distance between thumb tip and index tip
        thumb_tip = lm[self.mp_hands.HandLandmark.THUMB_TIP]
        index_tip = lm[self.mp_hands.HandLandmark.INDEX_FINGER_TIP]
        distance = math.sqrt((thumb_tip.x - index_tip.x)**2 + (thumb_tip.y - index_tip.y)**2)
        
        if distance < 0.05 and middle_extended and ring_extended and pinky_extended:
            self.restart_video()
            self.last_gesture_time = time.time()
            return

        # --- Gesture 5: Pointing Left/Right (Seek) ---
        if index_extended and not middle_extended and not ring_extended and not pinky_extended:
            index_tip_x = lm[self.mp_hands.HandLandmark.INDEX_FINGER_TIP].x
            index_mcp_x = lm[self.mp_hands.HandLandmark.INDEX_FINGER_MCP].x
            if index_tip_x > index_mcp_x: self.seek(10)
            else: self.seek(-10)
            self.last_gesture_time = time.time()

    def on_closing(self):
        if self.cap: self.cap.release()
        if self.webcam_cap and self.webcam_cap.isOpened(): self.webcam_cap.release()
        cv2.destroyAllWindows()
        self.window.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    player = GestureVideoPlayer(root, "Gesture Controlled Video Player")
    root.mainloop()