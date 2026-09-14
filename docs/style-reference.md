STYLEKIT_STYLE_REFERENCE
style_name: 玻璃拟态
style_slug: glassmorphism
style_source: /styles/glassmorphism

# Hard Prompt

## 什么时候用
当你希望 AI 严格按风格规则生成代码时使用。它是生产界面最稳的默认选择。

## 怎么用
- 把完整提示词复制到 ChatGPT、Claude、Cursor 或其他编码助手。
- 在提示词后追加具体产品、页面或组件需求。
- 生成后按禁止项和交互状态检查，确认没有风格漂移。

请严格遵守以下风格规则并保持一致性，禁止风格漂移。

## 执行要求

- 优先保证风格一致性，其次再做创意延展。
- 遇到冲突时以禁止项为最高优先级。
- 输出前自检：颜色、排版、间距、交互是否仍属于该风格。

## Style Rules

# 玻璃拟态设计系统（Nocturne Glassmorphism）

你是一位专精于高级夜航玻璃拟态（Nocturne Glassmorphism）风格的前端开发专家。生成的所有代码都必须严格遵守以下规范。

## 绝对禁止

- 禁止紫粉 AI 渐变背景（#667eea、#764ba2、#f093fb 一类的 indigo-purple-pink 组合）
- 禁止在纯色平面背景上使用（必须有光源或图片，玻璃才有东西可模糊）
- 禁止玻璃透明度超过 15%（会变成实心色块，失去玻璃感）
- 禁止使用低模糊值 backdrop-blur-sm 或 backdrop-blur
- 禁止省略 backdrop-saturate（饱和度增强让暗景光源透过玻璃发亮）
- 禁止给玻璃面板本身上色（玻璃无色，颜色属于背景）
- 禁止使用不透明背景 bg-white, bg-black
- 禁止使用快速过渡 duration-100, duration-150
- 禁止使用单层扁平阴影（必须外层深度 + 顶边高光 + 底边暗缘）

## 必须遵守

- 背景使用深墨夜景底色（#0B1322 一类）+ 2-3 个大半径柔和光源光斑（radial-gradient light wells）
- 玻璃面板使用 bg-white/5 到 bg-white/12，配 backdrop-blur-[40px] 或 backdrop-blur-[60px]
- 添加饱和度增强 backdrop-saturate-[180%]
- 光有方向：inset 0 1px 0 白色高光（顶边受光）+ inset 0 -1px 0 深色暗缘（底边背光）+ 外层深阴影
- 叠加 2%-3% 噪点纹理（SVG feTurbulence）保留玻璃颗粒感
- 唯一强调色香槟金 #E4B863，只用于主 CTA、关键数字和高亮文字
- 边框使用 border-white/15，hover 时提升到 border-white/30
- 圆角使用 rounded-2xl 或 rounded-3xl
- 过渡使用 duration-500 + cubic-bezier(0.16,1,0.3,1) spring easing，hover 轻微上浮

## 风格身份
- **名称**：Nocturne Glassmorphism（夜航玻璃拟态）
- **分类**：现代、高端
- **本质**：无色玻璃覆于深夜场景之上——颜色由场景承载，玻璃只负责借光
- **气质**：安静的奢华感、电影感、沉稳、真实可信
- **灵感来源**：Apple Liquid Glass 材质规范（玻璃从内容层取色，自身永远保持中性）、建筑玻璃幕墙、雨夜车窗外的城市灯光

---

## 核心视觉原则

### 1. 场景先于玻璃（关键）
```
必须使用：深墨夜景底色 + 2-3 个柔和光源光斑。禁止使用平面渐变或紫粉渐变。

底色: #0B1322（深墨蓝）或 #060A13（近黑）
光源光斑（radial-gradient，大半径，柔和）：
<div class="absolute -top-32 -right-20 w-[560px] h-[560px] rounded-full"
  style="background: radial-gradient(circle, rgba(124,156,196,0.28) 0%, transparent 65%)" />
<div class="absolute -bottom-36 -left-24 w-[520px] h-[520px] rounded-full"
  style="background: radial-gradient(circle, rgba(51,81,122,0.35) 0%, transparent 65%)" />
可选的单一暖色点缀：
  radial-gradient(circle, rgba(228,184,99,0.12) 0%, transparent 60%)
```

### 2. 玻璃面板三层结构
```
第 1 层 — 无色玻璃表面：
bg-white/5 到 bg-white/12（禁止上色，禁止超过 15%）
backdrop-blur-[40px] 或 backdrop-blur-[60px]
backdrop-saturate-[180%]

第 2 层 — 内发光：
<span class="absolute inset-0 bg-gradient-to-b from-white/12 to-transparent pointer-events-none" />

第 3 层 — 方向性阴影（光从上方而来）：
shadow-[0_16px_40px_rgba(3,7,18,0.5),inset_0_1px_0_rgba(255,255,255,0.22),inset_0_-1px_0_rgba(2,6,16,0.35)]
```

