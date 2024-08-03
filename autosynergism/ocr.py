# ocr.py
import subprocess

import cv2
import pytesseract
from PIL import Image

from autosynergism.geometry import Geometry


class OCR:
    def __init__(self, geometry: Geometry):
        self.geometry = geometry

    def preprocess_image_for_ocr(self, img_path):
        """Preprocess the image to improve OCR results."""
        image = cv2.imread(img_path, cv2.IMREAD_COLOR)
        gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        adaptive_thresh = cv2.adaptiveThreshold(
            gray_image,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            11,
            2
        )
        contours, _ = cv2.findContours(
            adaptive_thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            roi = gray_image[y:y+h, x:x+w]
            mean_intensity = cv2.mean(roi)[0]

            if mean_intensity < 127:
                gray_image[y:y+h, x:x+w] = cv2.bitwise_not(roi)

        cv2.imwrite('preprocessed_image.png', gray_image)
        return gray_image

    def capture_screen(self, output_file='full_screenshot.png'):
        """Capture the screen using `spectacle` and save it to a file."""
        cmd = ['spectacle', '-b', '-n', '-o', output_file]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error capturing screen with spectacle. Return code: {result.returncode}")
            print("stderr output:", result.stderr)
            return False
        return True

    def crop_image(self, x, y, width, height, input_file='full_screenshot.png', output_file='cropped_screenshot.png'):
        """Crop a part of the screenshot."""
        cmd = ['convert', input_file, '-crop', f'{width}x{height}+{x}+{y}', output_file]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error cropping image. Return code: {result.returncode}")
            print("stderr output:", result.stderr)
            return False
        return True

    def read_text_from_image(self, image_path, custom_config=None):
        """Read text from an image using Tesseract OCR."""
        image = Image.open(image_path)
        if custom_config is not None:
            ocr_result = pytesseract.image_to_string(image, config=custom_config)
        else:
            ocr_result = pytesseract.image_to_string(image)
        return ocr_result

    def text_in_rectangle(self, name, custom_config=None):
        """Extract text from a specified rectangle defined in the geometry."""
        rectangle = self.geometry.get_rectangle(name)
        if not rectangle:
            raise ValueError(f"Rectangle {name} not found in geometry.")
        
        full_screenshot_path = 'full_screenshot.png'
        if self.capture_screen(full_screenshot_path):
            cropped_image_path = 'cropped_screenshot.png'
            if self.crop_image(rectangle.x, rectangle.y, rectangle.width, rectangle.height, full_screenshot_path, cropped_image_path):
                text = self.read_text_from_image(cropped_image_path, custom_config=custom_config)
                return text.strip()
            else:
                raise ValueError("Failed to crop the screenshot.")
        raise ValueError("Failed to capture screenshot.")
