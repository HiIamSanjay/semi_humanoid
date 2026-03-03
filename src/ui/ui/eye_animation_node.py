import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Bool
import pygame
import time
import random
import numpy as np
import math
import os

# --- Pygame Initialization ---
# MOVED: os.environ setup is now handled in the launch file or external env vars.
# This ensures we don't overwrite the settings provided by ros2 launch.

pygame.init()

# --- Display Configuration ---
# We configure the display mode.
# If you want it FULLSCREEN on the specific monitor, you can switch flags.
# For now, we keep NOFRAME so it looks like a clean robot face.
pygame.display.set_mode((1, 1), pygame.NOFRAME) 
info = pygame.display.Info()

# Keeping your resolution. If you want it to fill the 1920x1080 screen, 
# you can change this to 1920, 1080, but ensure your drawing logic scales well.
WIDTH, HEIGHT = 1280, 720 

# --- Configuration ---
# Colors
EYE_COLOR = (0, 136, 255); HAPPY_COLOR = (0, 136, 255); GREET_COLOR = (0, 255, 0)
LID_COLOR = (0, 0, 0); BG_COLOR = (0, 0, 0); SMILE_COLOR = HAPPY_COLOR
ANGRY_COLOR = (255, 0, 0); PAMPER_COLOR = (255, 100, 100); TEAR_COLOR = (173, 216, 230)
SURPRISE_COLOR = (255, 255, 0); FEAR_COLOR = (180, 150, 255)
SPEAKING_COLOR = (200, 220, 255)

# Eye Parameters
EYE_WIDTH, EYE_HEIGHT = 180, 180; EYE_CORNER_RADIUS = 45
EYE_Y_POS = HEIGHT // 2 - EYE_HEIGHT // 2 - 100; EYE_SPACING = 300

# Animation Timings
EMOTION_ANIM_DURATION = 0.3; BLINK_DURATION = 0.1

# Emotion-Specific Animation Parameters
HAPPY_CONFIG = {"bounce_speed": 5, "bounce_amp": 8, "squint": 0.4}
SAD_CONFIG = {"gaze_x_amp": -20, "gaze_y_amp": 30, "droop_factor": 1.5, "mouth_float_speed": 8, "mouth_float_amp": 3, "tear_start_progress": 0.3, "tear_size": 40}
FEAR_CONFIG = {"wobble_speed": 15, "wobble_amp": 5, "pupil_scale": 0.8}
SURPRISE_CONFIG = {"scale_amp": 1.3, "mouth_size": 80}
PAMPER_CONFIG = {"glow_speed": 4, "glow_amp": 0.1, "bounce_speed": 3, "bounce_amp": 6, "stretch_speed": 6, "stretch_amp": 0.05}
SPEAKING_CONFIG = {"pulse_speed": 8, "pulse_amp": 5, "eye_radius": 70, "mouth_radius": 50, "line_thickness": 8}


