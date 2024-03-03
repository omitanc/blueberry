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




def process_image(image_path, output_path, resize):
    image = cv2.imread(image_path)
    if resize:
        # 解像度を半分にする
        image = cv2.resize(image, (0, 0), fx=0.5, fy=0.5)

    # 一時ファイルを作成する
    #temp_dir = tempfile.mkdtemp()
    #temp_file_path = os.path.join(temp_dir, os.path.basename(output_path))
    
    # 初期品質パラメータ
    quality = 98
    while quality > 0:
        # JPEG形式で画像を一時ファイルに保存
        cv2.imwrite(image_path, image, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
        # 生成された一時ファイルのサイズを確認
        if os.path.getsize(image_path) < 8 * 1024 * 1024:
            # 最終的な出力パスにファイルを移動
            shutil.move(image_path, output_path)
            break  # 目標ファイルサイズに収まったら終了
        quality -= 2  # 品質を下げて再試行






def main():
    st.title("Blueberry")
    
    file = st.file_uploader("ファイルをアップロードしてください", type=['png', 'jpg', 'mov', 'mp4', "quicktime"])
    resize = st.checkbox("サイズを半分にする")
    
    if file is not None:
        # 圧縮開始ボタンを追加
        if st.button('圧縮開始', use_container_width=True):

            #with tempfile.NamedTemporaryFile(delete=False, suffix="." + file.name.split('.')[-1]) as temp_file:
                #temp_file.write(file.getvalue())
                #saved_file_path = temp_file.name
            
            output_filename = generate_output_filename(file.name, ".mp4" if "video" in file.type else ".png")
            output_file_path = os.path.join(tempfile.gettempdir(), output_filename)
            saved_file_path = save_uploaded_file(file)

            
            if saved_file_path:

                with st.spinner("処理中..."):
                    if file.type in ["image/png", "image/jpeg", "image/heic"]:
                        process_image(saved_file_path, output_file_path, resize)
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
