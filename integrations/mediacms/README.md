# 选型参考 已停止实施

按用户确认，当前主线为自研业务流程加成熟开源组件。本目录仅保留此前隔离试验资料，不属于启动或部署依赖。

# MediaCMS 隔离接入试验

2026-09-15：已取得上游源码并固定提交 d146be7c3c6828075dfc83719c37819f1b6fbef7。当前仅准备部署配置，未完成运行、上传或分析联调。未替换原平台。

上游：https://github.com/mediacms-io/mediacms ，许可证 AGPL-3.0。使用时保留上游声明及对应源代码提供要求。官方源码位于被忽略的 outputs/mediacms-pilot/upstream，不复制入本仓库冒充自研。

运行 integrations/mediacms/start.ps1。端口限定127.0.0.1:8770，独立Compose项目及数据库卷；admin密码在本机 outputs/mediacms-pilot/credentials.json 中，禁止提交。源码提交已固定，镜像暂跟随上游latest，首次拉取后须记录并固定镜像摘要后再做可复现验收。

当前阻塞：Docker Desktop引擎管道不存在，日志报告 sailor-ingest.sock 无法访问或重命名。没有执行恢复出厂设置，也未删除Docker数据。修复引擎后继续部署。

联调次序：
1. 启动并记录镜像摘要，验证数据库迁移、登录和媒体权限。
2. 上传仓库 examples/platform.synthetic.mp4，验证转码及播放原始时间。
3. 为媒体UUID关联课镜弹幕记录，保存 playback_ms、分析选择与撤回状态。普通视频评论不直接当时间同步反馈。
4. 通过受控媒体映射取得原视频和固定快照，交给现有 workbench/course_av 分析。禁止靠公开URL绕过私有课程权限。
5. 测试播放跳转、原文引用、未同意排除、撤回失效与越权拒绝，通过后再评估迁移。

现阶段第2至5步待完成。现有平台仍在8766，尚无MediaCMS桥接成功记录。