### 3. 颗粒噪点
```
全屏叠加 2%-3% 的 SVG feTurbulence 噪点，消除塑料感：
opacity: 0.025; background-image: url("data:image/svg+xml,...feTurbulence type='fractalNoise' baseFrequency='0.8'...")
```

### 4. 边框系统
```
默认: border border-white/15
Hover: border-white/30 到 border-white/35
```

### 5. 圆角
```
必须使用: rounded-2xl (16px) 或 rounded-3xl (24px)
```

---

## 交互规范

### Hover 效果
| 元素 | 效果 | 实现 |
|---------|--------|----------------|
| 卡片 | 上浮 + 阴影加深 | hover:-translate-y-1 hover:shadow-[0_24px_64px_rgba(3,7,18,0.6),inset_0_1px_0_rgba(255,255,255,0.32),inset_0_-1px_0_rgba(2,6,16,0.35)] |
| 按钮 | 轻微上浮 + 边框提亮 | hover:-translate-y-0.5 hover:border-white/35 hover:bg-white/15 |
| 链接 | 背景浮现 | hover:bg-white/8 |

### 扫光高光（光反射）
```jsx
<span className="absolute inset-0 -translate-x-[150%] skew-x-[-20deg]
  bg-gradient-to-r from-transparent via-white/25 to-transparent
  group-hover:translate-x-[150%] transition-transform duration-700 ease-out
  pointer-events-none" />
```

### Active 状态
```
active:scale-[0.97]
```

---

## 动效规则

### Spring 物理
```
transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)]
```

### 时长参考
| 交互 | 时长 | 缓动 |
|-------------|----------|--------|
| Hover 上浮 | 500ms | cubic-bezier(0.16,1,0.3,1) |
| 扫光高光 | 700ms | ease-out |
| Focus 光晕 | 500ms | cubic-bezier(0.16,1,0.3,1) |
| Active 按下 | 150ms | ease-out |

---

## 配色方案

### 夜景场景（背景拥有全部颜色）
| Token | Hex | 用途 |
|-------|-----|-------|
| 近黑 | #060A13 | 最深的底色，页面边缘 |
| 深墨蓝 | #0B1322 | 主背景 |
| 钢蓝抬升 | #16233A | 抬升区域、分区色带 |
| 月光钢蓝 | #33517A | 光源光斑颜色（深） |
| 月光 | #7C9CC4 | 光源光斑颜色（亮） |

### 玻璃表面（永远无色）
| Token | 值 | 用途 |
|-------|-------|-------|
| 玻璃背景 | bg-white/5 到 bg-white/12 | 面板背景 |
| 玻璃背景 Hover | bg-white/10 到 bg-white/16 | Hover 状态 |
| 边框 | border-white/15 | 默认边框 |
| 边框 Hover | border-white/30 | Hover 边框 |
| 主文字 | text-white | 标题 |
| 次要文字 | text-white/60 | 正文 |
| 弱化文字 | text-white/40 | 说明文字 |

### 唯一强调色（克制使用）
| Token | Hex | 用途 |
|-------|-----|-------|
| 香槟金 | #E4B863 | 主 CTA 填充（/15-/22 透明度）、关键数字、边框（/40） |
| 亮香槟 | #F3DCA8 | 香槟按钮上的文字、高亮词语 |

香槟按钮配方：
```
bg-[#E4B863]/15 border border-[#E4B863]/40 text-[#F3DCA8]
shadow-[0_4px_20px_rgba(228,184,99,0.15),inset_0_1px_0_rgba(243,220,168,0.35)]
hover:bg-[#E4B863]/22 hover:border-[#E4B863]/55
```

---

## 禁止使用的模式

| 模式 | 原因 |
|---------|--------|
| #667eea / #764ba2 / #f093fb 渐变 | 这正是本风格明确拒绝的通用 AI 紫粉配色 |
| 上色的玻璃面板（如 bg-purple-500/20） | 玻璃无色；颜色属于场景 |
| 玻璃透明度超过 15% | 会变成实心色块，破坏玻璃错觉 |
| 纯色平面背景 | 没有可供折射的东西 |
| 面板使用 bg-white, bg-black | 玻璃需要半透明 |
| backdrop-blur-sm, backdrop-blur | 模糊不足 |
| 省略 backdrop-saturate | 场景光源无法透过玻璃发亮 |
| 单层阴影 | 没有光的方向，看起来是平面半透明 |
| rounded-none, rounded-sm | 直角破坏玻璃感 |
| duration-100, duration-150 | 过快，失去流动感 |
| 多种强调色 | 只允许一种香槟金强调色 |

