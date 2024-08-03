import json


class Rectangle:
    def __init__(self, name, x, y, width, height):
        self.name = name
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    def scale(self, scale_x, scale_y):
        """Scale the rectangle coordinates, width, and height."""
        scaled_x = self.x * scale_x
        scaled_y = self.y * scale_y
        scaled_width = self.width * scale_x
        scaled_height = self.height * scale_y
        return Rectangle(self.name, scaled_x, scaled_y, scaled_width, scaled_height)

    def center(self):
        """Get the center of the rectangle."""
        center_x = self.x + self.width / 2
        center_y = self.y + self.height / 2
        return center_x, center_y

    def __str__(self):
        return f"Rectangle({self.name}, {self.x}, {self.y}, {self.width}, {self.height})"


class Geometry:
    def __init__(self, config_file='config.json'):
        self.rectangles = {}
        self.scale_x = 1.0
        self.scale_y = 1.0
        self.load_from_file(config_file)

    def load_from_file(self, filename):
        """Load rectangles and scaling factors from a file."""
        try:
            with open(filename, 'r') as file:
                config = json.load(file)
                self.scale_x = config.get('scale_x', 1.0)
                self.scale_y = config.get('scale_y', 1.0)
                rectangles = config.get('rectangles', {})
                for name, props in rectangles.items():
                    self.add_rectangle(name, props['x'], props['y'], props['width'], props['height'])
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error reading configuration file {filename}: {e}")

    def add_rectangle(self, name, x, y, width, height):
        """Add a rectangle and automatically scale it."""
        rect = Rectangle(name, x, y, width, height)
        scaled_rect = rect.scale(self.scale_x, self.scale_y)
        self.rectangles[name] = scaled_rect

    def get_rectangle(self, name):
        """Get a rectangle by name."""
        return self.rectangles.get(name)

    def set_scaling(self, base_rect, new_rect):
        """Set scaling based on the difference between two rectangles."""
        self.scale_x = new_rect.width / base_rect.width
        self.scale_y = new_rect.height / base_rect.height
        self.apply_scaling()

    def apply_scaling(self):
        """Apply the scaling to all rectangles."""
        for key, rect in self.rectangles.items():
            self.rectangles[key] = rect.scale(self.scale_x, self.scale_y)