class EyeAnimationNode(Node):
    """
    Controls a full suite of robot eye animations based on ROS topics.
    Can also be controlled via keyboard for debugging.
    """
    def __init__(self, screen):
        super().__init__('eye_animation_node')
        self.screen = screen
        self.clock = pygame.time.Clock()
        
        # --- Subscribers ---
        self.person_sub = self.create_subscription(Bool, '/person_detected_status', self.person_callback, 10)
        self.state_sub = self.create_subscription(String, '/robot_state', self.state_callback, 10)
        self.emotion_sub = self.create_subscription(String, '/emotion', self.emotion_callback, 10)
        self.control_sub = self.create_subscription(String, '/emotion_recognition_control', self.control_callback, 10)
        
        # --- State Management ---
        self.is_person_present = False
        self.robot_state = "listening"
        self.current_emotion = "neutral"
        self.is_mirroring = False
        self.emotion_start_time = time.time()
        
        # --- Animation Variables ---
        self.is_nodding = False; self.blinking = False
        self.lid_progress = 0; self.emotion_anim_progress = 0
        self.blink_start_time = time.time(); self.blink_interval = random.uniform(3, 6)
        
        self.get_logger().info(f"Eye Animation node configured for {WIDTH}x{HEIGHT} display.")

    # --- ROS Callback Functions ---
    def person_callback(self, msg):
        if msg.data and not self.is_person_present:
            self.set_emotion("greet")
        self.is_person_present = msg.data

    def state_callback(self, msg):
        self.robot_state = msg.data
        if self.robot_state == "speaking":
            self.is_nodding = False
            if not self.is_mirroring:
                self.set_emotion("speaking")
        elif self.robot_state == "listening":
            self.is_nodding = True
            if self.current_emotion == "speaking":
                self.set_emotion("neutral")
        else:
            self.is_nodding = False

    def emotion_callback(self, msg):
        if self.is_mirroring:
            self.set_emotion(msg.data)
            
    def control_callback(self, msg):
        if msg.data == "start_mirroring":
            self.is_mirroring = True
            self.get_logger().info("Animation mode changed to MIRRORING.")
        elif msg.data == "stop_mirroring":
            self.is_mirroring = False
            self.set_emotion("neutral")
            self.get_logger().info("Animation mode changed to NEUTRAL.")
        
    def set_emotion(self, new_emotion):
        if self.current_emotion != new_emotion:
            self.current_emotion = new_emotion
            self.emotion_start_time = time.time()
            self.emotion_anim_progress = 0
            if new_emotion != "neutral":
                self.is_nodding = False

    # --- Drawing Logic ---
    def draw_rounded_eye(self, x, y, width, height, radius, color, offset=(0, 0)):
        pygame.draw.rect(self.screen, color, (x + offset[0], y + offset[1], width, height), border_radius=radius)

    def draw_lids(self, x, y, width, height, blink_progress=0, squint_progress=0):
        if blink_progress > 0:
            lid_height = int(height * blink_progress)
            pygame.draw.rect(self.screen, LID_COLOR, (x, y, width, lid_height), border_radius=EYE_CORNER_RADIUS)
            pygame.draw.rect(self.screen, LID_COLOR, (x, y + height - lid_height, width, lid_height), border_radius=EYE_CORNER_RADIUS)
        if squint_progress > 0:
            squint_height = int(height * squint_progress)
            pygame.draw.rect(self.screen, LID_COLOR, (x, y + height - squint_height, width, squint_height), border_radius=EYE_CORNER_RADIUS)

    def generate_smile_data(self, progress, y_offset=0):
        if progress <= 0: return None
        num_points, max_thickness = 50, 20
        x_vals = np.linspace(-1, 1, num_points)
        y_center = -(x_vals**4 * 0.8 + x_vals**2 * 0.2 - 0.7) * 50 * progress
        thickness = (1 - x_vals**2) * max_thickness * progress
        y_upper, y_lower = y_center - thickness/2, y_center + thickness/2
        smile_width, smile_y_pos = 320, HEIGHT // 2 + 100 + y_offset
        upper_points = [(WIDTH//2 + x*smile_width/2, smile_y_pos + y) for x, y in zip(x_vals, y_upper)]
        lower_points = [(WIDTH//2 + x*smile_width/2, smile_y_pos + y) for x, y in zip(x_vals, y_lower)]
        return upper_points + lower_points[::-1]

    def generate_angry_mouth_points(self, progress, offset=(0, 0)):
        if progress <= 0: return None
        points = [(-1, 0.5), (-0.5, -0.5), (0, 0.5), (0.5, -0.5), (1, 0.5)]
        mouth_width, mouth_height, mouth_y_pos = 150, 25 * progress, HEIGHT // 2 + 80
        return [(WIDTH/2 + p[0]*mouth_width/2 + offset[0], mouth_y_pos + p[1]*mouth_height + offset[1]) for p in points]

    def draw_greet_emotion(self, progress):
        for dx in [-EYE_SPACING, EYE_SPACING]:
            base_x = WIDTH // 2 + dx - EYE_WIDTH // 2
            self.draw_rounded_eye(base_x, EYE_Y_POS, EYE_WIDTH, EYE_HEIGHT, EYE_CORNER_RADIUS, color=GREET_COLOR)
            self.draw_lids(base_x, EYE_Y_POS, EYE_WIDTH, EYE_HEIGHT, squint_progress=progress * 0.4)
        smile_points = self.generate_smile_data(progress)
        if smile_points:
            pygame.draw.polygon(self.screen, GREET_COLOR, smile_points)

    def draw_happy_emotion(self, current_time, start_time, progress):
        cfg = HAPPY_CONFIG
        time_elapsed = current_time - start_time
        bounce = cfg["bounce_amp"] * math.sin(time_elapsed * cfg["bounce_speed"]) * progress
        for dx in [-EYE_SPACING, EYE_SPACING]:
            base_x = WIDTH // 2 + dx - EYE_WIDTH // 2
            self.draw_rounded_eye(base_x, EYE_Y_POS + bounce, EYE_WIDTH, EYE_HEIGHT, EYE_CORNER_RADIUS, color=HAPPY_COLOR)
            self.draw_lids(base_x, EYE_Y_POS + bounce, EYE_WIDTH, EYE_HEIGHT, squint_progress=progress * cfg["squint"])
        smile_points = self.generate_smile_data(progress, y_offset=bounce)
        if smile_points:
            pygame.draw.polygon(self.screen, SMILE_COLOR, smile_points)

    def draw_angry_emotion(self, progress):
        shake = (random.uniform(-3, 3), random.uniform(-3, 3)) if progress > 0.5 else (0, 0)
        for i, dx in enumerate([-EYE_SPACING, EYE_SPACING]):
            eye_x = WIDTH // 2 + dx - EYE_WIDTH // 2
            slant = 60 * progress
            p1 = (eye_x + shake[0], EYE_Y_POS + shake[1] + (slant if i == 1 else 0))
            p2 = (eye_x + shake[0] + EYE_WIDTH, EYE_Y_POS + shake[1] + (slant if i == 0 else 0))
            p3 = (eye_x + shake[0] + EYE_WIDTH, EYE_Y_POS + shake[1] + EYE_HEIGHT)
            p4 = (eye_x + shake[0], EYE_Y_POS + shake[1] + EYE_HEIGHT)
            pygame.draw.polygon(self.screen, ANGRY_COLOR, [p1, p2, p3, p4])
        mouth = self.generate_angry_mouth_points(progress, offset=shake)
        if mouth: pygame.draw.lines(self.screen, ANGRY_COLOR, False, mouth, 12)

    def draw_sad_emotion(self, current_time, start_time, progress):
        cfg = SAD_CONFIG
        gaze_offset = (cfg["gaze_x_amp"] * progress, cfg["gaze_y_amp"] * progress)
        droop_height = (EYE_HEIGHT / cfg["droop_factor"]) * math.sin(math.pi / 2 * progress)
        for dx in [-EYE_SPACING, EYE_SPACING]:
            eye_x = WIDTH // 2 + dx - EYE_WIDTH // 2
            self.draw_rounded_eye(eye_x, EYE_Y_POS, EYE_WIDTH, EYE_HEIGHT, EYE_CORNER_RADIUS, offset=gaze_offset, color=EYE_COLOR)
            lid_rect = pygame.Rect(eye_x + gaze_offset[0], EYE_Y_POS + gaze_offset[1], EYE_WIDTH, droop_height)
            pygame.draw.rect(self.screen, LID_COLOR, lid_rect, border_top_left_radius=EYE_CORNER_RADIUS, border_top_right_radius=EYE_CORNER_RADIUS)
        mouth_float_offset = math.sin(current_time * cfg["mouth_float_speed"]) * cfg["mouth_float_amp"] * progress
        frown_x, frown_y = WIDTH // 2, EYE_Y_POS + EYE_HEIGHT + 90
        frown_rect = pygame.Rect(frown_x - 100//2 + gaze_offset[0], frown_y + mouth_float_offset + gaze_offset[1], 100, 50)
        pygame.draw.arc(self.screen, EYE_COLOR, frown_rect, 0, math.pi, int(10 * progress))

    def draw_fear_emotion(self, current_time, progress):
        cfg = FEAR_CONFIG
        for dx in [-EYE_SPACING, EYE_SPACING]:
            wobble = (cfg["wobble_amp"] * math.sin(current_time * cfg["wobble_speed"] + dx) * progress,
                      cfg["wobble_amp"] * math.cos(current_time * cfg["wobble_speed"] + dx) * progress)
            base_x, base_y = WIDTH // 2 + dx - EYE_WIDTH // 2, EYE_Y_POS
            self.draw_rounded_eye(base_x, base_y, EYE_WIDTH, EYE_HEIGHT, EYE_CORNER_RADIUS, color=FEAR_COLOR, offset=wobble)
            pupil_size = (EYE_WIDTH / 4) * progress * cfg["pupil_scale"] 
            pupil_pos = (base_x + (EYE_WIDTH / 2) + wobble[0], base_y + (EYE_HEIGHT / 2) + wobble[1])
            pygame.draw.circle(self.screen, BG_COLOR, pupil_pos, pupil_size)

    def draw_surprise_emotion(self, progress):
        cfg = SURPRISE_CONFIG
        scale = 1 + (cfg["scale_amp"] - 1) * progress
        new_size = int(EYE_WIDTH * scale)
        for dx in [-EYE_SPACING, EYE_SPACING]:
            eye_x = WIDTH // 2 + dx - new_size // 2
            eye_y = EYE_Y_POS - (new_size - EYE_HEIGHT) // 2
            pygame.draw.ellipse(self.screen, SURPRISE_COLOR, (eye_x, eye_y, new_size, new_size))
        mouth_size = cfg["mouth_size"] * progress
        if mouth_size > 0:
            mouth_pos = (WIDTH // 2 - mouth_size / 2, HEIGHT // 2 + 120 - mouth_size / 2)
            pygame.draw.ellipse(self.screen, SURPRISE_COLOR, (*mouth_pos, mouth_size, mouth_size), width=10)

    def draw_pamper_emotion(self, current_time, start_time, progress):
        cfg = PAMPER_CONFIG
        time_elapsed = current_time - start_time
        for i, dx in enumerate([-EYE_SPACING, EYE_SPACING]):
            eye_x = WIDTH // 2 + dx - EYE_WIDTH // 2
            glow_scale = 1 + cfg["glow_amp"] * math.sin(time_elapsed * cfg["glow_speed"])
            bounce_offset = cfg["bounce_amp"] * math.sin(time_elapsed * cfg["bounce_speed"])
            stretch = 1 + cfg["stretch_amp"] * math.sin(time_elapsed * cfg["stretch_speed"])
            new_width, new_height = int(EYE_WIDTH * glow_scale), int(EYE_HEIGHT * stretch)
            eye_rect = pygame.Rect(eye_x - (new_width - EYE_WIDTH) // 2, EYE_Y_POS + bounce_offset, new_width, new_height)
            glow_color = tuple(min(255, int(c * glow_scale)) for c in EYE_COLOR)
            pygame.draw.ellipse(self.screen, glow_color, eye_rect, 0)
            blush_x = eye_x + (EYE_WIDTH // 2) - 40
            blush_y = EYE_Y_POS + EYE_HEIGHT + 10
            pygame.draw.ellipse(self.screen, PAMPER_COLOR, (blush_x, blush_y, 80, 40))
        mouth_x, mouth_y = WIDTH // 2, EYE_Y_POS + EYE_HEIGHT + 70
        smile_offset = 7 * math.sin(time_elapsed * 4)
        arc_rect = pygame.Rect(mouth_x - 120//2, mouth_y + smile_offset, 120, 60)
        pygame.draw.arc(self.screen, PAMPER_COLOR, arc_rect, math.pi, math.pi * 2, 5)

    def draw_speaking_emotion(self, current_time):
        cfg = SPEAKING_CONFIG
        for dx in [-EYE_SPACING, EYE_SPACING]:
            eye_center = (WIDTH // 2 + dx, EYE_Y_POS + cfg["eye_radius"])
            pygame.draw.circle(self.screen, SPEAKING_COLOR, eye_center, cfg["eye_radius"], cfg["line_thickness"])
        pulse = cfg["pulse_amp"] * math.sin(current_time * cfg["pulse_speed"])
        mouth_radius = cfg["mouth_radius"] + pulse
        mouth_center = (WIDTH // 2, EYE_Y_POS + EYE_HEIGHT + 70)
        pygame.draw.circle(self.screen, SPEAKING_COLOR, mouth_center, mouth_radius, cfg["line_thickness"])


    def draw_neutral_emotion(self):
        y_offset = 20 * math.sin(time.time() * 10) if self.is_nodding else 0
        
        if not self.blinking and time.time() - self.blink_start_time > self.blink_interval:
            self.blinking, self.lid_progress, self.lid_direction, self.blink_start_time = True, 0, 1, time.time()
        
        if self.blinking:
            dt = self.clock.get_time() / 1000.0
            if dt > 0:
                self.lid_progress += self.lid_direction * (dt / BLINK_DURATION)
            if self.lid_progress >= 1: self.lid_direction = -1
            elif self.lid_progress <= 0:
                self.blinking, self.lid_progress, self.blink_interval = False, 0, random.uniform(3, 6)
                
        for dx in [-EYE_SPACING, EYE_SPACING]:
            base_x = WIDTH // 2 + dx - EYE_WIDTH // 2
            self.draw_rounded_eye(base_x, EYE_Y_POS + y_offset, EYE_WIDTH, EYE_HEIGHT, EYE_CORNER_RADIUS, color=EYE_COLOR)
            self.draw_lids(base_x, EYE_Y_POS + y_offset, EYE_WIDTH, EYE_HEIGHT, blink_progress=self.lid_progress)
            
    def update_animations(self):
        now = time.time()
        dt = self.clock.tick(60) / 1000.0
        self.screen.fill(BG_COLOR)

        if self.current_emotion not in ["neutral", "speaking"]:
            self.emotion_anim_progress = min(self.emotion_anim_progress + dt / EMOTION_ANIM_DURATION, 1.0)
        else:
            self.emotion_anim_progress = 1.0
            
        if self.current_emotion == "greet":
            self.draw_greet_emotion(self.emotion_anim_progress)
            if self.emotion_anim_progress >= 1.0 and now - self.emotion_start_time > 2.0:
                self.set_emotion("neutral")
        elif self.current_emotion == "happy":
            self.draw_happy_emotion(now, self.emotion_start_time, self.emotion_anim_progress)
        elif self.current_emotion == "angry":
            self.draw_angry_emotion(self.emotion_anim_progress)
        elif self.current_emotion == "sad":
            self.draw_sad_emotion(now, self.emotion_start_time, self.emotion_anim_progress)
        elif self.current_emotion == "fear":
            self.draw_fear_emotion(now, self.emotion_anim_progress)
        elif self.current_emotion == "surprise":
            self.draw_surprise_emotion(self.emotion_anim_progress)
        elif self.current_emotion == "pamper":
            self.draw_pamper_emotion(now, self.emotion_start_time, self.emotion_anim_progress)
        elif self.current_emotion == "speaking":
            self.draw_speaking_emotion(now)
        else:
            self.draw_neutral_emotion()

        pygame.display.flip()

def main(args=None):
    rclpy.init(args=args)
    screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.NOFRAME) 
    pygame.display.set_caption("ROS 2 Eye Animator")
    
    eye_node = EyeAnimationNode(screen)
    
    running = True
    while running and rclpy.ok():
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                running = False
            if event.type == pygame.KEYDOWN:
                key_map = {
                    'h': "happy", 'a': "angry", 's': "sad",
                    'g': "greet", 'f': "fear", 'w': "surprise",
                    'p': "pamper", 'n': "neutral", 't': "speaking"
                }
                key_name = pygame.key.name(event.key)
                if key_name in key_map:
                    emotion = key_map[key_name]
                    eye_node.get_logger().info(f"Keyboard override: setting emotion to '{emotion}'")
                    if emotion not in ["greet", "neutral", "speaking"]:
                        eye_node.is_mirroring = True
                    if emotion == "speaking":
                        eye_node.state_callback(String(data="speaking"))
                    elif emotion == "neutral":
                         eye_node.state_callback(String(data="listening"))
                    else:
                        eye_node.set_emotion(emotion)
        
        rclpy.spin_once(eye_node, timeout_sec=0.0)
        eye_node.update_animations()

    eye_node.destroy_node()
    rclpy.shutdown()
    pygame.quit()

if __name__ == '__main__':
    main()
