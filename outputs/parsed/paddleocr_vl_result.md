## 图片生成 API 火山方舟

<div style="text-align: center;"><img src="imgs/img_in_image_box_838_117_1113_407.jpg" alt="Image" width="23%" /></div>


<div style="text-align: center;"><img src="imgs/img_in_image_box_0_530_1188_1592.jpg" alt="Image" width="99%" /></div>


---

## 法律声明

本《火山方舟》的所有内容，包括但不限于文字、商标、架构、图示、图片、页面布局等，其知识产权（著作权、商标权、专利权、商业秘密等）归属于北京火山引擎科技有限公司及其关联公司（火山引擎），非经火山引擎书面同意，任何个人和组织不得复制、使用、修改、转发或以任何违反本《火山方舟》所承载的目的进行传播。

本《火山方舟》陈述内容仅作为产品的通用性介绍和参考性指引，火山引擎保留按“现状”和“当前可用”的形式提供产品和服务的权利。火山引擎不对本《火山方舟》中所载的产品功能、性质、质量、标准等内容进行明示或默示的保证和承诺，最终以您与火山引擎实际签署的协议为准。

如您发现本《火山方舟》有任何错误或歧义，或发现有对本《火山方舟》、产品本身的侵权行为，请与火山引擎取得联系。

联系方式：service@volcengine.com，400-850-0030（周一至周五10:00-18:00）

---

## 目录

法律声明  
  
目录  
  
1. 图片生成 API

---

### 1. 图片生成 API

POST https://ark.cn-beijing.volces.com/api/v3/images/generations 运行

本文介绍图片生成模型如 Seedream 5.0 lite 的调用 API，包括输入输出参数，取值范围，注意事项等信息，供您使用接口时查阅字段含义。

## 不同模型支持的图片生成能力简介

doubao seedream 5.0 lite==new==、doubao seedream 4.5/4.0

生成组图（组图：基于您输入的内容，生成的一组内容关联的图片；需配置**sequential_image_generation**为auto）

■ 多图生组图，根据您输入的 ** $ \underline{\text{多张参考图片（2-14）}} $** + $ \underline{\text{文本提示词}} $ 生成一组内容关联的图片（输入的参考图数量+最终生成的图片数量≤15张）。

单图生组图，根据您输入的单张参考图片+文本提示词生成一组内容关联的图片（最多生成14张图片）。

☑ 文生组图，根据您输入的  $ \underline{\text{文本提示词}} $ 生成一组内容关联的图片（最多生成15张图片）。

生成单图（配置**sequential_image_generation**为 disabled）

☑ 多图生图，根据您输入的 ** $ \underline{\text{多张参考图片（2-14）}} $** +  $ \underline{\text{文本提示词}} $ 生成单张图片。

单图生图，根据您输入的单张参考图片+文本提示词生成单张图片。

☑ 文生图，根据您输入的  $ \underline{\text{文本提示词}} $ 生成单张图片。

## 鉴权说明

本接口仅支持 API Key 鉴权，请在获取 API Key 页面，获取长效 API Key。

快速入门

体验中心 ☑ 模型列表 ☑ 模型计费 ☑ API Key ☑ 调用教程 ☑ 接口文档 ☑ 常见问题 ☑ 开通模型 ☑

## 请求参数

请求体

您需要调用的模型的 ID（Model ID），开通模型服务 ☑，并查询 Model ID ☑。

您也可通过 Endpoint ID 来调用模型，获得限流、计费类型（前付费/后付费）、运行状态查询、监控、安全等高级能力，可参考获取 Endpoint ID ☐。

---

**prompt** string %%require%%

用于生成图像的提示词，支持中英文。（查看提示词指南：Seedream 4.0-5.0 提示词指南 ☑）建议不超过300个汉字或600个英文单词。字数过多信息容易分散，模型可能因此忽略细节，只关注重点，造成图片缺失部分元素。

image string/array

输入的图片信息，支持 URL 或 Base64 编码。其中，doubao-seedream-5.0-lite/4.5/4.0 支持单图或多图输入（查看多图融合示例 ☐）。