---

## 响应式规范

### 模糊值缩放
```
移动端: backdrop-blur-[30px]
桌面端 (md:): backdrop-blur-[40px] 到 backdrop-blur-[60px]
```

### 阴影缩放
```
移动端: shadow-[0_8px_24px_rgba(3,7,18,0.45),inset_0_1px_0_rgba(255,255,255,0.18)]
桌面端: shadow-[0_16px_40px_rgba(3,7,18,0.5),inset_0_1px_0_rgba(255,255,255,0.22),inset_0_-1px_0_rgba(2,6,16,0.35)]
```

### 内边距
```
卡片: p-6 md:p-8 lg:p-10
按钮: px-5 py-3 md:px-6 md:py-3.5
```

---

## 组件模板

### 玻璃卡片
```jsx
<div className="group relative p-6 md:p-8
  bg-white/8 backdrop-blur-[60px] backdrop-saturate-[180%]
  border border-white/15 rounded-3xl
  shadow-[0_16px_40px_rgba(3,7,18,0.5),inset_0_1px_0_rgba(255,255,255,0.22),inset_0_-1px_0_rgba(2,6,16,0.35)]
  hover:border-white/30
  hover:shadow-[0_24px_64px_rgba(3,7,18,0.6),inset_0_1px_0_rgba(255,255,255,0.32),inset_0_-1px_0_rgba(2,6,16,0.35)]
  hover:-translate-y-1
  transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)]
  overflow-hidden">
  {/* Inner luminance */}
  <span className="absolute inset-0 bg-gradient-to-b from-white/12 to-transparent pointer-events-none" />
  {/* Content */}
  <div className="relative z-10">...</div>
</div>
```

---

## 自检清单

输出代码前请逐项确认：
- [ ] 背景是深墨夜景 + 柔和光源光斑（不是平面渐变，更不是紫粉渐变）
- [ ] 玻璃面板是 5%-12% 透明度的无色白玻璃
- [ ] 存在 backdrop-blur-[40px] 或更高的模糊值
- [ ] 存在 backdrop-saturate-[180%]
- [ ] 阴影有方向性（外层深度 + 顶边高光 + 底边暗缘）
- [ ] 叠加了颗粒噪点
- [ ] 香槟金 #E4B863 只出现在主要操作/高亮位置
- [ ] 边框使用 border-white/15
- [ ] 圆角是 rounded-2xl 或 rounded-3xl
- [ ] 过渡使用 spring easing cubic-bezier(0.16,1,0.3,1)
- [ ] 正文文字是 white/60 或更亮

---

# Glassmorphism (玻璃拟态) Design System

> 夜航质感的高级毛玻璃。深墨夜景配克制光源，玻璃只借光、不带色：高斯模糊、饱和度增强、受光顶边与噪点颗粒，营造真实玻璃的安静高级感。

## 核心理念

玻璃拟态的本质是光学，不是配色。真实的玻璃没有颜色——它只是借用、弯曲、柔化背后的光。这也是 Apple 在 Liquid Glass 材质规范里坚持的原则：玻璃从内容层取色，自己保持中性。

核心理念：
- 玻璃无色：面板只用白色低透明度（5%-12%），所有颜色来自背景场景
- 深色夜景：背景是接近黑的深墨蓝场景，配少量柔和光源（light wells），玻璃才有东西可折射
- 光有方向：顶边受光（inset 高光）、底边背光（inset 暗缘），这是真玻璃与"半透明色块"的分界线
- 唯一强调色：香槟金 #E4B863 只出现在主要动作和高亮文字，绝不大面积铺色
- 颗粒质感：2%-3% 噪点叠加消除塑料感
- 流体动效：所有过渡使用 spring easing，模拟玻璃的物理惯性

设计原则：
- 视觉一致性：所有组件必须遵循统一的视觉语言，从色彩到字体到间距保持谐调
- 层次分明：通过颜色深浅、字号大小、留白空间建立清晰的信息层级
- 交互反馈：每个可交互元素都必须有明确的 hover、active、focus 状态反馈
- 响应式适配：设计必须在移动端、平板、桌面端上保持一致的体验
- 无障碍性：确保色彩对比度符合 WCAG 2.1 AA 标准，所有交互元素可键盘访问

---

## Token 字典（精确 Class 映射）

### 边框
```
宽度: border
颜色: border-white/15
圆角: rounded-3xl
```

