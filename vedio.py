import tkinter as tk
from tkinter import filedialog
import cv2
from PIL import Image, ImageTk
import threading
import time

class VideoPlayer:
    def __init__(self, window, title):
        self.window = window
        self.window.title(title)

        self.video_source = ""
        self.cap = None
        self.paused = True
        self.thread = None

        # Create a canvas to display the video
        self.canvas = tk.Canvas(window, width=800, height=600, bg='black')
        self.canvas.pack()

        # Create a frame for the control buttons
        btn_frame = tk.Frame(window)
        btn_frame.pack(fill=tk.X, expand=True)

        # Control Buttons
        self.btn_open = tk.Button(btn_frame, text="Open Video", command=self.open_file)
        self.btn_open.pack(side=tk.LEFT, padx=5, pady=5)
        
        self.btn_prev = tk.Button(btn_frame, text="<< 10s", command=self.seek_backward)
        self.btn_prev.pack(side=tk.LEFT, padx=5, pady=5)

        self.btn_play_pause = tk.Button(btn_frame, text="Play", command=self.play_pause)
        self.btn_play_pause.pack(side=tk.LEFT, padx=5, pady=5)
        
        self.btn_next = tk.Button(btn_frame, text=">> 10s", command=self.seek_forward)
        self.btn_next.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Close the window gracefully
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    def open_file(self):
        """Opens a video file selected by the user."""
        self.video_source = filedialog.askopenfilename(
            filetypes=[("Video files", "*.mp4 *.avi *.mkv *.mov")]
        )
        if not self.video_source:
            return

        # Release any existing video capture and start a new one
        if self.cap:
            self.cap.release()
            
        self.cap = cv2.VideoCapture(self.video_source)
        self.paused = False
        self.btn_play_pause.config(text="Pause")
        
        # Start the video streaming in a new thread
        if self.thread is None:
            self.thread = threading.Thread(target=self.stream_video)
            self.thread.daemon = 1 # Daemonize thread to exit when main program exits
            self.thread.start()

    def stream_video(self):
        """Main loop for reading and displaying video frames."""
        while True:
            if self.cap and self.cap.isOpened() and not self.paused:
                ret, frame = self.cap.read()
                if ret:
                    # Convert the frame to a format Tkinter can use
                    img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    img = Image.fromarray(img)
                    
                    # Resize image to fit the canvas
                    canvas_width = self.canvas.winfo_width()
                    canvas_height = self.canvas.winfo_height()
                    img.thumbnail((canvas_width, canvas_height), Image.Resampling.LANCZOS)
                    
                    self.photo = ImageTk.PhotoImage(image=img)
                    self.canvas.create_image(0, 0, image=self.photo, anchor=tk.NW)
                else:
                    # End of video
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    self.paused = True
                    self.btn_play_pause.config(text="Play")
                    
            # Control the frame rate
            time.sleep(1 / 30) # Roughly 30 FPS

    def play_pause(self):
        """Toggles the video's paused state."""
        if self.cap and self.cap.isOpened():
            self.paused = not self.paused
            if self.paused:
                self.btn_play_pause.config(text="Play")
            else:
                self.btn_play_pause.config(text="Pause")

    def seek_forward(self):
        """Jumps 10 seconds forward in the video."""
        self.seek(10)

    def seek_backward(self):
        """Jumps 10 seconds backward in the video."""
        self.seek(-10)

    def seek(self, seconds):
        """Seeks the video by a specified number of seconds."""
        if self.cap and self.cap.isOpened():
            # Get current frame number and frames per second
            current_frame = self.cap.get(cv2.CAP_PROP_POS_FRAMES)
            fps = self.cap.get(cv2.CAP_PROP_FPS)
            
            if fps > 0:
                # Calculate the new frame position
                new_frame = current_frame + (seconds * fps)
                total_frames = self.cap.get(cv2.CAP_PROP_FRAME_COUNT)

                # Ensure the new frame is within the video's bounds
                if 0 <= new_frame < total_frames:
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, new_frame)

    def on_closing(self):
        """Handles the window closing event."""
        if self.cap:
            self.cap.release()
        self.window.destroy()

# Create the main window and run the application
if __name__ == "__main__":
    root = tk.Tk()
    player = VideoPlayer(root, "Simple Python Video Player")
    root.mainloop()