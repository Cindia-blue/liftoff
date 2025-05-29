from moviepy.editor import VideoFileClip, CompositeVideoClip, ImageClip
from PIL import Image, ImageDraw, ImageFont
import numpy as np

clip = VideoFileClip("558 2.MP4")  # 替换为你的视频路径
W, H = clip.size
text = "这是川普最喜欢的小鱼之一～"
font = ImageFont.truetype("/path/to/your/ChineseFont.ttf", 60)

img = Image.new("RGBA", (W, 100), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)
w, h = draw.textsize(text, font=font)
draw.text(((W - w) / 2, 20), text, font=font, fill="white")

txt_clip = ImageClip(np.array(img), ismask=False).set_duration(clip.duration)
txt_clip = txt_clip.set_position(("center", "bottom"))

final = CompositeVideoClip([clip, txt_clip])
final.write_videofile("turtle_output.mp4", fps=24)