图片URL：请确保图片URL可被访问。

Base64编码：请遵循此格式 data:image/<图片格式>;base64,<Base64编码>。注意 <图片格式> 需小写，如 data:image/png;base64,<base64_image>。

## 说明

· 传入单张图片要求：

图片格式：jpeg、png（doubao-seedream-5.0-lite/4.5/4.0 模型新增支持 webp、bmp、tiff、gif、heic、heif 格式**new**）

宽高比（宽/高）范围：

[1/16, 16] (适用模型：doubao-seedream-5.0-lite/4.5/4.0)

宽高长度（px）>14

大小：不超过30MB

总像素：不超过  $ 6000 \times 6000 = 36000000 $ px（对单张图宽度和高度的像素乘积限制，而不是对宽度或高度的单独值进行限制）

doubao-seedream-5.0-lite/4.5/4.0 最多支持传入 14 张参考图。

**size** string

### doubao-seedream-5.0-lite

指定生成图像的尺寸信息，支持以下两种方式，不可混用。

方式1|指定生成图像的分辨率，并在prompt中用自然语言描述图片宽高比、图片形状或图片用途，最终由模型判断生成图片的大小。

可选值：2K、3K、4K

· 方式 2 | 指定生成图像的宽高像素值：

默认值：2048x2048

总像素取值范围：[2560x1440=3686400，4096x4096=16777216]

宽高比取值范围：[1/16, 16]

说明

---

采用方式2时，需同时满足总像素取值范围和宽高比取值范围。其中，总像素是对单张图宽度和高度的像素乘积限制，而不是对宽度或高度的单独值进行限制。

· 有效示例：3750×1250

总像素值  $ 3750 \times 1250 = 4687500 $，符合 [3686400, 16777216] 的区间要求；宽高比 3750/1250=3，符合 [1/16, 16] 的区间要求，故该示例值有效。

无效示例：1500×1500

总像素值  $ 1500 \times 1500 = 2250000 $，未达到 3686400 的最低要求；宽高 1500/1500=1，虽符合 [1/16, 16] 的区间要求，但因其未同时满足两项限制，故该示例值无效。

推荐的宽高像素值：


<table border=1 style='margin: auto; word-wrap: break-word;'><tr><td style='text-align: center; word-wrap: break-word;'>分辨率</td><td style='text-align: center; word-wrap: break-word;'>宽高比</td><td style='text-align: center; word-wrap: break-word;'>宽高像素值</td></tr><tr><td rowspan="8">2K</td><td style='text-align: center; word-wrap: break-word;'>1:1</td><td style='text-align: center; word-wrap: break-word;'>2048x2048</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>4:3</td><td style='text-align: center; word-wrap: break-word;'>2304x1728</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>3:4</td><td style='text-align: center; word-wrap: break-word;'>1728x2304</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>16:9</td><td style='text-align: center; word-wrap: break-word;'>2848x1600</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>9:16</td><td style='text-align: center; word-wrap: break-word;'>1600x2848</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>3:2</td><td style='text-align: center; word-wrap: break-word;'>2496x1664</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>2:3</td><td style='text-align: center; word-wrap: break-word;'>1664x2496</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>21:9</td><td style='text-align: center; word-wrap: break-word;'>3136x1344</td></tr><tr><td rowspan="8">3K</td><td style='text-align: center; word-wrap: break-word;'>1:1</td><td style='text-align: center; word-wrap: break-word;'>3072x3072</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>4:3</td><td style='text-align: center; word-wrap: break-word;'>3456x2592</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>3:4</td><td style='text-align: center; word-wrap: break-word;'>2592x3456</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>16:9</td><td style='text-align: center; word-wrap: break-word;'>4096x2304</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>9:16</td><td style='text-align: center; word-wrap: break-word;'>2304x4096</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>2:3</td><td style='text-align: center; word-wrap: break-word;'>2496x3744</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>3:2</td><td style='text-align: center; word-wrap: break-word;'>3744x2496</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>21:9</td><td style='text-align: center; word-wrap: break-word;'>4704x2016</td></tr><tr><td rowspan="2">4K</td><td style='text-align: center; word-wrap: break-word;'>1:1</td><td style='text-align: center; word-wrap: break-word;'>4096x4096</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>3:4</td><td style='text-align: center; word-wrap: break-word;'>3520x4704</td></tr></table>

