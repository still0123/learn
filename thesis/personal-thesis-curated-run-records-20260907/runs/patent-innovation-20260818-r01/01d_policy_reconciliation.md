# I1-R2 日期政策纠偏报告

- 生成时间：`2026-08-18T01:06:14+08:00`
- 阶段边界：仅做元数据召回与日期政策协调；未读取论文全文，未形成候选构思，未修改正式申请稿。
- 新政策：2026 正式会议/期刊论文允许最早预印本为 2025；仅预印本记录必须在 2026 首次公开。
- 专利时间口径：`prior_art_date = earliest_public_date`，不以正式发表年份替代最早公开日。

## 结果

| 指标 | 数量 |
|---|---:|
| 旧 `01c` 逐条保留 | 778 |
| 已识别误杀族恢复 | 38 |
| 跨源补查新增同类族 | 32 |
| 新池总数 | **848** |
| `research_pool_eligible=true` | 848 |
| `formal_venue_year=2026` | 499 |
| 仅预印本且 2026 首次公开 | 349 |
| 政策状态仍不确定 | **1** |

- 数量门槛：`848 >= 800 + 38 = 838`。
- 相对当前 `01c` 净增：`70` 条，其中恢复指定 38 条，另补查 32 条。
- 当前 `01c` 实际为 778 条；本轮没有删除、覆盖或改写任何 `01c` 文件。

## 修复内容

1. 删除旧逻辑中的错误推论：“文献族最早公开日早于 2026 ⇒ 不具备 2026 研究池资格”。
2. 将研究池资格与专利时间拆分：`formal_venue_year`/仅预印本首发年决定研究池资格，`earliest_public_date` 决定 `prior_art_date`。
3. 对 70 个纠偏族核对 arXiv 初次提交日期；用 OpenAlex 正式版本、Crossref 类型/日期、DBLP 2026 卷期或会议/论文集元数据确认正式载体。
4. 旧 778 条原字段和值保持不变，仅追加日期政策字段与证据链。

## 字段合同

- 每条记录均含：`research_pool_eligible`、`formal_venue_year`、`earliest_public_date`、`prior_art_date`、`date_evidence`。
- 每条记录均保持：`metadata_only=true`、`full_text_verified=false`。
- `date_evidence` 只记录元数据来源，不构成正文核验或论文技术内容确认。

## 不确定项

- `Towards Effective Long Video Understanding of Multimodal Large Language Models via One-shot Clip Retrieval`：已核到 arXiv `2512.08410` 于 2025 首次公开，OpenAlex/Crossref 当前仅给出 2026 SSRN `posted-content/repository` 元数据，未核到正式会议或期刊页。按“恢复已识别 38 项”要求暂留并标记 `eligible_provisional_formal_venue_unverified`；不得据此声称已正式发表。
- 另有 598 条继承自 `01c` 的记录日期置信度低于 `high`，属于旧池的一般元数据不完备，不计入上述 1 条“本次政策决定仍不确定”。

## 指定38项

