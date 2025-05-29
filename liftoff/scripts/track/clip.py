from moviepy.editor import VideoFileClip, CompositeVideoClip, AudioFileClip, TextClip
from moviepy.video.fx.all import resize

# 路径配置
video_path = "/Users/xinhui_li/Downloads/558 2.MP4"
output_path = "/Users/xinhui_li/Downloads/turtle_shorts_final.mp4"
# background_music_path = "/Users/xinhui_li/Downloads/bgm.mp3"  # 可选

# 加载视频
clip = VideoFileClip(video_path)

# 裁剪为竖屏（中心裁剪为 9:16）
target_height = 1080
target_width = 608
clip_resized = resize(clip, height=target_height)
x_center = clip_resized.w / 2
clip_cropped = clip_resized.crop(x_center=x_center, width=target_width)

# 中英文字幕（使用 pillow 渲染）
subtitle_text = "这是Trump小乌龟最爱的鱼🐟\nThis is Trump the turtle's favorite fish!"
txt_clip = TextClip(subtitle_text, fontsize=50, font='Arial', color='white', method='pillow',
                    size=(target_width - 40, None), align='center')\
            .set_position(("center", target_height - 200))\
            .set_duration(clip.duration)

# 添加背景音乐（如果有）
# bgm = AudioFileClip(background_music_path).volumex(0.2).set_duration(clip.duration)
# clip_cropped = clip_cropped.set_audio(bgm)

# 合成字幕与视频
final = CompositeVideoClip([clip_cropped, txt_clip])
final.write_videofile(output_path, codec="libx264", audio_codec="aac")
