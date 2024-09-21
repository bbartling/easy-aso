import os
import cv2
from PIL import Image

def avi_to_gif_opencv(avi_file, gif_file):
    """Converts an .avi file to a .gif file using OpenCV and Pillow."""
    cap = cv2.VideoCapture(avi_file)
    frames = []
    
    if not cap.isOpened():
        print(f"Error: Unable to open {avi_file}")
        return

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            # Convert the frame from BGR (OpenCV) to RGB (Pillow)
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            # Convert to a Pillow Image and append to frames list
            im = Image.fromarray(frame_rgb)
            frames.append(im)

        # Save the frames as a GIF
        frames[0].save(gif_file, save_all=True, append_images=frames[1:], loop=0, duration=40)
        print(f"Successfully converted {avi_file} to {gif_file}")
    
    except Exception as e:
        print(f"Error converting {avi_file}: {e}")
    
    finally:
        cap.release()

def convert_all_avi_to_gif_opencv(directory):
    """Loops over the directory and converts all .avi files to .gif files using OpenCV and Pillow."""
    for filename in os.listdir(directory):
        if filename.endswith(".avi"):
            avi_file = os.path.join(directory, filename)
            gif_file = os.path.splitext(avi_file)[0] + ".gif"
            avi_to_gif_opencv(avi_file, gif_file)

if __name__ == "__main__":
    # Get the current working directory
    current_directory = os.getcwd()
    print(f"Converting .avi files in the current directory: {current_directory}")
    convert_all_avi_to_gif_opencv(current_directory)