| 标题 | 最早公开日 | 2026正式载体元数据 | 状态 |
|---|---|---|---|
| A Survey of Multimodal Hallucination Evaluation and Detection | `2025-07-25` | International Journal of Computer Vision | `eligible_confirmed_2025_preprint_2026_formal` |
| AccKV: Towards Efficient Audio-Video LLMs Inference via Adaptive-Focusing and Cross-Calibration KV Cache Optimization | `2025-11-14` | Proceedings of the AAAI Conference on Artificial Intelligence | `eligible_confirmed_2025_preprint_2026_formal` |
| Admitting Ignorance Helps the Video Question Answering Models to Answer | `2025-01-15` | IEEE Transactions on Multimedia | `eligible_confirmed_2025_preprint_2026_formal` |
| APVR: Hour-Level Long Video Understanding with Adaptive Pivot Visual Information Retrieval | `2025-06-05` | Proceedings of the AAAI Conference on Artificial Intelligence | `eligible_confirmed_2025_preprint_2026_formal` |
| AV-Master: Dual-Path Comprehensive Perception Makes Better Audio-Visual Question Answering | `2025-10-21` | IEEE Transactions on Circuits and Systems for Video Technology | `eligible_confirmed_2025_preprint_2026_formal` |
| Benchmarking Multimodal Large Language Models for Face Recognition | `2025-10-16` | ICASSP 2026 - 2026 IEEE International Conference on Acoustics, Speech and Signal Processing (ICASSP) | `eligible_confirmed_2025_preprint_2026_formal` |
| ChartAgent: A Multimodal Agent for Visually Grounded Reasoning in Complex Chart Question Answering | `2025-10-06` | Proceedings of the 64th Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers) | `eligible_confirmed_2025_preprint_2026_formal` |
| CogStream: Context-guided Streaming Video Question Answering | `2025-06-12` | Proceedings of the AAAI Conference on Artificial Intelligence | `eligible_confirmed_2025_preprint_2026_formal` |
| Connecting the Dots: Training-Free Visual Grounding via Agentic Reasoning | `2025-11-24` | Proceedings of the AAAI Conference on Artificial Intelligence | `eligible_confirmed_2025_preprint_2026_formal` |
| EgoCross: Benchmarking Multimodal Large Language Models for Cross-Domain Egocentric Video Question Answering | `2025-08-14` | Proceedings of the AAAI Conference on Artificial Intelligence | `eligible_confirmed_2025_preprint_2026_formal` |
| EM-KD: Distilling Efficient Multimodal Large Language Model with Unbalanced Vision Tokens | `2025-11-26` | Proceedings of the AAAI Conference on Artificial Intelligence | `eligible_confirmed_2025_preprint_2026_formal` |
| Embodiment in multimodal large language models | `2025-10-11` | Neuron | `eligible_confirmed_2025_preprint_2026_formal` |
| Evaluating Multimodal Large Language Models on Vertically Written Japanese Text | `2025-11-19` | Proceedings of the Language Resources and Evaluation Conference | `eligible_confirmed_2025_preprint_2026_formal` |
| GCAgent: Long-Video Understanding via Schematic and Narrative Episodic Memory | `2025-11-15` | IEEE Transactions on Multimedia | `eligible_confirmed_2025_preprint_2026_formal` |
| KFS-Bench: Comprehensive Evaluation of Key Frame Sampling in Long Video Understanding | `2025-12-16` | 2026 IEEE/CVF Winter Conference on Applications of Computer Vision (WACV) | `eligible_confirmed_2025_preprint_2026_formal` |
| LeAdQA: LLM-Driven Context-Aware Temporal Grounding for Video Question Answering | `2025-07-20` | Lecture notes in computer science | `eligible_confirmed_2025_preprint_2026_formal` |
| Looking Beyond Visible Cues: Implicit Video Question Answering via Dual-Clue Reasoning | `2025-06-09` | International Journal of Computer Vision | `eligible_confirmed_2025_preprint_2026_formal` |
| LVC: A Lightweight Compression Framework for Enhancing VLMS in Long Video Understanding | `2025-04-09` | ICASSP 2026 - 2026 IEEE International Conference on Acoustics, Speech and Signal Processing (ICASSP) | `eligible_confirmed_2025_preprint_2026_formal` |
| MLlm-DR: Towards Explainable Depression Recognition with MultiModal Large Language Models | `2025-07-08` | ACM Transactions on Multimedia Computing Communications and Applications | `eligible_confirmed_2025_preprint_2026_formal` |
| Mono3DVG-EnSD: Enhanced Spatial-aware and Dimension-decoupled Text Encoding for Monocular 3D Visual Grounding | `2025-11-10` | Proceedings of the AAAI Conference on Artificial Intelligence | `eligible_confirmed_2025_preprint_2026_formal` |
| MuaLLM: A Multimodal Large Language Model Agent for Circuit Design Assistance with Hybrid Contextual Retrieval-Augmented Generation | `2025-08-11` | 2026 31st Asia and South Pacific Design Automation Conference (ASP-DAC) | `eligible_confirmed_2025_preprint_2026_formal` |
| Music Audio-Visual Question Answering Requires Specialized Multimodal Designs | `2025-05-27` | Findings of the Association for Computational Linguistics: ACL 2026 | `eligible_confirmed_2025_preprint_2026_formal` |
| OmniParser V2: Structured-Points-of-Thought for Unified Visual Text Parsing and Its Generality to Multimodal Large Language Models | `2025-02-22` | IEEE Transactions on Pattern Analysis and Machine Intelligence | `eligible_confirmed_2025_preprint_2026_formal` |
| Position: Multimodal Large Language Models Can Significantly Advance Scientific Reasoning | `2025-02-05` | Findings of the Association for Computational Linguistics: ACL 2026 | `eligible_confirmed_2025_preprint_2026_formal` |
| Protecting multimodal large language models against misleading visualizations | `2025-02-27` | Proceedings of the 64th Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers) | `eligible_confirmed_2025_preprint_2026_formal` |
| RSVG-ZeroOV: Exploring a Training-Free Framework for Zero-Shot Open-Vocabulary Visual Grounding in Remote Sensing Images | `2025-09-23` | Proceedings of the AAAI Conference on Artificial Intelligence | `eligible_confirmed_2025_preprint_2026_formal` |
| SightSound-R1: Cross-Modal Reasoning Distillation from Vision to Audio Language Models | `2025-09-19` | ICASSP 2026 - 2026 IEEE International Conference on Acoustics, Speech and Signal Processing (ICASSP) | `eligible_confirmed_2025_preprint_2026_formal` |
| SpaceVLLM: Endowing Multimodal Large Language Model with Spatio-Temporal Video Grounding Capability | `2025-03-18` | Proceedings of the AAAI Conference on Artificial Intelligence | `eligible_confirmed_2025_preprint_2026_formal` |
| SpeakerLM: End-to-End Versatile Speaker Diarization and Recognition with Multimodal Large Language Models | `2025-08-08` | Proceedings of the AAAI Conference on Artificial Intelligence | `eligible_confirmed_2025_preprint_2026_formal` |
| Start Small, Think Big: Curriculum-based Relative Policy Optimization for Visual Grounding | `2025-11-17` | Proceedings of the AAAI Conference on Artificial Intelligence | `eligible_confirmed_2025_preprint_2026_formal` |
| StreamKV: Streaming Video Question-Answering with Segment-based KV Cache Retrieval and Compression | `2025-11-10` | Proceedings of the AAAI Conference on Artificial Intelligence | `eligible_confirmed_2025_preprint_2026_formal` |
| SurgViVQA: temporally grounded video question answering for surgical scene understanding | `2025-11-05` | International Journal of Computer Assisted Radiology and Surgery | `eligible_confirmed_2025_preprint_2026_formal` |
| Towards Effective Long Video Understanding of Multimodal Large Language Models via One-shot Clip Retrieval | `2025-12-09` | SSRN Electronic Journal | `eligible_provisional_formal_venue_unverified` |
| TSPO: Temporal Sampling Policy Optimization for Long-form Video Language Understanding | `2025-08-06` | Proceedings of the AAAI Conference on Artificial Intelligence | `eligible_confirmed_2025_preprint_2026_formal` |
| VideoPro: Adaptive Program Reasoning for Long Video Understanding | `2025-09-22` | Proceedings of the 64th Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers) | `eligible_confirmed_2025_preprint_2026_formal` |
| VideoRAG: Retrieval-Augmented Generation with Extreme Long-Context Videos | `2025-02-03` | Proceedings of the 32nd ACM SIGKDD Conference on Knowledge Discovery and Data Mining V.1 | `eligible_confirmed_2025_preprint_2026_formal` |
| View-on-Graph: Zero-Shot 3D Visual Grounding via Vision-Language Reasoning on Scene Graphs | `2025-12-10` | Proceedings of the AAAI Conference on Artificial Intelligence | `eligible_confirmed_2025_preprint_2026_formal` |
| When Eyes and Ears Disagree: Can MLLMs Discern Audio-Visual Confusion? | `2025-11-13` | Proceedings of the AAAI Conference on Artificial Intelligence | `eligible_confirmed_2025_preprint_2026_formal` |