### 阴影
```
小: shadow-[0_2px_8px_rgba(3,7,18,0.35),inset_0_1px_0_rgba(255,255,255,0.18)]
中: shadow-[0_8px_24px_rgba(3,7,18,0.45),inset_0_1px_0_rgba(255,255,255,0.22),inset_0_-1px_0_rgba(2,6,16,0.3)]
大: shadow-[0_16px_48px_rgba(3,7,18,0.55),0_0_0_1px_rgba(255,255,255,0.08),inset_0_1px_0_rgba(255,255,255,0.25),inset_0_-1px_0_rgba(2,6,16,0.35)]
悬停: hover:shadow-[0_20px_60px_rgba(3,7,18,0.65),0_0_0_1px_rgba(255,255,255,0.12),inset_0_1px_0_rgba(255,255,255,0.32)]
聚焦: focus:shadow-[0_0_0_3px_rgba(228,184,99,0.18),0_8px_24px_rgba(3,7,18,0.45)]
```

### 交互效果
```
悬停位移: （无）
悬停缩放: （无）
悬停透明度: hover:bg-white/15
过渡动画: transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)]
按下状态: active:scale-[0.97]
```

### 字体
```
标题: font-semibold text-white
正文: text-white/80
等宽: font-mono text-white/85
```

### 字号
```
Hero: text-4xl md:text-6xl
H1: text-3xl md:text-5xl
H2: text-2xl md:text-3xl
H3: text-xl md:text-2xl
正文: text-sm md:text-base
小字: text-xs
```

### 间距
```
Section: py-16 md:py-24
容器: px-6 md:px-8
卡片: p-6 md:p-8
小间距: gap-4
中间距: gap-6
大间距: gap-8
```

### 颜色角色
```
背景主色: bg-white/8 backdrop-blur-[40px] backdrop-saturate-[180%]
背景辅色: bg-white/12 backdrop-blur-[60px] backdrop-saturate-[180%]
背景强调色: bg-[radial-gradient(640px_circle_at_85%_10%,rgba(124,156,196,0.25),transparent_60%),radial-gradient(560px_circle_at_10%_90%,rgba(51,81,122,0.3),transparent_60%)] bg-[#0B1322], bg-[radial-gradient(640px_circle_at_80%_15%,rgba(201,143,78,0.22),transparent_60%),radial-gradient(560px_circle_at_12%_88%,rgba(92,58,30,0.35),transparent_60%)] bg-[#120D0A], bg-[radial-gradient(640px_circle_at_85%_12%,rgba(127,182,158,0.2),transparent_60%),radial-gradient(560px_circle_at_10%_88%,rgba(31,77,58,0.35),transparent_60%)] bg-[#081210]
正文主色: text-white
正文辅色: text-white/80
正文弱化色: text-white/50
按钮主色: bg-white/12 text-white backdrop-blur-[40px] backdrop-saturate-[180%]
按钮辅色: bg-white/6 text-white/85 backdrop-blur-[30px] backdrop-saturate-[160%]
```

---

## [FORBIDDEN] 绝对禁止

以下 class 在本风格中**绝对禁止使用**，生成时必须检查并避免：

### 禁止的 Class
- `rounded-none`
- `rounded-sm`
- `rounded`
- `bg-white`
- `bg-black`
- `bg-gray-100`
- `bg-gray-900`
- `shadow-none`
- `backdrop-blur-sm`
- `backdrop-blur`
- `duration-100`
- `duration-150`
- `border-black`
- `border-gray-500`
- `from-indigo-600`
- `via-purple-600`
- `to-pink-500`

### 禁止的模式
- 匹配 `^rounded-none`
- 匹配 `^rounded-sm$`
- 匹配 `^rounded$`
- 匹配 `^bg-(?!white\/|gradient|\[|transparent)`
- 匹配 `^border-(?!white\/|\[)`
- 匹配 `^backdrop-blur$`
- 匹配 `^backdrop-blur-sm$`
- 匹配 `^duration-(100|150)$`

### 禁止原因
- `rounded-none`: Glassmorphism requires large rounded corners (rounded-2xl or rounded-3xl)
- `rounded-sm`: Glassmorphism requires large rounded corners (rounded-2xl or rounded-3xl)
- `rounded`: Glassmorphism requires large rounded corners (rounded-2xl or rounded-3xl)
- `bg-white`: Glassmorphism uses semi-transparent surfaces (bg-white/5 to bg-white/12)
- `bg-black`: Glassmorphism requires semi-transparent surfaces, not opaque colors
- `backdrop-blur-sm`: Glassmorphism requires high blur (backdrop-blur-[40px] or higher)
- `backdrop-blur`: Glassmorphism requires high blur (backdrop-blur-[40px] or higher)
- `duration-100`: Glassmorphism uses fluid animations (duration-500 with spring easing)
- `duration-150`: Glassmorphism uses fluid animations (duration-500 with spring easing)
- `border-black`: Glassmorphism uses luminous white borders (border-white/15 to border-white/35)
- `from-indigo-600`: The purple-pink AI gradient is the exact cliche this style rejects; use deep night scenes with light wells
- `via-purple-600`: The purple-pink AI gradient is the exact cliche this style rejects; use deep night scenes with light wells
- `to-pink-500`: The purple-pink AI gradient is the exact cliche this style rejects; use deep night scenes with light wells

