# 算法与开源组件来源

课镜的课程平台、数据快照、权限控制、弹幕证据链和音视频任务编排由本项目实现。语音转写使用faster-whisper和Whisper开放权重；文本与图像理解通过可替换模型服务完成，当前本地试验使用Qwen3.5-4B。媒体处理使用PyAV、FFmpeg及Pillow。使用现有模型不等于自研基础模型或已完成微调。

- faster-whisper：https://github.com/SYSTRAN/faster-whisper
- Whisper：https://github.com/openai/whisper
- Qwen3.5-4B：https://huggingface.co/Qwen/Qwen3.5-4B
- llama.cpp：https://github.com/ggml-org/llama.cpp
- PyAV：https://github.com/PyAV-Org/PyAV
- FFmpeg：https://ffmpeg.org/
- Pillow：https://python-pillow.org/

权重与运行器实际版本、文件哈希参见现有本地部署说明。直接依赖遵循各自许可证；代码的任务编排、缓存和数据结构独立维护。
