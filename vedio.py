import tkinter as tk
from tkinter import filedialog
import cv2
from PIL import Image, ImageTk
import threading
import time
import mediapipe as mp

class GestureVideoPlayer:
    def __init__(self, window, title):
        self.window = window
        self.window.title(title)

        # --- Video Player State ---
        self.video_source = ""
        self.cap = None
        self.paused = True
        self.video_thread = None
        
        # --- Gesture Control State ---
        self.gesture_thread = None
        self.webcam_cap = None
        self.last_gesture_time = 0
        self.gesture_cooldown = 2  # 2 seconds cooldown between gestures

        # --- MediaPipe Hand Tracking Setup ---
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(min_detection_confidence=0.7, min_tracking_confidence=0.7)
        self.mp_draw = mp.solutions.drawing_utils

        # --- GUI Setup ---
        # Create a canvas to display the video
        self.canvas = tk.Canvas(window, width=800, height=600, bg='black')
        self.canvas.pack()

        # Create a frame for the control buttons
        btn_frame = tk.Frame(window)
        btn_frame.pack(fill=tk.X, expand=True)

        # Control Buttons
        self.btn_open = tk.Button(btn_frame, text="Open Video", command=self.open_file)
        self.btn_open.pack(side=tk.LEFT, padx=5, pady=5)
        
        self.btn_play_pause = tk.Button(btn_frame, text="Play", command=self.toggle_play_pause)
        self.btn_play_pause.pack(side=tk.LEFT, padx=5, pady=5)

        # Start the gesture recognition thread
        self.start_gesture_control()

        # Close the window gracefully
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)

    def open_file(self):
        """Opens a video file selected by the user."""
        self.video_source = filedialog.askopenfilename(filetypes=[("Video files", "*.mp4 *.avi *.mkv")])
        if not self.video_source:
            return

        if self.cap:
            self.cap.release()
            
        self.cap = cv2.VideoCapture(self.video_source)
        self.paused = False
        self.btn_play_pause.config(text="Pause")
        
        if self.video_thread is None:
            self.video_thread = threading.Thread(target=self.stream_video)
            self.video_thread.daemon = True
            self.video_thread.start()

    def stream_video(self):
        """Main loop for reading and displaying video frames."""
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
        """Toggles the video's paused state."""
        if not self.cap or not self.cap.isOpened():
            return
            
        if self.paused:
            self.play_video()
        else:
            self.pause_video()
            
    def play_video(self):
        self.paused = False
        self.btn_play_pause.config(text="Pause")
        print("Gesture: Play")

    def pause_video(self):
        self.paused = True
        self.btn_play_pause.config(text="Play")
        print("Gesture: Pause")

    def seek(self, seconds):
        """Seeks the video by a specified number of seconds."""
        if self.cap and self.cap.isOpened():
            current_frame = self.cap.get(cv2.CAP_PROP_POS_FRAMES)
            fps = self.cap.get(cv.CAP_PROP_FPS)
            if fps > 0:
                new_frame = current_frame + (seconds * fps)
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, new_frame)
                print(f"Gesture: Seek {seconds}s")
    
    def start_gesture_control(self):
        """Starts the gesture control loop in a separate thread."""
        self.webcam_cap = cv2.VideoCapture(0) # Use default webcam
        self.gesture_thread = threading.Thread(target=self.run_gesture_control)
        self.gesture_thread.daemon = True
        self.gesture_thread.start()

    def run_gesture_control(self):
        """Main loop for capturing webcam feed and recognizing gestures."""
        while self.webcam_cap.isOpened():
            success, image = self.webcam_cap.read()
            if not success:
                continue

            # Flip the image horizontally for a later selfie-view display
            image = cv2.cvtColor(cv2.flip(image, 1), cv2.COLOR_BGR2RGB)
            results = self.hands.process(image)
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    self.mp_draw.draw_landmarks(image, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)
                    self.recognize_gesture(hand_landmarks)

            cv2.imshow('Gesture Control', image)
            if cv2.waitKey(5) & 0xFF == 27: # Press ESC to exit
                break
        
        self.webcam_cap.release()
        cv2.destroyWindow('Gesture Control')

    def recognize_gesture(self, landmarks):
        """Identifies a gesture based on hand landmark positions."""
        # Check for cooldown
        if time.time() - self.last_gesture_time < self.gesture_cooldown:
            return

        lm = landmarks.landmark
        
        # Gesture 1: Thumbs Up (Play) vs Thumbs Down (Pause)
        # Check if thumb tip is above its lower joints
        thumb_tip_y = lm[self.mp_hands.HandLandmark.THUMB_TIP].y
        thumb_mcp_y = lm[self.mp_hands.HandLandmark.THUMB_MCP].y
        
        # Check if other fingers are curled (below their base)
        index_curled = lm[self.mp_hands.HandLandmark.INDEX_FINGER_TIP].y > lm[self.mp_hands.HandLandmark.INDEX_FINGER_PIP].y
        middle_curled = lm[self.mp_hands.HandLandmark.MIDDLE_FINGER_TIP].y > lm[self.mp_hands.HandLandmark.MIDDLE_FINGER_PIP].y
        
        if index_curled and middle_curled:
            if thumb_tip_y < thumb_mcp_y:
                self.play_video()
                self.last_gesture_time = time.time()
                return
            elif thumb_tip_y > thumb_mcp_y:
                self.pause_video()
                self.last_gesture_time = time.time()
                return

        # Gesture 2: Pointing Left/Right (Seek)
        # Check if index finger is extended and others are curled
        index_extended = lm[self.mp_hands.HandLandmark.INDEX_FINGER_TIP].y < lm[self.mp_hands.HandLandmark.INDEX_FINGER_PIP].y
        
        if index_extended and middle_curled:
            index_tip_x = lm[self.mp_hands.HandLandmark.INDEX_FINGER_TIP].x
            index_mcp_x = lm[self.mp_hands.HandLandmark.INDEX_FINGER_MCP].x
            
            if index_tip_x > index_mcp_x + 0.05: # Pointing Right
                self.seek(10)
                self.last_gesture_time = time.time()
            elif index_tip_x < index_mcp_x - 0.05: # Pointing Left
                self.seek(-10)
                self.last_gesture_time = time.time()

    def on_closing(self):
        """Handles the window closing event."""
        if self.cap:
            self.cap.release()
        if self.webcam_cap:
            self.webcam_cap.release()
        cv2.destroyAllWindows()
        self.window.destroy()

# --- Main Application Start ---
if __name__ == "__main__":
    root = tk.Tk()
    player = GestureVideoPlayer(root, "Gesture Controlled Video Player")
    root.mainloop()