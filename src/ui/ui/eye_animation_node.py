import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Bool
import pygame
import time
import random
import numpy as np
import math

# --- Pygame Initialization ---
pygame.init()
pygame.font.init() # Ensure font is initialized
info = pygame.display.Info()
WIDTH, HEIGHT = info.current_w, info.current_h
font = pygame.font.SysFont('Arial', 30) # Debug font

# --- Configuration ---
# Colors
EYE_COLOR = (0, 136, 255); HAPPY_COLOR = (0, 136, 255); GREET_COLOR = (0, 255, 0)
LID_COLOR = (0, 0, 0); BG_COLOR = (0, 0, 0); SMILE_COLOR = HAPPY_COLOR
ANGRY_COLOR = (255, 0, 0); PAMPER_COLOR = (255, 100, 100); TEAR_COLOR = (173, 216, 230)
SURPRISE_COLOR = (255, 255, 0); FEAR_COLOR = (180, 150, 255)
TEXT_COLOR = (255, 255, 255)

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

# --- Configuration for Human-like Speaking Mouth ---
SPEAKING_CONFIG = {
    "transition_speed": 5.0,   
    "oscillate_speed": 8.0,    # Slow/Human-like speed
    "max_height": 90,          
    "width": 160,              
    "y_offset": 130            
}