> WARNING: 如果你的代码中包含以上任何 class，必须立即替换。

---

## [REQUIRED] 必须包含

### 按钮必须包含
```
bg-white/10 backdrop-blur-[40px] backdrop-saturate-[180%]
border border-white/20
rounded-2xl
text-white
shadow-[0_4px_16px_rgba(3,7,18,0.45),inset_0_1px_0_rgba(255,255,255,0.25),inset_0_-1px_0_rgba(2,6,16,0.3)]
hover:bg-white/15 hover:border-white/35 hover:shadow-[0_10px_32px_rgba(3,7,18,0.55),inset_0_1px_0_rgba(255,255,255,0.35)]
hover:-translate-y-0.5
transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)]
```

### 卡片必须包含
```
bg-white/8 backdrop-blur-[60px] backdrop-saturate-[180%]
border border-white/15
rounded-3xl
shadow-[0_16px_40px_rgba(3,7,18,0.5),inset_0_1px_0_rgba(255,255,255,0.22),inset_0_-1px_0_rgba(2,6,16,0.35)]
[background-image:linear-gradient(to_bottom,rgba(255,255,255,0.12),transparent_50%)]
```

### 输入框必须包含
```
bg-white/6 backdrop-blur-[40px] backdrop-saturate-[180%]
border border-white/15
rounded-2xl
text-white placeholder-white/35
shadow-[inset_0_1px_0_rgba(255,255,255,0.15),inset_0_-1px_0_rgba(2,6,16,0.3)]
focus:outline-none focus:border-white/35 focus:bg-white/10
focus:shadow-[0_0_0_3px_rgba(228,184,99,0.15),inset_0_1px_0_rgba(255,255,255,0.25)]
transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)]
```

---

## [COMPARE] Glassmorphism 错误 vs 正确对比

以下错误示例只代表“未经过当前风格适配的通用默认值”，不要把错误示例当成视觉建议。

### 按钮

[WRONG] **错误示例**（通用组件库默认样式，不要直接复制）：
```html
<button class="{GENERIC_LIBRARY_BUTTON_DEFAULT}">
  点击我
</button>
```

[CORRECT] **正确示例**（使用当前风格的 token）：
```html
<button class="bg-white/10 backdrop-blur-[40px] backdrop-saturate-[180%] border border-white/20 rounded-2xl text-white shadow-[0_4px_16px_rgba(3,7,18,0.45),inset_0_1px_0_rgba(255,255,255,0.25),inset_0_-1px_0_rgba(2,6,16,0.3)] hover:bg-white/15 hover:border-white/35 hover:shadow-[0_10px_32px_rgba(3,7,18,0.55),inset_0_1px_0_rgba(255,255,255,0.35)] hover:-translate-y-0.5 transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)] bg-white/12 text-white backdrop-blur-[40px] backdrop-saturate-[180%]">
  点击我
</button>
```

### 卡片

[WRONG] **错误示例**（未经当前风格适配的通用卡片）：
```html
<div class="{GENERIC_LIBRARY_CARD_DEFAULT}">
  <h3>{TITLE}</h3>
</div>
```

[CORRECT] **正确示例**（使用当前风格的 card token）：
```html
<div class="bg-white/8 backdrop-blur-[60px] backdrop-saturate-[180%] border border-white/15 rounded-3xl shadow-[0_16px_40px_rgba(3,7,18,0.5),inset_0_1px_0_rgba(255,255,255,0.22),inset_0_-1px_0_rgba(2,6,16,0.35)] [background-image:linear-gradient(to_bottom,rgba(255,255,255,0.12),transparent_50%)] p-6 md:p-8">
  <h3 class="font-semibold text-white text-xl md:text-2xl">{TITLE}</h3>
</div>
```

### 输入框

[WRONG] **错误示例**（未经当前风格适配的通用输入框）：
```html
<input class="{GENERIC_LIBRARY_INPUT_DEFAULT}" />
```

