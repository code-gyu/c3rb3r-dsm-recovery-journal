# 00 · 按证据推进的操作路线

[返回首页](../README.md)

Windows、macOS、Linux 均可作为救援工作站，先读[跨平台指南](11-cross-platform.md)核对命令及环境边界。

这是处置路线与停止条件，不是会自动操作现场的一键恢复脚本。本案 PID、接口名、内核、地址、标记和布局均不能直接套用。

## 先确认五件事

1. 物理机还是虚拟机，实际系统与内核版本是什么；是否重启过。
2. 当前是否仍在加密，可疑进程身份、启动时间和线程状态是否可信。
3. 怎样隔离 IPv4/IPv6 外网、同步与其他设备，同时保留可信受限管理通道。
4. 独立证据介质在哪里，挂载、可用空间和读回校验是否已确认。
5. 有没有感染前同版本原件或摘要，可以验证恢复字节。

## 分阶段门槛

| 阶段 | 需要的证据 | 不满足时 |
|---|---|---|
| 阻止损失 | 进程身份已核实，暂停后所有线程状态已核查 | 不按名称批量发信号；优先现场支持 |
| 易失保全 | 映射、读取错误/缺页、工具版本、来源和落盘摘要 | 保留失败流与缺口；不伪造页面 |
| 文件副本 | 来源与副本逐路径 SHA 一致、范围完整 | 补采明确缺失，不覆盖旧材料 |
| 适配验证 | 样本、EOF、模式、标记、长度与候选记录一致 | 拒绝未知格式，分层定位失败 |
| 单文件恢复 | 独立输入、全新输出、已知原件或格式检查 | 不能只看扩展名与图片预览 |
| 扩大范围 | 容量、冲突映射、元数据/链接台账、批次回执 | 不把小目录工具删上限后直接放大 |
| 验收与重建 | 全输出重读、范围核对、格式/应用验收、独立备份 | 不宣称全盘恢复或系统已干净 |

新事件优先把输出写入独立设备。若还可能依赖 Btrfs 旧 extent，减少受灾卷写入尤其重要。本文记录的同池新树只是历史操作，不证明不会覆盖潜在旧块。

## 本地副本的可执行检查

只在已经保存、稳定且受控的离线小范围副本上运行。本工具不采集现场；清单可能含私人文件名和链接目标，结果不要直接上传。

```sh
# 输出父目录先建立；报告必须位于扫描树之外，文件名必须不存在。
python3 tools/rescue_audit.py --output /SAFE/receipts/source.json inventory /SAFE/source-copy
python3 tools/rescue_audit.py --output /SAFE/receipts/destination.json inventory /SAFE/second-copy
python3 tools/rescue_audit.py --output /SAFE/receipts/comparison.json compare /SAFE/receipts/source.json /SAFE/receipts/destination.json
python3 tools/rescue_audit.py --output /SAFE/receipts/footer.json footer /SAFE/source-copy/sample.jpg.L0CK3D --marker e921db3b
python3 tools/rescue_audit.py --output /SAFE/receipts/path-plan.json plan /SAFE/receipts/source.json
```

`e921db3b` 只是本案标记示例。布局检查不验证候选密钥、不解密，也不认证正文。路径规划返回冲突时退出 1，仍保存报告，供人工审查。

## 停止当前批次的条件

进程身份或启动时间变化、线程恢复、SSH 指纹异常、来源成员或内容改变、归档校验失败、未知 footer/模式、候选匹配失败、输出冲突、无回执输出或空间不足，应停止依赖该条件的批次。保留失败产物与日志；不要清空输出再重跑，不要因此终止仍需保全的进程。

## 备份和业务恢复

保留原密文、内存原件、分析副本和恢复结果的独立位置及摘要。NAS 内归档与 Mac 同机双目录均不能代替独立设备备份。业务数据库、Docker 持久卷和虚拟磁盘在隔离的新环境单独验收；不要执行恢复程序或启动旧容器来碰运气。

更多判断依据见[内存保全](03-memory-preservation.md)、[验证等级](07-results-and-limits.md)和[可信重建](09-security-and-rebuild.md)。
