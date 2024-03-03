import subprocess
import tempfile
from PIL import Image
import shutil
import datetime
import os

import streamlit as st
import cv2
import numpy as np
import ffmpeg



def generate_output_filename(input_filename, suffix):
    # 入力ファイル名から拡張子を取り除く
    name, ext = os.path.splitext(input_filename)
    # 現在の日時を取得し、文字列としてフォーマットする
    datetime_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    # 新しいファイル名を生成する
    output_filename = f"{name}-COMP_{datetime_str}{suffix}"
    return output_filename



def save_uploaded_file(uploaded_file):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix="." + uploaded_file.name.split('.')[-1]) as tmp_file:
            shutil.copyfileobj(uploaded_file, tmp_file)
            return tmp_file.name
    except Exception as e:
        st.error(f"ファイルの保存中にエラーが発生しました: {e}")
        return None
    


def get_video_duration(video_path):
    try:
        # ffprobeを使って動画の情報を取得
        result = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                                    "format=duration", "-of",
                                    "default=noprint_wrappers=1:nokey=1", video_path],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT)
        # 出力から動画の長さ（秒）を取得
        duration = float(result.stdout)
        return duration
    except Exception as e:
        print(f"Error getting video duration: {e}")
        return 0




def calculate_bitrate(file_size:int, duration:int, audio_bitrate=256):
    # 目標ファイルサイズをビット単位で計算（8MB = 8 * 1024 * 1024 * 8ビット）
    target_file_size_bits = file_size * 1024 * 1024
    # オーディオビットレートをビット単位で計算
    audio_bitrate_bits = audio_bitrate * 1000
    # ビデオビットレートを計算
    video_bitrate = (target_file_size_bits - (audio_bitrate_bits * duration)) / duration
    return max(int(video_bitrate), 0)  # ビットレートが負の値にならないようにする




def process_video(video_path, output_path, resize, target_size_mb=8):
    # 動画の長さを取得
    duration = get_video_duration(video_path)
    # 目標ビットレートを計算
    bitrate = calculate_bitrate(target_size_mb, duration)
    
    # ビデオフィルターの設定
    video_filters = "scale=iw/2:ih/2" if resize else "scale=iw:ih"
    # ffmpegコマンドを組み立て
    ffmpeg_command = (
        ffmpeg
        .input(video_path)
        .output(output_path, vcodec='libx264', acodec='aac', audio_bitrate='256k', 
                video_bitrate=f'{bitrate}k', vf=video_filters, crf=23)
        .overwrite_output()
        .compile()
    )

    # ffmpegコマンドを実行
    try:
        process = subprocess.run(ffmpeg_command, text=True, capture_output=True)
        if process.returncode != 0:
            st.error(f"ffmpeg error: {process.stderr}")
        else:
            st.success("動画処理が完了しました。")
    except Exception as e:
        st.error(f"処理中にエラーが発生しました: {e}")



def resize_and_compress_image(image_path, output_path, resize):
    image = cv2.imread(image_path)
    if resize:
        image = cv2.resize(image, (image.shape[1] // 2, image.shape[0] // 2))
    cv2.imwrite(output_path, image, [int(cv2.IMWRITE_PNG_COMPRESSION), 9])



def main():
    st.title("Blueberry")
    
    file = st.file_uploader("ファイルをアップロードしてください", type=['png', 'jpg', 'mov', 'mp4', "quicktime"])
    resize = st.checkbox("サイズを半分にする")
    
    if file is not None:
        # 圧縮開始ボタンを追加
        if st.button('圧縮開始', use_container_width=True):
            saved_file_path = save_uploaded_file(file)
            if saved_file_path:
                output_filename = generate_output_filename(file.name, ".mp4" if "video" in file.type else ".png")
                # 一時ファイルのディレクトリに出力ファイル名を追加して、完全なパスを生成
                output_file_path = os.path.join(tempfile.gettempdir(), output_filename)

                with st.spinner("処理中..."):
                    if file.type in ["image/png", "image/jpeg", "image/heic"]:
                        resize_and_compress_image(saved_file_path, output_file_path, resize)
                        st.success("画像処理が完了しました。")
                        st.image(output_file_path)
                        # ダウンロードボタンを表示
                        with open(output_file_path, "rb") as file:
                            btn = st.download_button(
                                    label="ダウンロード",
                                    data=file,
                                    file_name=output_filename,
                                    mime="image/png",
                                    use_container_width=True
                                )
                    elif file.type in ["video/mp4", "video/mov", "video/quicktime"]:
                        process_video(saved_file_path, output_file_path, resize)
                        st.success("動画処理が完了しました。")
                        st.video(output_file_path)
                        # ダウンロードボタンを表示
                        with open(output_file_path, "rb") as file:
                            btn = st.download_button(
                                    label="ダウンロード",
                                    data=file,
                                    file_name=output_filename,
                                    mime="video/mp4",
                                    use_container_width=True
                                )
                    else:
                        st.error("サポートされていないファイル形式です。")





if __name__ == "__main__":
    main()