---


<table border=1 style='margin: auto; word-wrap: break-word;'><tr><td style='text-align: center; word-wrap: break-word;'>分辨率</td><td style='text-align: center; word-wrap: break-word;'>宽高比</td><td style='text-align: center; word-wrap: break-word;'>宽高像素值</td></tr><tr><td rowspan="6"></td><td style='text-align: center; word-wrap: break-word;'>4:3</td><td style='text-align: center; word-wrap: break-word;'>4704x3520</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>16:9</td><td style='text-align: center; word-wrap: break-word;'>5504x3040</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>9:16</td><td style='text-align: center; word-wrap: break-word;'>3040x5504</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>2:3</td><td style='text-align: center; word-wrap: break-word;'>3328x4992</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>3:2</td><td style='text-align: center; word-wrap: break-word;'>4992x3328</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>21:9</td><td style='text-align: center; word-wrap: break-word;'>6240x2656</td></tr></table>

### doubao-seedream-4.5

指定生成图像的尺寸信息，支持以下两种方式，不可混用。

方式1|指定生成图像的分辨率，并在prompt中用自然语言描述图片宽高比、图片形状或图片用途，最终由模型判断生成图片的大小。

可选值：2K、4K

· 方式 2 | 指定生成图像的宽高像素值：

默认值：2048x2048

总像素取值范围：[2560x1440=3686400，4096x4096=16777216]

宽高比取值范围：[1/16, 16]

## 说明

采用方式2时，需同时满足总像素取值范围和宽高比取值范围。其中，总像素是对单张图宽度和高度的像素乘积限制，而不是对宽度或高度的单独值进行限制。

· 有效示例：3750×1250

总像素值  $ 3750 \times 1250 = 4687500 $，符合 [3686400, 16777216] 的区间要求；宽高比 3750/1250=3，符合 [1/16, 16] 的区间要求，故该示例值有效。

无效示例：1500×1500

总像素值  $ 1500 \times 1500 = 2250000 $，未达到 3686400 的最低要求；宽高 1500/1500=1，虽符合 [1/16, 16] 的区间要求，但因其未同时满足两项限制，故该示例值无效。

推荐的宽高像素值：


<table border=1 style='margin: auto; word-wrap: break-word;'><tr><td style='text-align: center; word-wrap: break-word;'>分辨率</td><td style='text-align: center; word-wrap: break-word;'>宽高比</td><td style='text-align: center; word-wrap: break-word;'>宽高像素值</td></tr><tr><td rowspan="3">2K</td><td style='text-align: center; word-wrap: break-word;'>1:1</td><td style='text-align: center; word-wrap: break-word;'>2048x2048</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>4:3</td><td style='text-align: center; word-wrap: break-word;'>2304x1728</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>3:4</td><td style='text-align: center; word-wrap: break-word;'>1728x2304</td></tr></table>

---


