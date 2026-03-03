# pylint: disable=no-member
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from sensor_msgs.msg import Image
import cv2
from cv_bridge import CvBridge, CvBridgeError
import threading
import requests
import io
from PIL import Image as PILImage, ImageTk
import tkinter as tk
from tkinter import ttk
import webbrowser
from gtts import gTTS
import pygame
import os
import time

# --- UI Configuration ---
TIST_LOGO_URL = "https://tistcochin.edu.in/wp-content/uploads/2022/08/TISTlog-trans.png"
TIST_WEBSITE_URL = "https://tistcochin.edu.in/"
BG_COLOR = "#0A2239"
TEXT_COLOR = "#FFFFFF"
ACCENT_COLOR = "#005a9e"
FONT_FACE = "Segoe UI"


class MainGuiNode(Node):
    def __init__(self, root):
        super().__init__('main_gui_node')

        # --- ROS2 Publishers and Subscribers ---
        self.video_sub = self.create_subscription(
            Image, '/video_feed', self.video_callback, 10)
        self.user_text_sub = self.create_subscription(
            String, '/transcribed_text', self.user_text_callback, 10)
        self.ai_text_sub = self.create_subscription(
            String, '/ai_response', self.ai_text_callback, 10)
        self.state_sub = self.create_subscription(
            String, '/robot_state', self.state_callback, 10)

        self.text_input_publisher = self.create_publisher(
            String, '/transcribed_text', 10)
        # --- KEY CHANGE: Publisher to signal when TTS is finished ---
        self.finished_speaking_publisher = self.create_publisher(
            String, '/finished_speaking', 10)
        self.perf_publisher = self.create_publisher(
            String, '/performance_metrics', 10)

        self.bridge = CvBridge()
        self.latest_frame = None

        # --- Tkinter UI Setup ---
        self.root = root
        self.setup_ui()

        pygame.mixer.init()
        self.get_logger().info("TTS engine set to gTTS with Pygame.")

        threading.Thread(target=self.load_logo, daemon=True).start()
        self.update_video()
        self.perf_publisher = self.create_publisher(
            String, '/performance_metrics', 10)

    def setup_ui(self):
        self.root.title("TIST AI Assistant")
        self.root.attributes('-fullscreen', True)  # Make window fullscreen
        self.root.configure(bg=BG_COLOR)
        self.text_input_visible = False

        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("TFrame", background=BG_COLOR)
        style.configure("TLabel", background=BG_COLOR,
                        foreground=TEXT_COLOR, font=(FONT_FACE, 12))
        style.configure("TButton", background=ACCENT_COLOR, foreground=TEXT_COLOR, font=(
            FONT_FACE, 11, "bold"), borderwidth=0, padding=10)
        style.map("TButton", background=[("active", "#007bb5")])
        style.configure("TEntry", fieldbackground="#1E3A56",
                        foreground=TEXT_COLOR, borderwidth=1, insertcolor=TEXT_COLOR)

        content_frame = ttk.Frame(self.root, style="TFrame")
        content_frame.pack(side="top", fill="both", expand=True)

        bottom_frame = ttk.Frame(self.root, style="TFrame")
        bottom_frame.pack(side="bottom", fill="x", pady=10, padx=10)

        self.logo_label = ttk.Label(content_frame)
        self.logo_label.pack(pady=(15, 10))
        self.video_label = tk.Label(content_frame, bg=BG_COLOR)
        self.video_label.pack(pady=10, padx=20)
        self.user_text_label = ttk.Label(
            content_frame, text="You: ...", anchor="center")
        self.user_text_label.pack(fill="x", padx=20, pady=(0, 5))
        self.response_label = ttk.Label(content_frame, text="AI: Waiting for interaction...",
                                        wraplength=700, anchor="center", font=(FONT_FACE, 14, "italic"))
        self.response_label.pack(fill="x", padx=20, pady=10)

        self.text_input_frame = ttk.Frame(bottom_frame, style="TFrame")
        self.input_box = ttk.Entry(
            self.text_input_frame, font=(FONT_FACE, 14), width=40)
        self.input_box.pack(side="left", fill="x", expand=True, ipady=5)
        self.input_box.bind("<Return>", lambda event: self.on_submit_text())
        submit_button = ttk.Button(
            self.text_input_frame, text="➜", command=self.on_submit_text, width=3)
        submit_button.pack(side="left", padx=(10, 0))

        self.button_bar_frame = ttk.Frame(bottom_frame, style="TFrame")
        self.button_bar_frame.pack(fill="x", pady=(5, 0))
        self.button_bar_frame.columnconfigure((0, 1, 2), weight=1)

        text_btn = ttk.Button(
            self.button_bar_frame, text="Text Input 📝", command=self.on_text_input_pressed)
        text_btn.grid(row=0, column=0, sticky="ew", padx=5)

        voice_btn = ttk.Button(
            self.button_bar_frame, text="Speak Now 🎤", command=self.on_speak_now_pressed)
        voice_btn.grid(row=0, column=1, sticky="ew", padx=5)

        web_btn = ttk.Button(self.button_bar_frame,
                             text="Visit Website 🌐", command=self.open_website)
        web_btn.grid(row=0, column=2, sticky="ew", padx=5)

    def interrupt_speech(self):
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
            self.get_logger().info("TTS playback interrupted by user.")

    def on_text_input_pressed(self):
        self.interrupt_speech()
        self.toggle_text_input()

    def on_speak_now_pressed(self):
        self.interrupt_speech()
        self.user_text_label.config(text="You: Listening...")

    def speak_text(self, text):
        if not text or pygame.mixer.music.get_busy():
            return

        try:
            self.get_logger().info("Speaking...")
            mp3_fp = io.BytesIO()
            tts = gTTS(text=text, lang='en', slow=False)
            tts.write_to_fp(mp3_fp)
            mp3_fp.seek(0)

            pygame.mixer.music.load(mp3_fp)
            pygame.mixer.music.set_volume(1.0)
            pygame.mixer.music.play()

            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)

        except Exception as e:
            self.get_logger().error(f"Failed to play TTS audio: {e}")
        finally:
            # --- KEY CHANGE: Publish status when speaking is done ---
            finished_msg = String()
            finished_msg.data = "done"
            self.finished_speaking_publisher.publish(finished_msg)
            self.get_logger().info("Finished speaking and published status.")

    def toggle_text_input(self):
        if self.text_input_visible:
            self.text_input_frame.pack_forget()
        else:
            self.text_input_frame.pack(
                fill="x", before=self.button_bar_frame, pady=(0, 5))
            self.input_box.focus_set()
        self.text_input_visible = not self.text_input_visible

    def on_submit_text(self):
        user_input = self.input_box.get().strip()
        if user_input:
            self.input_box.delete(0, tk.END)
            msg = String()
            msg.data = user_input
            self.text_input_publisher.publish(msg)

    def open_website(self):
        webbrowser.open_new_tab(TIST_WEBSITE_URL)

    def load_logo(self):
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(
                TIST_LOGO_URL, headers=headers, stream=True)
            response.raise_for_status()
            logo_image = PILImage.open(io.BytesIO(response.content))
            logo_image.thumbnail((250, 250))
            self.logo_photo = ImageTk.PhotoImage(logo_image)
            self.root.after(0, lambda: self.logo_label.config(
                image=self.logo_photo))
        except Exception as e:
            self.get_logger().error(f"Could not download logo: {e}")

    def video_callback(self, msg):
        try:
            self.latest_frame = self.bridge.imgmsg_to_cv2(msg, "bgr8")
        except CvBridgeError as e:
            self.get_logger().error(f'Failed to convert image: {e}')

    def user_text_callback(self, msg):
        self.interrupt_speech()
        self.root.after(0, lambda: self.user_text_label.config(
            text=f"You: {msg.data}"))
        self.root.after(0, lambda: self.response_label.config(
            text=f"AI: Thinking..."))

    def ai_text_callback(self, msg):
        self.root.after(0, lambda: self.response_label.config(
            text=f"AI: {msg.data}"))
        threading.Thread(target=self.speak_text, args=(
            msg.data,), daemon=True).start()

    def state_callback(self, msg):
        if msg.data == "listening":
            self.root.after(0, lambda: self.user_text_label.config(
                text="You: Listening..."))

    def update_video(self):
        start_time = time.time()  # Start the timer

        if self.latest_frame is not None:
            try:
                # Resize and convert the image for Tkinter
                frame = cv2.cvtColor(self.latest_frame, cv2.COLOR_BGR2RGB)
                frame = cv2.resize(frame, (640, 480))
                imgtk = ImageTk.PhotoImage(image=PILImage.fromarray(frame))
                self.video_label.imgtk = imgtk
                self.video_label.config(image=imgtk)
            except Exception as e:
                self.get_logger().error(f"Error updating video frame: {e}")

        # --- LOGGING LOGIC START ---
        duration = time.time() - start_time

        # Publish the duration so the logger node can save it
        msg = String()
        msg.data = f"gui_node,video_update_loop,{duration:.4f}"
        self.perf_publisher.publish(msg)
        # --- LOGGING LOGIC END ---

        self.root.after(30, self.update_video)


def main(args=None):
    # This environment variable helps with some Tkinter/X11 issues
    os.environ['GDK_BACKEND'] = 'x11'
    rclpy.init(args=args)
    root = tk.Tk()
    gui_node = MainGuiNode(root)

    def ros_spin():
        rclpy.spin(gui_node)

    ros_thread = threading.Thread(target=ros_spin, daemon=True)
    ros_thread.start()

    try:
        root.mainloop()
    finally:
        gui_node.get_logger().info("Shutting down GUI node.")
        gui_node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
