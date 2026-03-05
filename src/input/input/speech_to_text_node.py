import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import speech_recognition as sr  # Only used for mic listing if needed, but we use sounddevice now
import sounddevice as sd
import queue
import sys
import json
import threading
from vosk import Model, KaldiRecognizer

# --- Configuration ---
MIC_NAME_TARGET = "Audio Array"
SAMPLE_RATE = 44100  # The rate that worked for you
BLOCK_SIZE = 16000   # Larger buffer to prevent "input overflow"

class SpeechToTextNode(Node):
    def __init__(self):
        super().__init__('speech_to_text_node')
        
        # ROS Publishers/Subscribers
        self.publisher_ = self.create_publisher(String, '/transcribed_text', 10)
        self.state_subscriber = self.create_subscription(
            String, '/robot_state', self.state_callback, 10)
        
        self.get_logger().info("Loading Vosk Model...")
        
        # 1. Load Vosk Model (Auto-downloaded to ~/.cache/vosk)
        try:
            # We use the name string so it finds the cached model you just downloaded
            self.model = Model(model_name="vosk-model-small-en-us-0.15")
        except Exception as e:
            self.get_logger().error(f"Failed to load model: {e}")
            sys.exit(1)

        # 2. Setup Microphone
        self.device_id = self.find_mic_by_name(MIC_NAME_TARGET)
        if self.device_id is None:
            self.get_logger().warn(f"'{MIC_NAME_TARGET}' not found. Using default mic.")
            self.device_id = None
        else:
            self.get_logger().info(f"Found '{MIC_NAME_TARGET}' at device ID {self.device_id}")

        # 3. Internal State
        self.q = queue.Queue()
        self.stream = None
        self.listening_active = False
        
        # Start the processing thread immediately (it will just wait for data)
        self.process_thread = threading.Thread(target=self.worker_thread, daemon=True)
        self.process_thread.start()

        self.get_logger().info("Node initialized. Waiting for 'listening' state...")

    def find_mic_by_name(self, target_name):
        """Finds the device ID for a microphone by name."""
        try:
            devices = sd.query_devices()
            for i, device in enumerate(devices):
                if device['max_input_channels'] > 0 and target_name.lower() in device['name'].lower():
                    return i
        except Exception:
            pass
        return None

    def state_callback(self, msg):
        """Handles switching between listening and speaking states."""
        if msg.data == "listening" and not self.listening_active:
            self.start_mic_stream()
        elif msg.data != "listening" and self.listening_active:
            self.stop_mic_stream()

    def start_mic_stream(self):
        self.get_logger().info("State: LISTENING. Opening microphone...")
        try:
            self.stream = sd.RawInputStream(
                samplerate=SAMPLE_RATE, 
                blocksize=BLOCK_SIZE, 
                device=self.device_id, 
                dtype='int16', 
                channels=1, 
                callback=self.audio_callback
            )
            self.stream.start()
            self.listening_active = True
        except Exception as e:
            self.get_logger().error(f"Failed to start mic: {e}")

    def stop_mic_stream(self):
        self.get_logger().info("State: SPEAKING. Closing microphone...")
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        self.listening_active = False
        # Clear queue so we don't process old audio later
        with self.q.mutex:
            self.q.queue.clear()

    def audio_callback(self, indata, frames, time, status):
        """Callback from sounddevice - must be fast!"""
        if status:
            # We ignore 'input overflow' to keep logs clean, as we did in testing
            pass
        self.q.put(bytes(indata))

    def worker_thread(self):
        """Thread that continuously processes audio from the queue."""
        rec = KaldiRecognizer(self.model, SAMPLE_RATE)
        
        while rclpy.ok():
            try:
                # Wait for audio data (blocking)
                data = self.q.get(timeout=1.0) 
            except queue.Empty:
                continue

            if rec.AcceptWaveform(data):
                result = json.loads(rec.Result())
                text = result.get("text", "")
                
                if text:
                    self.get_logger().info(f"Transcribed: '{text}'")
                    msg = String()
                    msg.data = text
                    self.publisher_.publish(msg)

def main(args=None):
    rclpy.init(args=args)
    node = SpeechToTextNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.stop_mic_stream()
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