<table border=1 style='margin: auto; word-wrap: break-word;'><tr><td style='text-align: center; word-wrap: break-word;'>分辨率</td><td style='text-align: center; word-wrap: break-word;'>宽高比</td><td style='text-align: center; word-wrap: break-word;'>宽高像素值</td></tr><tr><td rowspan="5"></td><td style='text-align: center; word-wrap: break-word;'>16:9</td><td style='text-align: center; word-wrap: break-word;'>2848x1600</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>9:16</td><td style='text-align: center; word-wrap: break-word;'>1600x2848</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>3:2</td><td style='text-align: center; word-wrap: break-word;'>2496x1664</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>2:3</td><td style='text-align: center; word-wrap: break-word;'>1664x2496</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>21:9</td><td style='text-align: center; word-wrap: break-word;'>3136x1344</td></tr><tr><td rowspan="8">4K</td><td style='text-align: center; word-wrap: break-word;'>1:1</td><td style='text-align: center; word-wrap: break-word;'>4096x4096</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>3:4</td><td style='text-align: center; word-wrap: break-word;'>3520x4704</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>4:3</td><td style='text-align: center; word-wrap: break-word;'>4704x3520</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>16:9</td><td style='text-align: center; word-wrap: break-word;'>5504x3040</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>9:16</td><td style='text-align: center; word-wrap: break-word;'>3040x5504</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>2:3</td><td style='text-align: center; word-wrap: break-word;'>3328x4992</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>3:2</td><td style='text-align: center; word-wrap: break-word;'>4992x3328</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>21:9</td><td style='text-align: center; word-wrap: break-word;'>6240x2656</td></tr></table>

### doubao-seedream-4.0

指定生成图像的尺寸信息，支持以下两种方式，不可混用。

方式1|指定生成图像的分辨率，并在prompt中用自然语言描述图片宽高比、图片形状或图片用途，最终由模型判断生成图片的大小。

可选值：1K、2K、4K

· 方式 2 | 指定生成图像的宽高像素值：

默认值：2048x2048

总像素取值范围：[1280x720=921600，4096x4096=16777216]

宽高比取值范围：[1/16, 16]

## 说明

采用方式2时，需同时满足总像素取值范围和宽高比取值范围。其中，总像素是对单张图宽度和高度的像素乘积限制，而不是对宽度或高度的单独值进行限制。

· 有效示例：1600×600

总像素值  $ 1600 \times 600 = 960000 $，符合 [921600, 16777216] 的区间要求；宽高比 1600/600=8/3，符合 [1/16, 16] 的区间要求，故该示例值有效。

无效示例：800×800

---

总像素值  $ 800 \times 800 = 640000 $，未达到 921600 的最低要求；宽高 800/800=1，虽符合 [1/16, 16] 的区间要求，但因其未同时满足两项限制，故该示例值无效。

推荐的宽高像素值：


<table border=1 style='margin: auto; word-wrap: break-word;'><tr><td style='text-align: center; word-wrap: break-word;'>分辨率</td><td style='text-align: center; word-wrap: break-word;'>宽高比</td><td style='text-align: center; word-wrap: break-word;'>宽高像素值</td></tr><tr><td rowspan="8">1K</td><td style='text-align: center; word-wrap: break-word;'>1:1</td><td style='text-align: center; word-wrap: break-word;'>1024x1024</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>4:3</td><td style='text-align: center; word-wrap: break-word;'>1152x864</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>3:4</td><td style='text-align: center; word-wrap: break-word;'>864x1152</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>16:9</td><td style='text-align: center; word-wrap: break-word;'>1280x720</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>9:16</td><td style='text-align: center; word-wrap: break-word;'>720x1280</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>3:2</td><td style='text-align: center; word-wrap: break-word;'>1248x832</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>2:3</td><td style='text-align: center; word-wrap: break-word;'>832x1248</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>21:9</td><td style='text-align: center; word-wrap: break-word;'>1512x648</td></tr><tr><td rowspan="8">2K</td><td style='text-align: center; word-wrap: break-word;'>1:1</td><td style='text-align: center; word-wrap: break-word;'>2048x2048</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>4:3</td><td style='text-align: center; word-wrap: break-word;'>2304x1728</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>3:4</td><td style='text-align: center; word-wrap: break-word;'>1728x2304</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>16:9</td><td style='text-align: center; word-wrap: break-word;'>2848x1600</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>9:16</td><td style='text-align: center; word-wrap: break-word;'>1600x2848</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>3:2</td><td style='text-align: center; word-wrap: break-word;'>2496x1664</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>2:3</td><td style='text-align: center; word-wrap: break-word;'>1664x2496</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>21:9</td><td style='text-align: center; word-wrap: break-word;'>3136x1344</td></tr><tr><td rowspan="7">4K</td><td style='text-align: center; word-wrap: break-word;'>1:1</td><td style='text-align: center; word-wrap: break-word;'>4096x4096</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>3:4</td><td style='text-align: center; word-wrap: break-word;'>3520x4704</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>4:3</td><td style='text-align: center; word-wrap: break-word;'>4704x3520</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>16:9</td><td style='text-align: center; word-wrap: break-word;'>5504x3040</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>9:16</td><td style='text-align: center; word-wrap: break-word;'>3040x5504</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>2:3</td><td style='text-align: center; word-wrap: break-word;'>3328x4992</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>3:2</td><td style='text-align: center; word-wrap: break-word;'>4992x3328</td></tr></table>