## 补查新增32项

| 标题 | 最早公开日 | 2026正式载体元数据 |
|---|---|---|
| A Lightweight Large Vision-Language Model for Multimodal Medical Images | `2025-04-08` | Lecture notes on data engineering and communications technologies |
| An anomaly-aware detection head for frugal and robust Infrared Small Target Detection | `2025-10-06` | Engineering Applications of Artificial Intelligence |
| Are large pre-trained vision language models effective construction safety inspectors | `2025-08-14` | Data-Centric Engineering |
| CLAMP: Contrastive learning with adaptive multi-loss and progressive fusion for multimodal aspect-based sentiment analysis | `2025-07-21` | Neural Networks |
| COMODO: Cross-Modal Video-to-IMU Distillation for Efficient Egocentric Human Activity Recognition | `2025-03-10` | Proceedings of the ACM on Interactive Mobile Wearable and Ubiquitous Technologies |
| Cross‐Modal Urban Sensing: Evaluating Sound–Vision Alignment Across Street‐Level and Aerial Imagery | `2025-06-03` | Transactions in GIS |
| DEJIMA: A Novel Large-scale Japanese Dataset for Image Captioning and Visual Question Answering | `2025-11-30` | Proceedings of the Language Resources and Evaluation Conference |
| DiffusionCom: Structure-Aware Multimodal Diffusion Model for Multimodal Knowledge Graph Completion | `2025-04-09` | ICASSP 2026 - 2026 IEEE International Conference on Acoustics, Speech and Signal Processing (ICASSP) |
| Discrete Prompt Tuning via Recursive Utilization of Black-Box Multimodal Large Language Model for Personalized Visual Emotion Recognition | `2025-08-30` | IEEE Access |
| Doc-Researcher: A Unified System for Multimodal Document Parsing and Deep Research | `2025-10-24` | Proceedings of the ACM Web Conference 2026 |
| DSM: Constructing a Diverse Semantic Map for 3D Visual Grounding | `2025-04-11` | IEEE Robotics and Automation Letters |
| EVA02-AT: Egocentric Video-Language Understanding with Spatial-Temporal Rotary Positional Embeddings and Symmetric Optimization | `2025-06-17` | IEEE Transactions on Image Processing |
| Exploring Partial Multi-Label Learning via Integrating Semantic Co-occurrence Knowledge | `2025-07-08` | IEEE Transactions on Multimedia |
| From street views to urban science: Discovering road safety factors with multimodal large language models | `2025-06-02` | Transportation Research Part C Emerging Technologies |
| Improving Generalized Visual Grounding With Instance-Aware Joint Learning | `2025-09-08` | IEEE Trans. Pattern Anal. Mach. Intell. |
| Large multimodal models for low-resource languages: A survey | `2025-02-08` | Information Fusion |
| LMOD \(\boldsymbol{+}\) : A Comprehensive Multimodal Dataset and Benchmark for Developing and Evaluating Multimodal Large Language Models in Ophthalmology | `2025-09-30` | ACM Transactions on Computing for Healthcare |
| LSVG: Language-Guided Scene Graphs with 2D-Assisted Multi-Modal Encoding for 3D Visual Grounding | `2025-05-07` | Pattern Recognit. |
| Marine Saliency Segmenter: Object-Focused Conditional Diffusion With Region-Level Semantic Knowledge Distillation | `2025-04-03` | IEEE Transactions on Image Processing |
| MMTabReal: Real-World Benchmark for Multimodal Table Understanding | `2025-05-27` | Findings of the Association for Computational Linguistics: ACL 2026 |
| Multimodal Large Language Models for Low-Resource Languages: A Case Study for Basque | `2025-11-12` | Proceedings of the Language Resources and Evaluation Conference |
| Point-It-Out: Benchmarking Embodied Reasoning for Vision Language Models in Multi-Stage Visual Grounding | `2025-09-30` | Trans. Mach. Learn. Res. |
| Progressive Multimodal Search and Reasoning for Knowledge-Intensive Visual Question Answering | `2025-08-31` | Proceedings of the 64th Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers) |
| SafePLUG: Empowering Multimodal LLMs with Pixel-Level Insight and Temporal Grounding for Traffic Accident Understanding | `2025-08-09` | CHAIN |
| SimToken: A Simple Baseline for Referring Audio-Visual Segmentation | `2025-09-22` | ICASSP 2026 - 2026 IEEE International Conference on Acoustics, Speech and Signal Processing (ICASSP) |
| Task Graph Maximum Likelihood Estimation for Procedural Activity Understanding in Egocentric Videos | `2025-02-25` | IEEE Transactions on Pattern Analysis and Machine Intelligence |
| Teacher-Guided Pseudo Supervision and Cross-Modal Alignment for Audio-Visual Video Parsing | `2025-09-17` | ICASSP 2026 - 2026 IEEE International Conference on Acoustics, Speech and Signal Processing (ICASSP) |
| UrbanTwin: Synthetic Roadside LiDAR Datasets | `2025-09-08` | IEEE Open Journal of Intelligent Transportation Systems |
| ViQAgent: Zero-Shot Video Question Answering via Agent with Open-Vocabulary Grounding Validation | `2025-05-21` | Proceedings of the 21st International Conference on Computer Vision Theory and Applications |
| Visual Position Prompt for MLLM Based Visual Grounding | `2025-03-19` | IEEE Transactions on Multimedia |
| VTLA: Vision-Tactile-Language-Action model with preference learning for insertion manipulation | `2025-05-14` | Biomimetic Intelligence and Robotics |
| Zero-Shot Audio-Visual Editing via Cross-Modal Delta Denoising | `2025-03-26` | 2026 IEEE/CVF Winter Conference on Applications of Computer Vision (WACV) |

## 完整性与哈希

- `01d_2026_eligible_pool.jsonl`：`eb8c629bfbefcaf1e0d467f3ec0a48605b0c62a04fffc3833ba33959fe11578e`
- 输入文件 SHA256：
  - `00_brief.md`：`48113d5c3e9680ffeadc489c6174828c9c8aa1c5f61f75532883001c9ec3705d`
  - `01c_2026_recall_pool.jsonl`：`ad61a24c05c83794120a6fd4f12f89b104e2757c0396822a4d92ec333642579d`
  - `01c_2026_recall_summary.md`：`40d90e794c0969be6e1a694abe157f66e09d2e6bfa02c625026658e0f865d24e`
  - `build_01c_2026_recall.py`：`1e0957bb0705af5fea5cd1705961b3ca80637e3d74c117280dc2b13428c791d8`

说明：报告文件自身的 SHA256 只能在报告定稿后计算，因此不写入自身内容；外部校验值见执行回执。