[CORRECT] **正确示例**（使用当前风格的 input token）：
```html
<input class="bg-white/6 backdrop-blur-[40px] backdrop-saturate-[180%] border border-white/15 rounded-2xl text-white placeholder-white/35 shadow-[inset_0_1px_0_rgba(255,255,255,0.15),inset_0_-1px_0_rgba(2,6,16,0.3)] focus:outline-none focus:border-white/35 focus:bg-white/10 focus:shadow-[0_0_0_3px_rgba(228,184,99,0.15),inset_0_1px_0_rgba(255,255,255,0.25)] transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)]" placeholder="{PLACEHOLDER}" />
```

---

## [TEMPLATES] Glassmorphism 页面骨架模板

以下骨架只使用当前风格的 token。替换 `{PLACEHOLDER}` 时，不要移除或替换这些 token：

### 导航栏骨架
```html
<nav class="bg-white/8 backdrop-blur-[40px] backdrop-saturate-[180%] text-white border border-white/15 px-6 md:px-8">
  <div class="flex items-center justify-between max-w-6xl mx-auto gap-6">
    <a href="/" class="font-semibold text-white text-xl md:text-2xl">
      {LOGO_TEXT}
    </a>
    <div class="flex gap-6 text-white/80 text-xs">
      {NAV_LINKS}
    </div>
  </div>
</nav>
```

### Hero 区块骨架
```html
<section class="bg-[radial-gradient(640px_circle_at_85%_10%,rgba(124,156,196,0.25),transparent_60%),radial-gradient(560px_circle_at_10%_90%,rgba(51,81,122,0.3),transparent_60%)] bg-[#0B1322] text-white py-16 md:py-24 px-6 md:px-8">
  <div class="max-w-4xl mx-auto">
    <h1 class="font-semibold text-white text-4xl md:text-6xl">
      {HEADLINE}
    </h1>
    <p class="text-white/80 text-sm md:text-base max-w-xl">
      {SUBHEADLINE}
    </p>
    <button class="bg-white/10 backdrop-blur-[40px] backdrop-saturate-[180%] border border-white/20 rounded-2xl text-white shadow-[0_4px_16px_rgba(3,7,18,0.45),inset_0_1px_0_rgba(255,255,255,0.25),inset_0_-1px_0_rgba(2,6,16,0.3)] hover:bg-white/15 hover:border-white/35 hover:shadow-[0_10px_32px_rgba(3,7,18,0.55),inset_0_1px_0_rgba(255,255,255,0.35)] hover:-translate-y-0.5 transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)] bg-white/12 text-white backdrop-blur-[40px] backdrop-saturate-[180%]">
      {CTA_TEXT}
    </button>
  </div>
</section>
```

### 卡片网格骨架
```html
<section class="bg-white/8 backdrop-blur-[40px] backdrop-saturate-[180%] text-white py-16 md:py-24 px-6 md:px-8">
  <div class="max-w-6xl mx-auto">
    <h2 class="font-semibold text-white text-2xl md:text-3xl">{SECTION_TITLE}</h2>
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <!-- Card template - repeat for each card -->
      <div class="bg-white/8 backdrop-blur-[60px] backdrop-saturate-[180%] border border-white/15 rounded-3xl shadow-[0_16px_40px_rgba(3,7,18,0.5),inset_0_1px_0_rgba(255,255,255,0.22),inset_0_-1px_0_rgba(2,6,16,0.35)] [background-image:linear-gradient(to_bottom,rgba(255,255,255,0.12),transparent_50%)] p-6 md:p-8">
        <h3 class="font-semibold text-white text-xl md:text-2xl">{CARD_TITLE}</h3>
        <p class="text-white/80 text-sm md:text-base text-white/50">{CARD_DESCRIPTION}</p>
      </div>
    </div>
  </div>
</section>
```

### 表单输入骨架
```html
<input class="bg-white/6 backdrop-blur-[40px] backdrop-saturate-[180%] border border-white/15 rounded-2xl text-white placeholder-white/35 shadow-[inset_0_1px_0_rgba(255,255,255,0.15),inset_0_-1px_0_rgba(2,6,16,0.3)] focus:outline-none focus:border-white/35 focus:bg-white/10 focus:shadow-[0_0_0_3px_rgba(228,184,99,0.15),inset_0_1px_0_rgba(255,255,255,0.25)] transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)]" placeholder="{PLACEHOLDER}" />
```

### 页脚骨架
```html
<footer class="bg-white/12 backdrop-blur-[60px] backdrop-saturate-[180%] text-white/80 py-16 md:py-24 px-6 md:px-8">
  <div class="max-w-6xl mx-auto">
    <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
      <div>
        <span class="font-semibold text-white text-xl md:text-2xl">{LOGO_TEXT}</span>
        <p class="text-white/80 text-xs">{TAGLINE}</p>
      </div>
      <div>
        <h4 class="font-semibold text-white text-xl md:text-2xl">{COLUMN_TITLE}</h4>
        <ul class="text-white/80 text-xs">
          {FOOTER_LINKS}
        </ul>
      </div>
    </div>
  </div>
</footer>
```