---


<table border=1 style='margin: auto; word-wrap: break-word;'><tr><td style='text-align: center; word-wrap: break-word;'>分辨率</td><td style='text-align: center; word-wrap: break-word;'>宽高比</td><td style='text-align: center; word-wrap: break-word;'>宽高像素值</td></tr><tr><td style='text-align: center; word-wrap: break-word;'></td><td style='text-align: center; word-wrap: break-word;'>21:9</td><td style='text-align: center; word-wrap: break-word;'>6240x2656</td></tr></table>

doubao-seedream-3.0-t2i

指定生成图像的宽高像素值。

· 默认值：1024×1024

· 单张图片像素取值范围：[512x512，2048x2048]

推荐的宽高像素值：


<table border=1 style='margin: auto; word-wrap: break-word;'><tr><td style='text-align: center; word-wrap: break-word;'>宽高比</td><td style='text-align: center; word-wrap: break-word;'>宽高像素值</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>1:1</td><td style='text-align: center; word-wrap: break-word;'>1024×1024</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>4:3</td><td style='text-align: center; word-wrap: break-word;'>864×1152</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>3:4</td><td style='text-align: center; word-wrap: break-word;'>1152×864</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>16:9</td><td style='text-align: center; word-wrap: break-word;'>1280×720</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>9:16</td><td style='text-align: center; word-wrap: break-word;'>720×1280</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>3:2</td><td style='text-align: center; word-wrap: break-word;'>832×1248</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>2:3</td><td style='text-align: center; word-wrap: break-word;'>1248×832</td></tr><tr><td style='text-align: center; word-wrap: break-word;'>21:9</td><td style='text-align: center; word-wrap: break-word;'>1512×648</td></tr></table>

sequential_image_generation string 默认值 disabled
仅 doubao-seedream-5.0-lite/4.5/4.0 支持该参数 | 查看组图输出示例
控制是否关闭组图功能。

说明

组图：基于您输入的内容，生成的一组内容关联的图片。

auto：自动判断模式，模型会根据用户提供的提示词自主判断是否返回组图以及组图包含的图片数量。

disabled：关闭组图功能，模型只会生成一张图。

---

组图功能的配置。仅当 **sequential_image_generation** 为 auto 时生效。

属性

sequential_image_generation_options.**max_images *** integer 默认值15
指定本次请求，最多可生成的图片数量。

取值范围： $ [1,15] $

## 说明

实际可生成的图片数量，除受到 **max_images ** 影响外，还受到输入的参考图数量影响。输入的参考图数量+最终生成的图片数量≤15张。

tools==new*** array of object

仅 doubao-seedream-5.0-lite 支持该参数

配置模型要调用的工具。

属性

tools.**type ** string 指定使用的工具类型。

web_search：联网搜索功能。

## 说明

开启联网搜索后，模型会根据用户的提示词自主判断是否搜索互联网内容（如商品、天气等），提升生成图片的时效性，但也会增加一定的时延。

实际搜索次数可通过字段 usage.tool_usage.web_search 查询，如果为 0 表示未搜索。

stream Boolean 默认值 false

仅 doubao-seedream-5.0-lite/4.5/4.0 支持该参数 | 查看流式输出示例

控制是否开启流式输出模式。

false：非流式输出模式，等待所有图片全部生成结束后再一次性返回所有信息。

