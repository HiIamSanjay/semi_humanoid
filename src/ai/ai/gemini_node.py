import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import google.generativeai as genai
import os

# --- Configuration Constants ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable not set!")

GEMINI_MODEL = "gemini-2.5-flash"
# --- Keyword Lists (from your reference script) ---
MIRROR_KEYWORDS = ["mirror my emotion", "copy me", "mirror me"]
STOP_MIRROR_KEYWORDS = ["stop mirroring", "stop copying", "that's enough"]

# This context is now part of the system instruction
COLLEGE_CONTEXT = """
# Toc H Institute of Science and Technology (TIST) - Detailed Information
...
"""

# This prompt now serves as the system instruction for the AI's persona
SYSTEM_INSTRUCTION = fSYSTEM_INSTRUCTION = """
You are a friendly, helpful robot assistant at the Toc H Institute of Science and Technology.
Your knowledge base includes detailed information about the college and general inforamtion accessible in the intrernet.

**RESPONSE PROTOCOL**
1.  Analyze the user's query in the context of the ongoing conversation.
2.  Generate a helpful and concise response.
3.  Only provide the clean text answer without * (asterisk)symbols.
"""


class GeminiNode(Node):
    """
    This node processes transcribed text with Gemini AI and now also controls
    the emotion recognition and animation nodes based on user commands.
    """

    def __init__(self):
        super().__init__('gemini_node')

        self.subscription = self.create_subscription(
            String, '/transcribed_text', self.text_callback, 10)
        self.publisher = self.create_publisher(String, '/ai_response', 10)

        # --- Publishes to a single control topic for both nodes ---
        self.emotion_control_publisher = self.create_publisher(
            String, '/emotion_recognition_control', 10)

        try:
            genai.configure(api_key=GEMINI_API_KEY)
            model = genai.GenerativeModel(
                GEMINI_MODEL, system_instruction=SYSTEM_INSTRUCTION)
            self.chat = model.start_chat()
            self.get_logger().info("Gemini AI model initialized with conversation history.")
        except Exception as e:
            self.get_logger().error(f"Failed to initialize Gemini AI: {e}")
            self.destroy_node()
            return

        self.get_logger().info("AI node started. Waiting for transcribed text...")

    def publish_emotion_control(self, command):
        """Publishes a command to start or stop emotion mirroring."""
        msg = String()
        msg.data = command
        self.emotion_control_publisher.publish(msg)
        self.get_logger().info(
            f'Published emotion control command: "{command}"')

    def publish_ai_response(self, text):
        """Publishes the AI's verbal response."""
        msg = String()
        msg.data = text
        self.publisher.publish(msg)

    def text_callback(self, msg):
        """
        Processes user text, checks for control keywords, and gets AI response.
        """
        user_query = msg.data
        user_query_lower = user_query.lower()
        self.get_logger().info(
            f'Received text for AI processing: "{user_query}"')

        # --- KEY CHANGE: Send more specific commands ---
        if any(keyword in user_query_lower for keyword in MIRROR_KEYWORDS):
            self.publish_emotion_control("start_mirroring")
            self.publish_ai_response("Okay, I am now mirroring your emotion.")
            return

        if any(keyword in user_query_lower for keyword in STOP_MIRROR_KEYWORDS):
            self.publish_emotion_control("stop_mirroring")
            self.publish_ai_response("Okay, I will stop mirroring you.")
            return

        try:
            self.get_logger().info("Sending request to Gemini API (with history)...")
            response = self.chat.send_message(user_query)
            ai_response_text = response.text.strip()
            self.get_logger().info(
                f'Received AI response: "{ai_response_text}"')
            self.publish_ai_response(ai_response_text)
        except Exception as e:
            self.get_logger().error(
                f"An error occurred during Gemini API call: {e}")


def main(args=None):
    rclpy.init(args=args)
    gemini_node = GeminiNode()
    if hasattr(gemini_node, 'chat'):
        rclpy.spin(gemini_node)
    gemini_node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