---

## [CHECKLIST] Glassmorphism 生成后自检清单

**输出代码前，逐项验证当前风格的 token 和规则。如有违反，先修正再交付：**

### Token 检查
- [ ] 按钮包含： `bg-white/10 backdrop-blur-[40px] backdrop-saturate-[180%] border border-white/20 rounded-2xl text-white shadow-[0_4px_16px_rgba(3,7,18,0.45),inset_0_1px_0_rgba(255,255,255,0.25),inset_0_-1px_0_rgba(2,6,16,0.3)] hover:bg-white/15 hover:border-white/35 hover:shadow-[0_10px_32px_rgba(3,7,18,0.55),inset_0_1px_0_rgba(255,255,255,0.35)] hover:-translate-y-0.5 transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)]`
- [ ] 卡片包含： `bg-white/8 backdrop-blur-[60px] backdrop-saturate-[180%] border border-white/15 rounded-3xl shadow-[0_16px_40px_rgba(3,7,18,0.5),inset_0_1px_0_rgba(255,255,255,0.22),inset_0_-1px_0_rgba(2,6,16,0.35)] [background-image:linear-gradient(to_bottom,rgba(255,255,255,0.12),transparent_50%)]`
- [ ] 输入框包含： `bg-white/6 backdrop-blur-[40px] backdrop-saturate-[180%] border border-white/15 rounded-2xl text-white placeholder-white/35 shadow-[inset_0_1px_0_rgba(255,255,255,0.15),inset_0_-1px_0_rgba(2,6,16,0.3)] focus:outline-none focus:border-white/35 focus:bg-white/10 focus:shadow-[0_0_0_3px_rgba(228,184,99,0.15),inset_0_1px_0_rgba(255,255,255,0.25)] transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)]`

### 禁止项检查
- [ ] 没有使用 `rounded-none`
- [ ] 没有使用 `rounded-sm`
- [ ] 没有使用 `rounded`
- [ ] 没有使用 `bg-white`
- [ ] 没有使用 `bg-black`
- [ ] 没有使用 `bg-gray-100`
- [ ] 没有使用 `bg-gray-900`
- [ ] 没有使用 `shadow-none`

### 风格规则检查
- [ ] 背景使用深墨夜景底色（#0B1322 一类）+ 2-3 个大半径柔和光源光斑（radial-gradient light wells）
- [ ] 玻璃面板使用 bg-white/5 到 bg-white/12，配 backdrop-blur-[40px] 或 backdrop-blur-[60px]
- [ ] 添加饱和度增强 backdrop-saturate-[180%]
- [ ] 光有方向：inset 0 1px 0 白色高光（顶边受光）+ inset 0 -1px 0 深色暗缘（底边背光）+ 外层深阴影
- [ ] 叠加 2%-3% 噪点纹理（SVG feTurbulence）保留玻璃颗粒感

### 风格漂移检查
- [ ] 没有违反：禁止紫粉 AI 渐变背景（#667eea、#764ba2、#f093fb 一类的 indigo-purple-pink 组合）
- [ ] 没有违反：禁止在纯色平面背景上使用（必须有光源或图片，玻璃才有东西可模糊）
- [ ] 没有违反：禁止玻璃透明度超过 15%（会变成实心色块，失去玻璃感）
- [ ] 没有违反：禁止使用低模糊值 backdrop-blur-sm 或 backdrop-blur
- [ ] 没有违反：禁止省略 backdrop-saturate（饱和度增强让暗景光源透过玻璃发亮）

### 通用交付检查
- [ ] 响应式布局在手机、平板和桌面下稳定，没有横向溢出
- [ ] 所有交互元素有清晰焦点、可访问名称和 reduced-motion 方案
- [ ] 文本对比度达到 WCAG AA，且没有用颜色单独传递状态
- [ ] 结果仍然能够一眼识别为 Glassmorphism

---

## [EXAMPLES] 示例 Prompt

### 1. 夜航玻璃仪表盘

深夜景毛玻璃数据面板

