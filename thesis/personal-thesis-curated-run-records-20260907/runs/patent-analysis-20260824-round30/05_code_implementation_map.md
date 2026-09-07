# 说明书可实施性映射

| 权项机制 | V4.6 中的实现支持 | 状态 |
|---|---|---|
| E0/ΔE/E+ | EvidenceUnit、used_in_E0、FreezeSnapshot | 已写 |
| 许可服务无答案读权 | ReadDomain、A0/A2 store ACL、字段禁止 | 已上提权1并有伪代码 |
| 候选服务双盲 | Q+RawEvidence(E+) 白名单、A0/permit store 禁读 | 已写 |
| t_a 前无反向写入 | 输入接口/共享缓存/消息队列禁写，伪代码断言 | 本轮补强 |
| 四时点 | t_p、t_s、t_a、t_j 及摘要日志 | 已写 |
| 同 E+ 复评 | NormalizeAndVerify(A0/A2, Eplus, same_config) | 已写 |
| 唯一配准 | UniqueMatch 的七类键 | 已写 |
| 有向闭包 | outgoing write set / incoming proof set | 已写 |
| 原子提交/禁写 | Stage、AllGateConditionsSatisfied、AtomicCommit/RejectAll | 已写 |
| 非价格场景 | ASR 时间事件 + 前置条件闭包 | 本轮新增 |

建议原型日志不是递交法定附件，但最好在答审前冻结一份：两个服务输入摘要、四时点、permit/A2 摘要、配准结果和失败原因。