class EyeAnimationNode(Node):
    """
    Controls a full suite of robot eye animations based on ROS topics.
    Integrated with Active Listening and Advanced Mouth Rendering.
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
        self.robot_state = "listening" # Default state
        self.current_emotion = "neutral"
        self.is_mirroring = False
        self.emotion_start_time = time.time()
        
        # --- Animation Variables ---
        self.is_nodding = False
        self.blinking = False
        self.lid_progress = 0; self.emotion_anim_progress = 0
        self.blink_start_time = time.time(); self.blink_interval = random.uniform(3, 6)
        
        # --- Speaking State Variable ---
        self.speak_intensity = 0.0

        self.get_logger().info("Eye Animation node started: Debug Mode Active.")

    # --- ROS Callback Functions ---
    def person_callback(self, msg):
        if msg.data and not self.is_person_present:
            self.set_emotion("greet")
        self.is_person_present = msg.data

    def state_callback(self, msg):
        # FIX: Force lowercase and strip spaces to ensure matching works
        self.robot_state = msg.data.lower().strip()
        # Log state changes to terminal for debugging
        self.get_logger().info(f"State received: '{self.robot_state}'")

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

    def update_behavior_state(self):
        """
        Manages nodding logic based on 'Active Listening'.
        The robot nods when listening to show attention, and stops when speaking.
        """
        # Ensure we match 'listening' regardless of exact string format
        if "listening" in self.robot_state:
            self.is_nodding = True
        else:
            self.is_nodding = False

        # If we are displaying a strong emotion (like angry/fear), override nodding
        if self.current_emotion != "neutral":
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

    # --- Advanced Speaking Mouth Animation ---
    def draw_speaking_mouth(self):
        dt = self.clock.get_time() / 1000.0
        
        # Smoothly transition intensity based on state
        if "speaking" in self.robot_state:
            self.speak_intensity = min(self.speak_intensity + dt * SPEAKING_CONFIG["transition_speed"], 1.0)
        else:
            self.speak_intensity = max(self.speak_intensity - dt * SPEAKING_CONFIG["transition_speed"], 0.0)

        # Only draw if visible
        if self.speak_intensity > 0.01:
            cfg = SPEAKING_CONFIG
            
            # Oscillation (talking speed)
            oscillation = (math.sin(time.time() * cfg["oscillate_speed"]) + 1) / 2
            
            # Current Opening Height (scales with intensity)
            current_open_h = cfg["max_height"] * oscillation * self.speak_intensity
            
            # Shape Calculations
            center_x = WIDTH // 2
            center_y = EYE_Y_POS + EYE_HEIGHT + cfg["y_offset"]
            mouth_w = cfg["width"]
            
            # Human-like movement: Bottom lip moves more than top lip
            top_move = current_open_h * 0.3 
            bottom_move = current_open_h * 0.7
            
            points = []
            
            # Generate Top Lip Curve
            steps = 20
            for i in range(steps + 1):
                t = i / steps # 0.0 to 1.0
                x = center_x - mouth_w/2 + (mouth_w * t)
                curve_factor = 1 - (2*t - 1)**2
                y = center_y - (top_move * curve_factor)
                points.append((x, y))
                
            # Generate Bottom Lip Curve
            for i in range(steps, -1, -1):
                t = i / steps
                x = center_x - mouth_w/2 + (mouth_w * t)
                curve_factor = 1 - (2*t - 1)**2
                y = center_y + (bottom_move * curve_factor)
                points.append((x, y))
            
            pygame.draw.polygon(self.screen, EYE_COLOR, points)

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

    def draw_neutral_emotion(self):
        # 1. Update Behavior
        self.update_behavior_state()
        
        # 2. Nodding Offset (Sine wave if active listening)
        y_offset = 20 * math.sin(time.time() * 10) if self.is_nodding else 0
        
        # 3. Blinking Logic
        if not self.blinking and time.time() - self.blink_start_time > self.blink_interval:
            self.blinking, self.lid_progress, self.lid_direction, self.blink_start_time = True, 0, 1, time.time()
        if self.blinking:
            dt = self.clock.get_time() / 1000.0
            if dt > 0:
                self.lid_progress += self.lid_direction * (dt / BLINK_DURATION)
            if self.lid_progress >= 1: self.lid_direction = -1
            elif self.lid_progress <= 0:
                self.blinking, self.lid_progress, self.blink_interval = False, 0, random.uniform(3, 6)
        
        # 4. Draw Eyes
        for dx in [-EYE_SPACING, EYE_SPACING]:
            base_x = WIDTH // 2 + dx - EYE_WIDTH // 2
            self.draw_rounded_eye(base_x, EYE_Y_POS + y_offset, EYE_WIDTH, EYE_HEIGHT, EYE_CORNER_RADIUS, color=EYE_COLOR)
            self.draw_lids(base_x, EYE_Y_POS + y_offset, EYE_WIDTH, EYE_HEIGHT, blink_progress=self.lid_progress)
            
        # 5. Draw Mouth Overlay
        self.draw_speaking_mouth()

    def update_animations(self):
        """Main drawing loop to select and render the correct emotion."""
        now = time.time()
        dt = self.clock.tick(60) / 1000.0
        
        self.screen.fill(BG_COLOR)

        if self.current_emotion != "neutral":
            self.emotion_anim_progress = min(self.emotion_anim_progress + dt / EMOTION_ANIM_DURATION, 1.0)
        else:
            self.emotion_anim_progress = 0
            
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
        else:
            self.draw_neutral_emotion()

        # --- DEBUG HUD ---
        # This will show you exactly what state the code thinks it is in.
        status_text = f"STATE: {self.robot_state.upper()}"
        nod_text = f"NODDING: {self.is_nodding}"
        
        text_surf_1 = font.render(status_text, True, TEXT_COLOR)
        text_surf_2 = font.render(nod_text, True, TEXT_COLOR)
        
        self.screen.blit(text_surf_1, (20, 20))
        self.screen.blit(text_surf_2, (20, 60))

        pygame.display.flip()

def main(args=None):
    rclpy.init(args=args)
    screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
    pygame.display.set_caption("ROS 2 Eye Animator")
    
    eye_node = EyeAnimationNode(screen)
    
    running = True
    while running and rclpy.ok():
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                running = False
            # Keyboard overrides for debugging
            if event.type == pygame.KEYDOWN:
                key_map = {
                    'h': "happy", 'a': "angry", 's': "sad",
                    'g': "greet", 'f': "fear", 'w': "surprise",
                    'p': "pamper",
                    'n': "neutral"
                }
                key_name = pygame.key.name(event.key)
                if key_name in key_map:
                    emotion = key_map[key_name]
                    eye_node.get_logger().info(f"Keyboard override: setting emotion to '{emotion}'")
                    if emotion not in ["greet", "neutral"]:
                        eye_node.is_mirroring = True
                    eye_node.set_emotion(emotion)
        
        rclpy.spin_once(eye_node, timeout_sec=0.0)
        eye_node.update_animations()

    eye_node.destroy_node()
    rclpy.shutdown()
    pygame.quit()

if __name__ == '__main__':
    main()