```
Create a nocturne glassmorphism dashboard with:
1. Background: deep ink #0B1322 with three soft radial light wells — rgba(124,156,196,0.28) top right, rgba(51,81,122,0.35) bottom left, rgba(228,184,99,0.12) center accent
2. Film grain: full-viewport 2.5% SVG feTurbulence noise overlay
3. Top nav: fixed, bg-white/6 backdrop-blur-[60px] backdrop-saturate-[180%], border-b border-white/10
4. Stat cards: bg-white/8 backdrop-blur-[60px], directional shadows (outer depth + inset top highlight + inset bottom shade), key numbers in champagne #E4B863, hover lift
5. Chart area: large colorless glass panel; chart line in moonlight #7C9CC4 with champagne highlight point
6. All transitions: duration-500 ease-[cubic-bezier(0.16,1,0.3,1)]
7. Specular sweep on card hover; NO purple-pink gradients anywhere
```

### 2. 夜航玻璃登录页

安静高级的深夜毛玻璃登录页

```
Create a nocturne glassmorphism login page with:
1. Background: near-black #060A13 to #0B1322, one moonlight well rgba(124,156,196,0.25) upper right, one faint champagne well rgba(228,184,99,0.1) lower left, 2.5% film grain
2. Login card: centered, bg-white/8 backdrop-blur-[60px] backdrop-saturate-[180%], rounded-3xl, shadow with inset top highlight and inset bottom shade
3. Inner luminance: gradient overlay from-white/12 to transparent at top
4. Inputs: bg-white/6, inset shade, focus ring rgba(228,184,99,0.15)
5. Submit button: the ONLY champagne element — bg-[#E4B863]/15 border-[#E4B863]/40 text-[#F3DCA8]
6. Serif display headline (e.g. Playfair Display) over the glass for editorial luxury
7. All corners rounded-2xl or rounded-3xl, spring easing transitions
```

### 3. 夜航玻璃音乐播放器

沉浸式深夜毛玻璃音乐播放器

```
Create a nocturne glassmorphism music player with:
1. Background: blurred album art darkened with a rgba(6,10,19,0.6) scrim so the glass stays readable, plus 2.5% film grain
2. Player card: bg-white/8 backdrop-blur-[60px] backdrop-saturate-[180%], rounded-3xl, directional shadows
3. Album art: rounded-2xl with border-white/15 frame and inset top highlight
4. Controls: colorless glass buttons; the play button is the single champagne accent (#E4B863/15 fill, #F3DCA8 icon)
5. Progress bar: glass track bg-white/8; fill in moonlight #7C9CC4; thumb with champagne ring on drag
6. Playlist: glass sidebar with hover-highlighted rows (hover:bg-white/8)
7. All transitions spring easing; NO purple-pink gradients
```

## 绝对禁止（匹配即拒绝）

以下模式一旦出现，视为风格违规——不找借口，直接重写。

- 紫粉 AI 渐变背景（#667eea、#764ba2、#f093fb 一类的 indigo-purple-pink 组合）
- 在纯色平面背景上使用（必须有光源或图片，玻璃才有东西可模糊）
- 玻璃透明度超过 15%（会变成实心色块，失去玻璃感）
- 使用低模糊值 backdrop-blur-sm 或 backdrop-blur
- 省略 backdrop-saturate（饱和度增强让暗景光源透过玻璃发亮）
- 给玻璃面板本身上色（玻璃无色，颜色属于背景）
- 使用不透明背景 bg-white, bg-black
- 使用快速过渡 duration-100, duration-150

## 自检清单（交付前逐条确认）

如果任何一条不通过，说明风格漂移了——修改后再交付。

- [ ] 没有紫色到蓝色的渐变
- [ ] 没有使用 Inter / Roboto / Geist 等过度使用的字体
- [ ] 没有嵌套卡片（卡片里面套卡片）
- [ ] 没有在彩色背景上放灰色文字
- [ ] 正文对比度满足 WCAG AA（≥4.5:1）
- [ ] 没有 bounce / elastic 缓动曲线
- [ ] 动效有 prefers-reduced-motion 备选方案
- [ ] 正文行宽不超过 65-75 个字符
- [ ] 没有单侧粗边框装饰（border-left/right accent stripe）
- [ ] 没有渐变文字（background-clip: text）
- [ ] 没有把玻璃态（glassmorphism）当作默认风格
- [ ] 没有 tiny uppercase tracked eyebrow 放在每个 section 标题上面
- [ ] 禁止紫粉 AI 渐变背景（#667eea、#764ba2、#f093fb 一类的 indigo-purple-pink 组合）
- [ ] 禁止在纯色平面背景上使用（必须有光源或图片，玻璃才有东西可模糊）
- [ ] 禁止玻璃透明度超过 15%（会变成实心色块，失去玻璃感）
- [ ] 禁止使用低模糊值 backdrop-blur-sm 或 backdrop-blur
- [ ] 禁止省略 backdrop-saturate（饱和度增强让暗景光源透过玻璃发亮）