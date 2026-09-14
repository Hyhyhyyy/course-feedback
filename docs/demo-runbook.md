# Demo运行与理解说明

## 先理解当前边界

实际验证分为两部分：合成弹幕与转写导入到报告；合成语音和视频经本地Whisper转写与取帧。指定54分钟课程仍缺取得条件和真实数据，不能称为该课程已经跑通。规则模式用于检查工程功能，其分类准确率没有经过标注评估。

## 最小演示

在仓库根目录执行README中的两条命令。基础报告只依赖Python标准库。首页的“查看已验证的合成数据演示”打开已生成报告，报告支持类别筛选、分钟柱图、问题搜索、词云主题展开、单条弹幕、候选转写片段及教师记录保存。当前问题概述为原文摘录；不同条件不会为了归组而改写或丢弃。

`src/run_demo.py`调用`course_feedback/pipeline.py`读取并校验输入；规则模式调用`rule_analysis()`，模型模式调用`models.classify()`；随后建立候选时间关联、计算统计、核验引用，写出`report.json`和`index.html`。模型或输入失败会写出失败记录和失败页面，避免继续展示旧结果。

## 音视频处理

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements-media.txt
.venv/Scripts/python.exe src/prepare_media.py --media data/course.mp4 --model small --out outputs/course-media
```

媒体输入由PyAV解码获得实际时长；每块默认300秒，额外保留1秒上下文并按句段中点归属。块内时间加回全课偏移，输出`transcript.json`；默认每60秒取一帧，输出`frames.json`。每个分块保存状态和输入校验值，相同配置重跑可复用成功块。边界去重策略仍需真实语音核查，不能仅凭全区间有任务记录证明转写无遗漏。

`--model`可以指定本地faster-whisper模型目录，避免运行时网络下载。CPU默认int8，CUDA默认float16。帧的时间记录为请求取帧位置，尚未校验实际帧PTS。已取帧不表示模型已经理解板书或公式。

## 一条命令执行在线任务

```powershell
.venv/Scripts/python.exe src/oneclick.py --url 'https://www.bilibili.com/video/BV1Y2DGYoEEw/' --access-record data/access-record.md --asr-model small --model-url http://127.0.0.1:8080/v1 --model local-model --out outputs/real-course
```

`access-record.md`记录实际成立的素材取得与处理范围；文件存在仅帮助追溯，不自动证明许可有效。没有相应材料时不要创建虚构许可。该连接器使用yt-dlp返回的弹幕XML快照，不宣称平台全部历史弹幕或全部分片覆盖。请求失败停止，未实现代理轮换或限制绕过。

如果访问需要登录，当前支持调用者主动提供的本地会话文件路径参数`--cookie-file`。程序不会提取浏览器凭证，应用内浏览器登录也不会自动同步到后台。会话文件不能提交GitHub或上传模型服务。自动跳转登录、会话安全保存与状态回调仍待实现，不能把“打开B站”按钮称为登录接入完成。

## 链接输入首页

设置本机环境变量后运行`.venv/Scripts/python.exe src/serve_demo.py`：

```powershell
$env:COURSE_ACCESS_RECORD='本地真实取得与处理记录路径'
$env:COURSE_MODEL_URL='http://127.0.0.1:8080/v1'
$env:COURSE_MODEL_NAME='实际部署的模型名'
$env:COURSE_ASR_MODEL='small'
```

如需会话文件，可设置`COURSE_COOKIE_FILE`；模型密钥仅在本地设置`COURSE_MODEL_API_KEY`。不要把密钥填进链接。首页只向后台提交课程链接，模型设置与会话路径不返回前端；服务仅绑定127.0.0.1并校验启动请求令牌，单次仅运行一个任务。

后台顺序调用`acquire_course.py → prepare_media.py → run_demo.py`，在`job.json`记录各阶段状态。当前模型模式仅将脱敏后的弹幕提交指定服务做标注，课程关联仍是候选检索，尚未进行多模态语义判定。在线任务尚未以目标课程实测。

## 输入与输出

弹幕JSON或CSV使用`playback_ms`和`text`，可选`source_id`；也支持显式`playback_s`。XML按B站`d`元素的`p`属性读取秒数和来源编号。未知单位不得猜测。原始记录编号冲突进入拒收清单，不以同文、同时间直接删除弹幕。

转写JSON接受`segments:[{start,end,text}]`，start/end单位秒；也接受FrameScope外层`transcript`结构。当前导入不校验媒体哈希匹配，应在真实试验中核对课程与分P。规则脱敏只覆盖电话和邮箱，姓名等仍需人工核查。

`run.json`记录实际阶段与耗时；`report.json`是统计、问题与证据的共同来源；`index.html`独立呈现报告。教师记录保存到浏览器本地，也可导出JSON；不同浏览器不会自动同步。截图和转写输出目前与报告分开，视觉解释尚未接入。

## 验证

```bash
python -m unittest discover -s tests -v
```

测试核查重复记录、异常时间、疑问保留、情绪区分、隐私字段、FrameScope格式、引用与计数及链接范围。浏览器交互检查另外验证逐条证据、问题搜索、保存恢复和窄屏布局。测试通过证明相应工程约束成立，不证明教学分析准确率。
