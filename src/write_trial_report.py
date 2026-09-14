"""Refresh the current real-course trial document from verified completed artifacts."""
import json
from pathlib import Path
from course_feedback.pipeline import validate_report
from local_model import cited_items


def main():
    root=Path(__file__).resolve().parents[1]
    project=root.parents[1]
    job=root/'outputs/jobs/d1150d3d51de4597b510077f7628a6ba'
    read=lambda p:json.loads(p.read_text(encoding='utf-8'))
    state=read(job/'analysis/state.json');r=read(job/'analysis/report.json')
    record=read(job/'assets/acquisition.json')
    media=read(job/'analysis/media/media_run.json')
    if state['status']!='completed' or r.get('analysis_status')!='model_preliminary':
        raise ValueError('真实课程尚未完成所选范围的模型流程，不更新为成功报告')
    if record['bvid']!='BV1Y2DGYoEEw':raise ValueError('试验视频身份不符')
    validate_report(r)
    allowed={x['id'] for k in ['comments','segments','frames','chapters'] for x in r.get(k,[])}
    items=[p for k in r['chapters'] for p in k['points']]+r['model_review']['findings']+r['model_review']['alignment']
    cited_items(items,allowed)
    refs=sum(len(x['evidence_ids']) for x in items)
    unknown=sum(c.get('model_unresolved',False) for c in r['comments'])
    uncertain=sum(c.get('uncertain',False) for c in r['comments'])
    members=[q for g in r['groups'] for q in g['question_ids']]
    if len(members)!=len(r['questions']) or set(members)!={q['id'] for q in r['questions']}:raise ValueError('问题列表不完整')
    counts='\n'.join('| '+k+' | '+str(v)+' |' for k,v in r['label_counts'].items())
    graph=(project/'07_实际试验/BV1Y2DGYoEEw_试验逻辑.mmd').read_text(encoding='utf-8')
    text=f'''# 课镜立项前真实素材与100条抽样闭环试验报告

## 试验目的与当前结论

本次以用户指定的[BV1Y2DGYoEEw课程](https://www.bilibili.com/video/BV1Y2DGYoEEw/)第一分P约54分钟课程为素材来源，最终验收限定为前5分钟内抽样100条弹幕的闭环试用。系统已经取得真实课程素材，通过本地语音转写、开源文本与视觉模型推理、结构与引用校验，生成可回查原文的反馈报告。完成的是标注前的小样本工程闭环；没有人工金标准，因此尚不能给出分类准确率、真实问题召回率或教师受益结论。

本次最终运行状态为`{state['status']}`，模型为`{r['model_id']}`，处理代码版本标识为`{r['model_version']}`。模型曾出现结构遗漏，程序拦截后补处理；单条仍未完成分类的记录共{unknown}条，均保留原文与待处理标记。报告不会将这些记录算成已确认无关。

## 研究设计如何落到试验

申报书前期任务要求实现从课程材料到教师复盘的基本流程。因为研究以弹幕线索帮助教师改进，所以先对全部输入建立原文编号，再提取问题、理解自述、情绪和评价等信息。通过语音转写和课堂画面获得附近讲解材料，从而帮助解释反馈所指内容。教师教学大纲提供原定目标与安排；缺少真实大纲时，该部分保持未提供状态，不补造目标。

六类反馈和证据复盘设计沿用[教学反馈判定细则](../03_研究与实验/教学反馈判定细则与报告依据.md)。CoKnowledge用于借鉴弹幕分类、分层浏览和时间联动，EduRABSA用于区分评价对象与表达，EduFeedback-RAG与ALCE用于借鉴原文检索、摘要及引用评价。具体出处和适配限制见[前沿相关研究综述](../03_研究与实验/前沿相关研究综述.md)。这些研究支持设计选择，不能代替本次课程的准确性检验。

## 输入与部署

实际课程标题为“{record['title']}”。接口时长为3241秒，媒体探测时长为3240.78585秒，完整输入保留到课程结束。整课取得7200条带播放位置的弹幕，前5分钟有4943条、262种不同原文。本次按原文去重保留首次位置，再按时间排序等间隔选取100条，仅用于链路验证；这一抽样不保持原始频率分布。其余记录保留在素材中，不参与本次报告。这份快照记录的是取得时可用的弹幕，不表示平台全部历史弹幕或全部观看者。

| 输入或模型产物 | 实际数量 |
|---|---:|
| 纳入的真实弹幕 | {len(r['comments'])}条 |
| 不同弹幕原文 | {len(set(c['text'] for c in r['comments']))}种 |
| 本地转写草稿 | {len(r['segments'])}段 |
| 已提取课堂画面 | {len(r['frames'])}张 |
| 模型讲解主题窗 | {len(r['chapters'])}个 |
| 教师真实教学大纲 | 未提供 |

文本和画面理解使用Qwen3.5-4B的Q4_K_M权重及F16视觉投影文件，运行器为llama.cpp b10951；语音转写使用faster-whisper与Whisper tiny。主机内存33,752,997,888字节，处理器为Intel Core Ultra 9 285H。已识别Intel Arc核显，但并行加载额外核显服务曾造成内存压力，核显对照未完成，当前采用8线程CPU、本机回环地址服务、16384 token上下文上限。权重来源、SHA-256与实际参数见[本地部署说明](../source/course-feedback/docs/local-model-deployment.md)。量化权重与运行组合需要独立评估，不能照搬模型发布指标。

## 各阶段处理与产出

首先校验弹幕时间和格式，保留每条记录的编号、原文、来源行及播放位置。相同原文在第一轮不引入讲解上下文的文本分类中复用结果，再映射回不同时间位置。模型每批处理48种原文，用六类反馈、积极表达和语义不明标记返回对应序号。程序核查序号范围和覆盖，遗漏时缩小批次补处理；显式疑问规则另行补查，保留无问号求助和混合表达中的疑问候选。

随后仅纳入完整落在前五分钟的转写句段，按五分钟窗组织，每窗选取一张已有画面，与该窗转写共同输入视觉语言模型。模型返回主题标题和带转写或画面引用的讲解概述。这是固定时间窗主题复盘，尚未实现或验证自适应知识点分段。原始转写保留，模型概述不覆盖转写中的术语和公式错误。

对每个已识别问题保留原文，仅合并空白差异相同的表达，再生成逐问题概述。模型提出主题词后，程序只接受原问题中实际出现的词，复算词频并链接到相关问题。综合复盘使用按时间窗选取的{len(r['synthesis_comment_ids'])}条代表反馈及讲解主题，输出观察和候选行动；完整问题列表另外展示，不因综合摘要篇幅限制而删除。

最后校验引用属于当前课程，核对计数和问题归组，保存JSON并通过网页或HTML呈现。教师可点击单条弹幕、查看附近转写和画面、定位视频并保存确认或排除记录。导入大纲后可以重跑对应分析；大纲变更会使旧对应失效。本次真实课程未提供大纲，因此真实大纲对应准确性不在实测结论范围内。

```mermaid
{graph}```

[可编辑Mermaid](BV1Y2DGYoEEw_试验逻辑.mmd) · [矢量图](BV1Y2DGYoEEw_试验逻辑.svg) · [图片](BV1Y2DGYoEEw_试验逻辑.png)

## 实际输出与检验结果

| 模型初步分类 | 弹幕条数 |
|---|---:|
{counts}

六类允许重叠，数量不能相加为人数。本次产生{r['question_count']}个问题单元、{len(r['groups'])}个原文问题组及{len(r['wordcloud'])}个主题词；积极表达候选{len(r['positive_comment_ids'])}条，语义不明或模型未完成分类标记{uncertain}条。上述数值描述当前模型输出，不表示经人工确认的真实类别分布。

检验对象为报告引用、输入计数和问题清单。共检查{refs}个引用位置，非法编号为0；时间轴累计弹幕数为{sum(b['count'] for b in r['timeline'])}，与输入一致；问题分组包含{len(members)}个唯一问题编号，与已识别问题列表一致。该结果说明未在汇总过程中丢失已识别问题，不等于真实问题召回率达到100%。

程序测试共39项，覆盖输入校验、数量守恒、引用越界拒绝、模型遗漏处理、重复原文映射、大纲更新失效和原有工作台功能。两条修正后的接口回归用例分别返回问题与求助、教学评价及积极表达，属于开发检查，未用作独立准确率估计。真实240秒附近课堂画面的模型描述与人工查看内容对应，但未检验完整公式识别。另保留合成大纲分支的结构检查材料；未将其用作真实课程效果证据。

首次100条完整运行实测306.394秒；当前前端复验耗时{state['elapsed_s']}秒。该次复用了已有转写和部分模型缓存，且开发过程中进行过提示及校验修正，所以不能用该数值作为冷启动整课速度。随后对综合复盘提示作了修正并单独重算该部分，不将其混入上述首次运行耗时。各次请求输入、输出和耗时保存在本机模型缓存，便于复查。

## 尚未闭合的证据及中期检验

Whisper tiny对高数术语和公式存在明显误识别；一次视觉抽样不能覆盖整段板书，也不能保证纠正转写。第一轮分类不使用逐条讲解上下文，相同原文跨位置的不同含义尚未充分处理；附近片段仍属候选关联。固定窗概述、原文问题合并与代表反馈综合均为基本实现，不能写成已验证的精确知识点识别、条件保护语义聚类或全面课程质量评价。

本次人工浏览发现，“初中物竞可以食用吗”被概述为字面上的“是否可食用”，闲聊“没有告知的义务”进入问题候选，综合摘要也出现将“实名开卷”扩写为“开卷考试经历”等缺乏依据的说法。这些反例说明当前小模型的隐喻理解、教学相关性和摘要忠实性不足。原始输出保留供复核，界面允许排除误判；本次不将模型输出写为经验证的教学结论。

中期以三门课程各约一万条弹幕建立人工参照，分开检验标签多选、隐含问题召回、混合问题拆分、问题概述忠实性、公式条件保留、引用支持充分性和主题关联。通过只读弹幕、加入转写、加入局部画面三组对照，检验音视频是否带来增益，再比较更大开源模型或微调。教师任务实验检验在固定复盘时间内发现的有效线索与建议质量；没有测验或学习过程记录，不推断掌握率、真实情绪轨迹或教学因果效果。

开发中，曾发现分类提示要求与输出结构约束不一致，已统一为类别到输入序号的映射，并重新计算当前样本，旧结果不作为本次实测结论。无图片的合成材料曾被模型描述为画面清晰度不足，且引用了实际存在的转写编号。这一错误说明引用存在性与引用支持充分性是不同检验对象。已调整提示，禁止把模型处理风险写成课堂缺陷；对应原始响应保留在合成测试缓存中。提示修正不能代替后续独立语义评价。

## 文件与复现

源码工作台入口为[source/course-feedback](../source/course-feedback)，运行`start-local-demo.ps1`后打开本机8766页面。选择已有54分钟课程，或在登录后重新获取当前快照，选择离线本地分析、前5分钟与100条抽样，再生成报告。API为页面默认主要方式，未配置时不会自动调用；校园服务与专用训练权重尚待部署及验证，详见[运行方式设计](../source/course-feedback/docs/inference-modes.md)。配置、失败恢复及导出方式见[操作说明](../source/course-feedback/docs/demo-runbook.md)。

本次真实任务编号为`d1150d3d51de4597b510077f7628a6ba`。该任务的`assets`保存素材，`analysis/media`保存转写和画面，`analysis/model-cache`保存模型证据，`analysis/report.json`保存当前报告。已有失败和合成试验作为必要溯源材料保留，不作为当前实测成功证据；当前说明和图直接更新，未另存历史版本。

弹幕文件SHA-256：`{r['analysis_scope']['source_audit']['source_sha256']}`。媒体文件SHA-256：`{media['media_sha256']}`。通过散列可核对复跑是否使用同一份原始材料；重新获取的快照可能变化，应另行记录输入标识。
'''
    (project/'07_实际试验/BV1Y2DGYoEEw_完整课程试验报告.md').write_text(text,encoding='utf-8')
    metrics={'status':state['status'],'comments':len(r['comments']),'question_units':r['question_count'],
             'groups':len(r['groups']),'wordcloud_terms':len(r['wordcloud']),'chapters':len(r['chapters']),
             'citation_positions':refs,'invalid_references':0,'unresolved_comments':unknown,'model_uncertain':uncertain,
             'question_membership_count':len(members),'semantic_accuracy':'not_measured'}
    (job/'analysis/verification.json').write_text(json.dumps(metrics,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(metrics,ensure_ascii=False))


if __name__=='__main__':main()
