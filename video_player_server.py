import tkinter as tk
from tkinter import filedialog
import cv2
from PIL import Image, ImageTk
import threading
import time
import socket

class VideoPlayerServer:
    def __init__(self, window, title):
        self.window = window
        self.window.title(title)
        
        # --- Video Player State ---
        self.cap = None
        self.paused = True
        
        # --- GUI Setup ---
        self.canvas = tk.Canvas(window, width=800, height=600, bg='black')
        self.canvas.pack()
        self.btn_open = tk.Button(window, text="Open Video", command=self.open_file)
        self.btn_open.pack()
        
        # --- Start network server thread ---
        self.start_server()
        
        self.video_thread = threading.Thread(target=self.stream_video)
        self.video_thread.daemon = True
        self.video_thread.start()

        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)

    def start_server(self):
        """Initializes and starts the socket server in a new thread."""
        server_thread = threading.Thread(target=self.listen_for_commands)
        server_thread.daemon = True
        server_thread.start()

    def listen_for_commands(self):
        """The server's main loop to listen for commands from the client."""
        host = '127.0.0.1'  # localhost
        port = 65432
        
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((host, port))
            s.listen()
            print(f"✅ Player Server listening on {host}:{port}")
            conn, addr = s.accept()
            with conn:
                print(f"Gesture Controller connected from {addr}")
                while True:
                    data = conn.recv(1024)
                    if not data:
                        break
                    command = data.decode('utf-8')
                    # Use window.after to safely update GUI from this thread
                    self.window.after(0, self.handle_command, command)

    def handle_command(self, command):
        """Executes a player action based on the received command."""
        print(f"Received command: {command}")
        if command == 'PLAY': self.play_video()
        elif command == 'PAUSE': self.pause_video()
        elif command == 'SEEK_10': self.seek(10)
        elif command == 'SEEK_-10': self.seek(-10)
        elif command == 'RESTART': self.restart_video()

    def open_file(self):
        video_source = filedialog.askopenfilename()
        if not video_source: return
        self.cap = cv2.VideoCapture(video_source)
        self.play_video()

    def stream_video(self):
        while True:
            if self.cap and not self.paused:
                ret, frame = self.cap.read()
                if ret:
                    img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    img = Image.fromarray(img)
                    self.photo = ImageTk.PhotoImage(image=img)
                    self.canvas.create_image(0, 0, image=self.photo, anchor=tk.NW)
                else: self.pause_video()
            time.sleep(1 / 30)

    def play_video(self): self.paused = False
    def pause_video(self): self.paused = True
    def restart_video(self):
        if self.cap: self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    def seek(self, seconds):
        if self.cap:
            current_frame = self.cap.get(cv2.CAP_PROP_POS_FRAMES)
            fps = self.cap.get(cv2.CAP_PROP_FPS)
            if fps > 0:
                new_frame = current_frame + (seconds * fps)
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, new_frame)

    def on_closing(self):
        if self.cap: self.cap.release()
        self.window.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    player = VideoPlayerServer(root, "Video Player (Server)")
    root.mainloop()