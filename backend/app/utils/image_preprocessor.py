import cv2
import numpy as np


class ImagePreprocessor:
    """
    Utility class providing reusable image preprocessing steps using OpenCV.
    These methods are designed to be chainable to clean up images before OCR.
    """

    @staticmethod
    def load_image(image_path: str) -> np.ndarray:
        """
        Load an image from a file path.

        Args:
            image_path (str): Path to the image file.

        Returns:
            np.ndarray: Loaded OpenCV image.
        """
        image = cv2.imread(image_path)
        if image is None:
            raise FileNotFoundError(f"Could not load image at path: {image_path}")
        return image

    @staticmethod
    def grayscale(image: np.ndarray) -> np.ndarray:
        """
        Convert an image to grayscale.

        Args:
            image (np.ndarray): Color or grayscale image.

        Returns:
            np.ndarray: Grayscale image.
        """
        if len(image.shape) == 2:
            return image  # Already grayscale
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    @staticmethod
    def denoise(image: np.ndarray, strength: float = 10.0) -> np.ndarray:
        """
        Denoise the image using fast non-local means denoising.

        Args:
            image (np.ndarray): Input image.
            strength (float): Strength of the denoising effect.

        Returns:
            np.ndarray: Denoised image.
        """
        if len(image.shape) == 2:
            return cv2.fastNlMeansDenoising(image, None, h=strength, templateWindowSize=7, searchWindowSize=21)
        return cv2.fastNlMeansDenoisingColored(image, None, h=strength, hForColorComponents=strength, templateWindowSize=7, searchWindowSize=21)

    @staticmethod
    def threshold(image: np.ndarray) -> np.ndarray:
        """
        Apply adaptive binarization thresholding to convert image to binary (black and white).

        Args:
            image (np.ndarray): Input image.

        Returns:
            np.ndarray: Binarized image.
        """
        gray = ImagePreprocessor.grayscale(image)
        return cv2.adaptiveThreshold(
            gray,
            maxValue=255,
            adaptiveMethod=cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            thresholdType=cv2.THRESH_BINARY,
            blockSize=11,
            C=2
        )

    @staticmethod
    def deskew(image: np.ndarray) -> np.ndarray:
        """
        Detect skew angle in text alignment and rotate the image to straighten it.

        Args:
            image (np.ndarray): Input image.

        Returns:
            np.ndarray: Deskewed/rotated image.
        """
        gray = ImagePreprocessor.grayscale(image)
        
        # Invert colors (we need white text on black background to find coordinates)
        inverted = cv2.bitwise_not(gray)
        
        # Find all coordinates containing pixels that are not black
        coords = np.column_stack(np.where(inverted > 0))
        if len(coords) == 0:
            return image  # Empty image or completely white, no rotation needed

        # Compute minimum bounding box of all text pixels
        angle = cv2.minAreaRect(coords)[-1]

        # The angle returned is in the range [-90, 0)
        # We normalize the angle to get a correct rotation direction
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle

        # If rotation angle is minimal, skip rotation to avoid quality loss
        if abs(angle) < 0.5:
            return image

        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        rotation_matrix = cv2.getRotationMatrix2D(center, angle, scale=1.0)
        
        # Rotate image filling edges with replicated border pixels
        rotated = cv2.warpAffine(
            image,
            rotation_matrix,
            (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE
        )
        return rotated
