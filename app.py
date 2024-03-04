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
    datetime_str = datetime.datetime.now().strftime("%Y%m%d")

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
        duration = round(float(result.stdout), 1)
        st.info(f"動画の長さ：{duration}秒")
        return duration
    except Exception as e:
        print(f"Error getting video duration: {e}")
        return 0



def calculate_bitrate(target_size_mb, duration, audio_bitrate_kbps=256):
    #1MB = 1024 * 1024 * 8ビット
    target_size_bits = target_size_mb * 1024 * 1024 * 8
    total_audio_bits = audio_bitrate_kbps * 1024 * duration
    
    # ビデオ用に残されたビット数を計算
    available_video_bits = target_size_bits - total_audio_bits
    
    # 必要なビデオビットレートを計算（kbps）
    video_bitrate_kbps = ((available_video_bits / duration) / 1024 ) * 0.94
    st.info(f"変換後ビットレート：{int(video_bitrate_kbps)}kbps")

    return max(int(video_bitrate_kbps), 1)  # ビットレートが非常に小さくならないようにする




def process_video(video_path, output_path, resize:bool, has_no_audio:bool, target_size_mb:int, show_logs:bool):
    duration = get_video_duration(video_path)
    bitrate = calculate_bitrate(target_size_mb, duration)
    
    video_filters = "fps=30," + ("scale=trunc(iw/2):trunc(ih/2)" if resize else "scale=trunc(iw/2)*2:trunc(ih/2)*2")
    
    if not has_no_audio:
        ffmpeg_command = (
            ffmpeg
            .input(video_path)
            .output(output_path, vcodec='libx264', acodec='aac', audio_bitrate='256k', 
                    video_bitrate=f'{bitrate}k', vf=video_filters)
            .overwrite_output()
            .compile()
        )
    else:
        ffmpeg_command = (
            ffmpeg
            .input(video_path)
            .output(output_path, vcodec='libx264',acodec='aac', audio_bitrate='256k', video_bitrate=f'{bitrate}k', vf=video_filters, an=None)
            .overwrite_output()
            .compile()
        )

    # ffmpegコマンドを実行
    try:
        process = subprocess.run(ffmpeg_command, text=True, capture_output=True)
        if process.returncode != 0:
            st.error(f"ffmpeg error: {process.stderr}")

    except Exception as e:
        st.error(f"処理中にエラーが発生しました: {e}")




def process_image(image_path, output_path, resize:bool, target_size_mb:int, show_logs:bool):
    image = cv2.imread(image_path)
    if resize:
        image = cv2.resize(image, None, fx=0.5, fy=0.5)

    temp_dir = tempfile.mkdtemp()
    temp_file_path = os.path.join(temp_dir, os.path.basename(output_path))
    
    quality = 0
    while quality  <= 9:
        cv2.imwrite(temp_file_path, image, [cv2.IMWRITE_PNG_COMPRESSION, quality])

        if quality >= 9:
            comp_rate = os.path.getsize(temp_file_path) / (target_size_mb * 1024 * 1024)
            fx_root = round(np.sqrt(1 / comp_rate), 8)
            fy_root = round(np.sqrt(1 / comp_rate), 8)

            if show_logs:
                st.text(f"png_comp_level: {quality}\nfilesize_comp_rate: {comp_rate}\nscale: {fx_root}, {fy_root}")

            image = cv2.resize(image, None, fx=fx_root, fy=fy_root)
            cv2.imwrite(temp_file_path, image)

            shutil.copy(temp_file_path, output_path)

        if show_logs:
            st.image(image)
            st.text(f"png_comp_level: {quality}\nfilesize: {os.path.getsize(temp_file_path)} byte")

        if os.path.getsize(temp_file_path) < target_size_mb * 1024 * 1024:
            shutil.copy(temp_file_path, output_path)
            break
        quality += 1
    
    




def main():

    st.set_page_config(
        page_title = "Blueberry",
        page_icon = "",
        layout = "centered",
        initial_sidebar_state = "collapsed",
        menu_items = {
            'Get Help': 'https://github.com/omitanc/blueberry',
            'About': "JPEG, PNG, MOV, MP4 などのメディアを指定サイズに圧縮するWebAppです。"
        }
    )

    st.title("Blueberry")
    st.subheader("Discordの25MB制限なんて大っ嫌い！w")
    
    st.write("\n  \n")
    st.write("\n  \n")

    is_devmode = st.sidebar.checkbox("Developer mode")

    
    file = st.file_uploader("ファイルをアップロードしてください", type=['png', 'jpg', 'mov', 'mp4', "quicktime"])
    
    with st.expander("制限ファイルサイズの変更", expanded=False):
        limited_mb = st.radio(label="制限ファイルサイズを指定してください。（デフォルト：25MB）",
                        options=("8MB", "25MB", "50MB", "100MB", "500MB"), index=1, horizontal=True,
                        )
    limited_mb = int(limited_mb.replace("MB", ""))
    st.write("\n  \n")
    st.text("オプション")
    resize = st.checkbox("画素数を1/4にする")
    has_no_audio = st.checkbox("音声を除去する")
    
    st.write("\n  \n")
    st.write("\n  \n")
    
    if file is not None:
        saved_file_path = save_uploaded_file(file)
        comp_rate = round(os.path.getsize(saved_file_path) / (limited_mb * 1024 * 1024), 1)

        if comp_rate < 1:
            st.error("既に制限サイズ以下です。")
            st.stop()

        st.info(f"情報量が1/{comp_rate}に圧縮されます。")

        if comp_rate > 5:
            st.warning("圧縮後の画質が大幅に劣化する可能性があります。")

        if st.button('圧縮開始', use_container_width=True):
            output_filename = generate_output_filename(file.name, ".mp4" if "video" in file.type else ".png")
            output_file_path = os.path.join(tempfile.gettempdir(), output_filename)
            
            
            if saved_file_path:

                with st.spinner("処理中..."):
                    
                    if file.type in ["image/png", "image/jpeg", "image/heic"]:
                        process_image(saved_file_path, output_file_path, resize, limited_mb, is_devmode)
                        st.success("画像処理が完了しました。")

                        if os.path.exists(output_file_path):
                            with open(output_file_path, "rb") as file:
                                st.image(file.read())
                        else:
                            st.error(f"ファイルが見つかりません: {output_file_path}")

                        with open(output_file_path, "rb") as file:
                            btn = st.download_button(
                                    label="ダウンロード",
                                    data=file,
                                    file_name=output_filename,
                                    mime="image/png",
                                    use_container_width=True
                                )
                            
                    elif file.type in ["video/mp4", "video/mov", "video/quicktime"]:
                        process_video(saved_file_path, output_file_path, resize, has_no_audio, limited_mb, is_devmode)
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