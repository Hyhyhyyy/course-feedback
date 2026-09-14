# FrameScope接入与加强

## 已知与未知

已知来自[项目说明](https://scnmbmhpuw95.feishu.cn/wiki/PUAUw7oM3iewdDkyL3nch1FrnAf)：Vue3/TypeScript前端、FastAPI/LangGraph后端、SQLite、Qwen文本处理、Whisper/Groq转写、时间截图和追问。此为文档核验，未接触代码。2026-09-11已确认当前只有项目链接，源码可以后续提供。不能把以下接口误认为原项目已有端点。

## 复用决策

| 原模块 | 接入方法 | 必须加强 | 验收 |
|---|---|---|---|
| 视频输入/搜索 | 换成SourceAdapter，只接已授权本地媒体或获准连接器 | 原始hash、来源、权限与课程ID | URL与实际文件匹配；无许可不自动拉取 |
| Whisper转写 | 包装TranscriptProvider，可对换Qwen3-ASR | 词句时间、块偏移、原文与校正分开 | 小片段对比音频与文字，边界不漂移 |
| 截图与时间索引 | 包装MediaEvidenceProvider | 原始PTS、帧hash、区域框、原分辨率 | 点击能回到正确原片及板书位置 |
| 视频总结 | 拆成课程结构服务与有据主张服务 | 层级知识点、证据ID、不可确定字段 | 同一课重复处理映射一致；不虚构学生问题 |
| 多视频比较 | 首期暂停作为报告主线 | 后续只对可比课程研究，不做排行 | 不抢占单课程闭环实现 |
| 对话追问 | 只检索当前课程证据后回答 | 权限、引用、相反意见、拒答 | 无依据问题明确无法从材料回答 |
| LangGraph工作流 | 有价值则复用任务状态及恢复 | 可追溯中间结果、幂等、取消/重试 | 故障恢复不重复计数 |
| Vue报告组件 | 以当前五步阅读顺序重组 | 六类、多问、问题云、证据与动作保存 | 所有条数和入口同源，刷新后复核存在 |

所谓“适配器”，就是把原模块的输入输出翻译为本项目统一格式，使报告不依赖原模块内部写法。无需先重写一切，也不因原项目暂缺能力而删需求。

## 新增接口契约

- ingest_media：输入已登记媒体路径及media_id；输出duration_ms、sha256、音轨、时间基准和资源索引。
- transcribe：输入audio_asset_id及语言提示；输出utterance_id、start_ms、end_ms、text_raw、可选词级时间和错误状态。
- extract_frames：输入media_id与候选时间；输出frame_id、source_time_ms、资源路径与hash。
- parse_board：输入frame_id及区域；输出bbox、text_raw、formula_latex_candidate、uncertain、来源框。
- build_structure：输入转录/帧/可选教师提纲；输出父子知识节点、边界、依据ID及确认状态。
- contextualize_feedback：输入弹幕/问题单元和候选片段；输出归属候选及证据，不改变弹幕原文。
- retrieve_evidence：输入课程及问题；输出允许访问的弹幕、转录、画面、声音ID与排序。
- export_report：输入经过校验的report对象；输出HTML/JSON及内部资源清单。

接口命名是本项目设计，源码到手后由实际函数适配，不假装已经存在。所有输出须包含处理状态；失败不能返回一个空列表让下游误当无反馈。

## 音视频加强的具体理由

数学课信息分布在口语、板书和时间中。ASR可能把“无穷小”写错，OCR可能丢上下标，单帧可能拍到推导中间状态。因此保留相邻帧和对应句段，标出冲突；不让语言模型凭常识修成一个“看似正确”的公式覆盖来源。

章节采用内容层级而不是镜头列表。先以幻灯片变化、转录话题转换和教师提示找候选；再合并成概念/例题/步骤。知识节点可跨多个不连续片段；重复讲解回链到同一知识节点，显示发生区间。

对“卡顿/重复”拆成可测的源文件静音、冻结画面、相似讲解，以及不可从源文件推出的播放端网络/回看行为。原声保留；降噪只作派生音轨。否则会把需要核查的声音问题先消除，再声称原视频没问题。

先完成媒体取证，不需要实时全双工能力。MiniCPM或Gemma用于短片段复核的增量需在B3/B4对照中验证，不能用模型会看视频作为教学解释可靠的证明。

## 源码交接后第一轮核查

检查仓库许可、作者复用授权、入口命令、依赖锁定、模型调用方、密钥读取方式、是否把媒体发往Groq等外部处理方、文件留存位置、URL下载逻辑与异常处理。用一份允许处理的短媒体包重现原输出，记录复用模块对应的commit。未有许可的代码不直接拷入发布仓库。

主系统在没有FrameScope源码时仍可按上述契约独立实现。取得源码后只替换通过同一验收的模块。当前状态：接入研究已完成，源码核验和实际接入未完成。

技术来源：[Qwen3-ASR](https://github.com/QwenLM/Qwen3-ASR)、[PaddleOCR-VL-1.6](https://huggingface.co/PaddlePaddle/PaddleOCR-VL-1.6)、[FFmpeg](https://ffmpeg.org/ffmpeg-filters.html)、[PySceneDetect](https://www.scenedetect.com/docs/latest/)。教育适用边界参照E07/E12/E25，效果必须由本项目对照检验。

