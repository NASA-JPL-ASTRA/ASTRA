# WebRTC VAD vs Silero VAD 详细对比分析

---

## 一、技术原理对比

| 维度 | WebRTC VAD | Silero VAD |
|------|------------|------------|
| **算法类型** | 传统信号处理 | 深度学习（神经网络） |
| **核心模型** | 高斯混合模型 (GMM) | PyTorch 神经网络 |
| **决策方式** | 二元决策（有/无语音） | 连续概率输出（0–1） |
| **特征提取** | 子带能量、频谱、过零率、基频 | 数据驱动，模型自动学习 |
| **频率范围** | 最大 4kHz（8k 重采样） | 支持 8k/16k 原采样率 |
| **处理单元** | 10/20/30ms 固定帧 | 建议 75–250ms chunk，支持 31.25ms |

### WebRTC VAD 细节

- **6 个子带**：80–250Hz, 250–500Hz, 500–1kHz, 1–2kHz, 2–3kHz, 3–4kHz  
- **每带 2 个高斯**，用于语音/噪声建模  
- **4 档灵敏度 (0–3)**：0 最宽松，3 最严格  
- **自适应性**：根据环境更新均值和方差  
- **实现**：纯 C，无外部依赖  

### Silero VAD 细节

- **预训练模型**：支持 6000+ 语言语料  
- **输出**：每 chunk 的 `speech_prob`  
- **阈值可调**：用户设定阈值，高于即判为有语音  
- **格式**：PyTorch JIT 或 ONNX  
- **参数量**：约 260K  

---

## 二、准确率对比（基准数据）

### ROC-AUC（Multi-Domain Validation，17 小时多场景数据）

| 模型 | ROC-AUC |
|------|---------|
| WebRTC VAD | **0.73** |
| Silero v4 | 0.91 |
| Silero v5 | 0.96 |
| Silero v6 | **0.97** |

**结论**：Silero 明显优于 WebRTC，Silero v6 比 WebRTC 高约 **24 个百分点**。

### 分场景 ROC-AUC（Silero 官方 Wiki）

| 数据集 | 场景 | WebRTC | Silero v5 | Silero v6 |
|--------|------|--------|-----------|-----------|
| AliMeeting | 远近场会议 | 0.82 | 0.96 | 0.96 |
| Earnings 21 | 电话 | 0.86 | 0.95 | 0.95 |
| MSDWild | 噪声环境 | **0.62** | **0.79** | **0.79** |
| AISHELL-4 | 会议 | 0.74 | 0.94 | 0.94 |
| VoxConverse | 噪声语音 | **0.65** | 0.94 | 0.94 |
| Libriparty | 噪声语音 | 0.79 | 0.97 | 0.97 |

WebRTC 在 **MSDWild**、**VoxConverse** 等噪声场景明显偏低。

### 噪声数据上的整体准确率

在纯噪声（ESC-50、Private noise）上，以“整段误判为语音”的准确率：

| 模型 | ESC-50 | Private noise |
|------|--------|---------------|
| WebRTC | **0** | **0.15** |
| Silero v5 | 0.61 | 0.44 |
| Silero v6 | **0.65** | **0.53** |

WebRTC 在纯噪声上的误激活率很高，Silero 明显更稳。

### Picovoice 基准（5% 假阳性率）

| VAD | 真阳性率 (TPR) | 漏检率 |
|-----|-----------------|--------|
| WebRTC | **50%** | 约 1/2 语音帧漏检 |
| Silero | 87.7% | 约 1/8 语音帧漏检 |
| Cobra（商业） | 98.9% | 约 1/100 语音帧漏检 |

在相同假阳性率下，Silero 的漏检约为 WebRTC 的 **1/4**。

---

## 三、性能与资源

| 维度 | WebRTC VAD | Silero VAD |
|------|------------|------------|
| **依赖** | 无（纯 C / webrtcvad） | PyTorch 或 ONNX Runtime |
| **模型大小** | 无模型 | ~1MB (ONNX) |
| **推理速度** | 极快 | ~165× 实时（ONNX，单 chunk 31.25ms） |
| **CPU 占用** | 极低 | ~0.43%（Ryzen 9，1 小时音频） |
| **内存** | 极低 | 需加载模型与 PyTorch/ONNX |
| **Raspberry Pi Zero** | 可行 | 几乎不可行（约 43% CPU） |

---

## 四、适用场景

| 场景 | WebRTC 更合适 | Silero 更合适 |
|------|----------------|----------------|
| 安静、近场 | ✓ | ✓ |
| 噪声、远场 | ✗ | ✓ |
| 会议、多人 | ✗ | ✓ |
| 键盘、咳嗽等瞬态噪声 | ✗ | ✓ |
| 音乐、背景人声 | ✗ | ✓ |
| 嵌入式 / 低功耗 | ✓ | ✗ |
| Web 端 | ✓（原生支持） | 需 ONNX/WebAssembly |
| Python 研究/原型 | ✓ | ✓（更推荐） |

---

## 五、优缺点总结

### WebRTC VAD

**优点：**

- 极轻量、无依赖  
- 部署简单、跨平台  
- 久经考验、文档多  
- 更擅长区分“静音 vs 有声”  

**缺点：**

- 噪声下准确率显著下降  
- 易将噪声、音乐误判为语音  
- 难以区分“噪声中的语音”  
- 只有二元输出，无法做细粒度阈值  

### Silero VAD

**优点：**

- 准确率远高于 WebRTC  
- 在噪声、远场、会议场景更稳健  
- 输出概率，阈值可调  
- 持续更新（v3→v6）  
- 开源，MIT 协议  

**缺点：**

- 依赖 PyTorch 或 ONNX  
- 体积和算力要求更高  
- 低端/嵌入式设备压力大  
- 无官方移动 SDK，需自行导出 ONNX  

---

## 六、对 ASTRA 项目的意义

| 考虑 | WebRTC | Silero |
|------|--------|--------|
| 当前问题 | 噪声易触发、键盘/咳嗽误判 | 可显著减少误触发 |
| 部署环境 | 本地 demo，算力充足 | 适合，CPU 足够 |
| 依赖 | 已有 webrtcvad | 需加入 PyTorch（项目已有） |
| 实现成本 | 已完成 | 需重写 VAD 调用逻辑 |
| 预期效果 | 幻觉仍依赖 Whisper 置信度过滤 | 从源头减少无效 Whisper 调用 |

**建议**：若噪声误触发和幻觉仍是主要问题，且运行环境有足够算力，迁移到 Silero VAD 收益较大。WebRTC 更适合作为轻量备选或嵌入式方案。

---

## 七、参考文献

- [Silero VAD GitHub](https://github.com/snakers4/silero-vad)  
- [Silero VAD Quality Metrics (Wiki)](https://github.com/snakers4/silero-vad/wiki/Quality-Metrics)  
- [Picovoice VAD Benchmark](https://picovoice.ai/docs/benchmark/vad/)  
- [Picovoice: Best VAD 2026](https://picovoice.ai/blog/best-voice-activity-detection-vad/)  
- [WebRTC VAD Algorithm (Alibaba Cloud)](https://topic.alibabacloud.com/a/webrtcs-voice-activity-detection-vad-algorithm_8_8_10267733.html)  
