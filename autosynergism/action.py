import time

from pynput.keyboard import Controller as KeyboardController
from pynput.keyboard import Key
from pynput.mouse import Button
from pynput.mouse import Controller as MouseController


class Actions:
    def __init__(self, geometry=None):
        self.geometry = geometry
        self.sequences = {}
        self.mouse = MouseController()
        self.keyboard = KeyboardController()

        self.x_scale: float = 1.0
        self.y_scale: float = 1.0

    def add_sequence(self, seq_name, sequence):
        """Add a sequence of actions."""
        self.sequences[seq_name] = sequence

    def get_rectangle_center(self, name):
        """Get the center of a rectangle."""
        if not self.geometry:
            print("Geometry not provided")
            return None
        rect = self.geometry.get_rectangle(name)
        if rect:
            x0 = rect.x + rect.width / 2
            y0 = rect.y + rect.height / 2
            return (self.x_scale * x0, self.y_scale * y0)
        else:
            print(f"Rectangle {name} not found")
            return None

    def perform_click(self, position, button=Button.left, modifiers=[]):
        """Perform a click action at a given position with optional modifiers."""
        for modifier in modifiers:
            self.keyboard.press(modifier)
        self.mouse.position = position
        time.sleep(0.05)  # Small delay between keystrokes for realism
        self.mouse.click(button,1)
        for modifier in modifiers:
            self.keyboard.release(modifier)

    def hover(self, name):
        position = self.get_rectangle_center(name)
        if position is None:
            return
        self.mouse.position = position

        position = self.get_rectangle_center(name)
    def click(self, name, button=Button.left, modifiers=[], times=1):
        """Perform a click action at a given position with optional modifiers."""
        position = self.get_rectangle_center(name)
        if position is None:
            return
        for modifier in modifiers:
            self.keyboard.press(modifier)
        self.mouse.position = position
        for _ in range(times):
            time.sleep(0.05)  # Small delay between keystrokes for realism
            self.mouse.click(button,1)
        for modifier in modifiers:
            self.keyboard.release(modifier)

    def perform_button_press(self, button, modifiers=[]):
        """Perform a button press action with optional modifiers."""
        for modifier in modifiers:
            self.keyboard.press(modifier)
        self.keyboard.press(button)
        self.keyboard.release(button)
        for modifier in modifiers:
            self.keyboard.release(modifier)

    def type_text(self, text):
        """Type out the provided text."""
        for char in str(text):
            self.keyboard.type(char)
            time.sleep(0.05)  # Small delay between keystrokes for realism

    def perform_action(self, action):
        """Perform an individual action."""
        action_type = action.get('type')
        position = action.get('position', None)
        rect_name = action.get('name', None)
        button = action.get('button', Button.left)
        modifiers = action.get('modifiers', [])
        text = action.get('input', None)
        delay = action.get('delay', 0)

        if delay:
            #print(f"Waiting {delay} seconds")
            time.sleep(delay)

        if rect_name and self.geometry:
            position = self.get_rectangle_center(rect_name)
        
        if action_type == 'click' and position:
            self.perform_click(position, button, modifiers)
        elif action_type == 'key_press':
            keyboard_button = getattr(Key, button, button)
            self.perform_button_press(keyboard_button, modifiers)
        elif action_type == 'type_text' and text is not None:
            self.type_text(text)
        else:
            print(f"Unknown action type or missing input/position: {action_type}")

    def perform_sequence(self, seq_name, input=None, delay=0.05):
        """Perform a sequence of actions with optional input for text."""
        if seq_name not in self.sequences:
            print(f"Sequence {seq_name} not found")
            return

        sequence = self.sequences[seq_name]
        for action in sequence:
            if delay:
                time.sleep(delay)
            if 'input_placeholder' in action:
                action['input'] = input
            self.perform_action(action)

