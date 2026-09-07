# 05｜实现对应图

| 专利组件 | 最小实现对象 | 当前状态 |
|---|---|---|
| EvidenceUnit与E0/ΔE/E+ | 不可变证据索引和快照摘要 | 说明书已定义，待实现 |
| 第一读取域 | permit_service账户、ACL、输入模式 | 说明书已定义，待实现 |
| 许可冻结 | permit_store、permit_digest、t_p | 说明书已定义，待实现 |
| 第二读取域 | candidate_service账户、字段白名单 | 说明书已定义，待实现 |
| 候选冻结 | A2_digest、A2_version、t_s/t_a | 说明书已定义，待实现 |
| 联合读取 | control_service授权和t_j | 说明书已定义，待实现 |
| 同E+核验 | F0+/F2+记录及统一配置ID | 旧实验不等于该实现 |
| 唯一配准 | migration_permit_match表 | 待实现 |
| 双域闭包 | write_set、proof_reference_set | 待实现 |
| 原子写入 | staged closure和事务日志 | 待实现 |
| 无新增终检 | render—extract—compare循环 | 待实现 |

本轮没有把“存在说明书伪代码”误记为“已有可运行代码”。
