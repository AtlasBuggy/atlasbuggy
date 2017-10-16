import numpy as np
from moviepy.editor import VideoClip

def make_frame(t):
    """ returns an image of the frame at time t """
    # ... create the frame with any library
    return np.zeros((300, 400, 3)) # (Height x Width x 3) Numpy array

animation = VideoClip(make_frame, duration=3) # 3-second clip

# For the export, many options/formats/optimizations are supported
animation.write_videofile("my_animation.mp4", fps=24) # export as video
animation.write_gif("my_animation.gif", fps=24) # export as GIF (slow)