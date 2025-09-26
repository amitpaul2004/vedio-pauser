import cv2
import mediapipe as mp
import time
import math
import socket

class GestureControllerClient:
    def __init__(self):
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(min_detection_confidence=0.7, min_tracking_confidence=0.7)
        self.mp_draw = mp.solutions.drawing_utils
        
        self.last_gesture_time = 0
        self.gesture_cooldown = 2
        
        self.client_socket = None
        self.connect_to_server()

    def connect_to_server(self):
        """Connects the client to the server socket."""
        host = '127.0.0.1'  # localhost
        port = 65432
        
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.client_socket.connect((host, port))
            print("✅ Connected to Video Player Server.")
        except ConnectionRefusedError:
            print("❌ Connection failed. Is the video_player_server.py script running?")
            self.client_socket = None

    def send_command(self, command):
        """Sends a command to the server if connected."""
        if self.client_socket:
            try:
                self.client_socket.sendall(command.encode('utf-8'))
                print(f"Sent command: {command}")
            except (ConnectionResetError, BrokenPipeError):
                print("❌ Lost connection to the server.")
                self.client_socket = None

    def run(self):
        """The main loop to capture webcam and detect gestures."""
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("Error: Could not open webcam.")
            return

        while cap.isOpened():
            success, image = cap.read()
            if not success: continue

            image = cv2.cvtColor(cv2.flip(image, 1), cv2.COLOR_BGR2RGB)
            results = self.hands.process(image)
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    self.mp_draw.draw_landmarks(image, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)
                    self.recognize_gesture(hand_landmarks)
            
            cv2.imshow('Gesture Controller (Client)', image)
            if cv2.waitKey(5) & 0xFF == 27: # ESC to exit
                break
        
        cap.release()
        if self.client_socket: self.client_socket.close()
        cv2.destroyAllWindows()

    def recognize_gesture(self, landmarks):
        if time.time() - self.last_gesture_time < self.gesture_cooldown: return

        lm = landmarks.landmark
        
        index_extended = lm[self.mp_hands.HandLandmark.INDEX_FINGER_TIP].y < lm[self.mp_hands.HandLandmark.INDEX_FINGER_PIP].y
        thumb_extended = lm[self.mp_hands.HandLandmark.THUMB_TIP].y < lm[self.mp_hands.HandLandmark.THUMB_IP].y
        all_curled = not any([
            index_extended,
            lm[self.mp_hands.HandLandmark.MIDDLE_FINGER_TIP].y < lm[self.mp_hands.HandLandmark.MIDDLE_FINGER_PIP].y,
            lm[self.mp_hands.HandLandmark.RING_FINGER_TIP].y < lm[self.mp_hands.HandLandmark.RING_FINGER_PIP].y,
            lm[self.mp_hands.HandLandmark.PINKY_FINGER_TIP].y < lm[self.mp_hands.HandLandmark.PINKY_FINGER_PIP].y,
        ])
        
        command = None
        if all_curled: command = 'PAUSE'
        elif thumb_extended and not index_extended: command = 'PLAY'
        elif index_extended:
            index_tip_x = lm[self.mp_hands.HandLandmark.INDEX_FINGER_TIP].x
            index_mcp_x = lm[self.mp_hands.HandLandmark.INDEX_FINGER_MCP].x
            if index_tip_x > index_mcp_x: command = 'SEEK_10'
            else: command = 'SEEK_-10'

        if command:
            self.send_command(command)
            self.last_gesture_time = time.time()

if __name__ == "__main__":
    controller = GestureControllerClient()
    controller.run()