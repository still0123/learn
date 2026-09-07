# 材料清单

## 核心稿件

- `deliverables/patent/视频问答答案可靠性保障专利申请候选稿_V3_20260823.md`
  - 权1第30行：A2 不以 A0 为待改写文本。
  - 权1第32至34行：A2 再评分，并以绝对阈值与相对裕量决定替换/回退。
  - 权7第56至62行：用相对参考答案正确性生成标签，训练证据支持度验证器。
  - 第254至264行：把 Full-7844 的 40.31/59.87% 表述成完整闭环结果。

## 代码证据

- `.remote_threshold_work/infer_qwen3_adaptive_crop_threshold_full_v1.py:179-208,486-498`
  - A2 提示显式包含 `Initial answer: {a0_prediction}`，要求验证/必要时修改初答。
- `.remote_overnight_work/materialize_adsqa_supplement2526_candidates_v1.py:136-154`
  - 触发后直接采用 A2；没有读取 A2 支持度、替换阈值或相对裕量。
- `evaluation/tools/score_answer_claims_qwen3_v1.py:85-92`
  - 接口称输入为 atomic claim；但 Full 流程的上游把完整答案直接写入 `claim` 字段。
- `.remote_overnight_work/build_evads_a0_verifier_pool_v2.py:145-163`
  - `claim` 字段实际为完整候选答案，未见自动原子声明拆分。

## 实验记录

- `docs/AdsQA实验结果总表与复现索引.md:4096-4120`
  - Confirm-1000 执行阈值+margin 门控，结果 30.90/48.05%；相对 MMR 为 -1.30/+0.35 pp，未稳定胜出。
- `docs/AdsQA实验结果总表与复现索引.md:4384-4407`
  - Full-7844 结果为 40.31/59.87%，但记录只支持 A0 低支持触发补证后使用 A2。

## 外部专利与法律资料

- CN121388101A：《基于迭代式多模态的视频问答系统及方法》。
- CN120472379B：《视频问答方法、设备及介质》。
- CN121235759B：《一种对APP广告内容合规性的检测方法及系统》。
- CN117744802A：《一种解决法律大语言模型的幻觉问题的方法及系统》。
- CN121962369A、CN122615110A：本轮未取得可核验的具体著录/全文记录。
- 《中华人民共和国专利法（2020年修正）》第二十二、二十六、二十九、三十三条。

