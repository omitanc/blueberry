# Blueberry

Discordのアップロード制限8MBに悩まされている子羊たちへ、画像や動画を8MBギリギリにイイカンジに圧縮できるWebUIを作ったぞ。

---


# 環境構築



### 依存関係のインストール

```python
brew install ffmpeg
```

<br>

```python
pip install -r requirements.txt
```

---

# WebUIの起動


```python
streamlit run app.py
```

<br>

# 参考

- [OpenCV Official Docs](https://docs.opencv.org/4.0.1/d4/da8/group__imgcodecs.html#ga292d81be8d76901bff7988d18d2b42ac)
- [FFmpeg Codecs Documentation](https://ffmpeg.org/ffmpeg-codecs.html#libx264_002c-libx264rgb)
- [Python, OpenCVで画像ファイルの読み込み、保存](https://note.nkmk.me/python-opencv-imread-imwrite/)
- [Streamlitのレイアウトとコンテナを見てみよう](https://welovepython.net/streamlit-layout-container/#toc4)

<br>

開発者テスト環境：python 3.11.8, MacOS 12.5