true：流式输出模式，即时返回每张图片输出的结果。在生成单图和组图的场景下，流式输出模式均生效。

---

**guidance_scale** Float
doubao-seedream-5.0-lite/4.5/4.0 不支持

模型输出结果与prompt的一致程度，生成图像的自由度，又称为文本权重；值越大，模型自由度越小，与用户输入的提示词相关性越强。

取值范围：[1，10]。

output_format==new== string 默认值 jpeg

仅 doubao-seedream-5.0-lite 支持该参数

png
jpeg

指定生成图像的文件格式。可选值：

说明
doubao-seedream-4.5/4.0 模型生成图像的文件格式默认为 jpeg，不支持自定义设置。

response_format string 默认值 url
指定生成图像的返回格式。支持以下两种返回方式：

url：返回图片下载链接；链接在图片生成后24小时内有效，请及时下载图片。

b64_json：以 Base64 编码字符串的 JSON 格式返回图像数据。

watermark Boolean 默认值 true 是否在生成的图片中添加水印。

false: 不添加水印。

true：在图片右下角添加“AI生成”字样的水印标识。

**optimize_prompt_options** object

仅 doubao-seedream-5.0-lite/4.5/4.0 支持该参数

提示词优化功能的配置。

属性

optimize_prompt_options.**mode ** string 默认值 standard 设置提示词优化功能使用的模式。

standard：标准模式，生成内容的质量更高，耗时较长。

fast：快速模式，生成内容的耗时更短，质量一般；doubao-seedream-5.0-lite/4.5 当前不支持。

---

## 响应参数

## 流式响应参数

请参见文档。

## 非流式响应参数

model string
本次请求使用的模型 ID（模型名称-版本）。

created integer
本次请求创建时间的 Unix 时间戳（秒）。

data array

输出图像的信息。

说明

doubao-seedream-5.0-lite/4.5/4.0 模型生成组图场景下，组图生成过程中某张图生成失败时：

· 若失败原因为审核不通过：仍会继续请求下一个图片生成任务，即不影响同请求内其他图片的生成流程。

· 若失败原因为内部服务异常（500）：不会继续请求下一个图片生成任务。

可能类型

图片信息 object

生成成功的图片信息。

属性

data.**url ** string

图片的 url 信息，当 **response_format** 指定为 url 时返回。该链接将在生成后 24 小时内失效，请务必及时保存图像。

推荐配置火山引擎 TOS 提供的数据订阅功能，将您的模型推理产物自动转存到自己的 TOS 桶中，便于长期备份或二次加工。详细介绍请参见 TOS 数据订阅 ☑。

data.b64_json string
图片的 base64 信息，当 **response_format **指定为 b64_json 时返回。

---

data.size string

仅 doubao-seedream-5.0-lite/4.5/4.0 支持该字段。

图像的宽高像素值，格式 <宽像素>x<高像素>，如 2048×2048。

错误信息 object

某张图片生成失败，错误信息。

属性

data.error object 错误信息结构体。

属性

data.error.code

某张图片生成错误的错误码，请参见错误码。

data.error.message

某张图片生成错误的提示信息。

tools array of object

本次请求，配置的模型调用工具

属性

tools.**type ** string 配置的调用工具类型。

web\_search：联网搜索工具。

usage object

本次请求的用量信息。

属性

usage.**generated_images **integer

模型成功生成的图片张数，不包含生成失败的图片。仅对成功生成图片按张数进行计费。

---

usage.output_tokens integer

模型生成的图片花费的 token 数量。

计算逻辑为：计算 sum(图片长*图片宽)/256 ，然后取整。

usage.total_tokens integer

本次请求消耗的总 token 数量。

当前不计算输入 token，故与 output_tokens 值一致。

usage.**tool_usage ** object

使用工具的用量信息。

属性

usage.tool_usage.**web_search ** integer 调用联网搜索工具次数，仅开启联网搜索时返回。

error object

本次请求，如发生错误，对应的错误信息。

属性

error.code string 请参见错误码。

error.message string 错误提示信息