# 离线审计工具 / Offline audit helper

Python **3.9+**，只用标准库，已适配 Windows、macOS 和 Linux 的稳定、受控离线副本（本地实测仅 macOS）。无网络、无密钥处理、无解密、无块设备读取、无来源写入。只显式新建一个 JSON 报告，POSIX 系统权限为 `0600`，Windows 继承目标目录 ACL，需事先限制目录访问；已有报告拒绝覆盖。报告中的路径与链接目标可能敏感，应私有保存。

Windows PowerShell 示例与平台限制见[跨平台指南](../docs/11-cross-platform.md)。以下 shell 示例使用 macOS/Linux 的命令形式。

## 命令

在仓库根目录执行，将 `/SAFE` 替换成真实独立介质。输出父目录须预先建立，输出文件须不存在；`--output` 写在子命令之前。

```sh
python3 tools/rescue_audit.py --output /SAFE/receipts/source.json inventory /SAFE/source-copy
python3 tools/rescue_audit.py --output /SAFE/receipts/copy.json inventory /SAFE/second-copy
python3 tools/rescue_audit.py --output /SAFE/receipts/compare.json compare /SAFE/receipts/source.json /SAFE/receipts/copy.json
python3 tools/rescue_audit.py --output /SAFE/receipts/footer.json footer /SAFE/source-copy/example.L0CK3D --marker e921db3b
python3 tools/rescue_audit.py --output /SAFE/receipts/plan.json plan /SAFE/receipts/source.json
```

| 子命令 | 输出与保证 | 限制 |
|---|---|---|
| inventory | 相对路径、类型、尺寸、SHA、链接目标；空目录也列出；文件读取前后身份核对 | 不跟符号链接，拒绝 Windows junction/其他 reparse point，不跨不同 st_dev；特殊文件或读取失败令 complete=false |
| compare | 精确路径集合、类型、文件大小/SHA、链接目标；列出额外/缺失/改变 | 不做模糊名称匹配，不比较时间、权限、ACL/xattr 和硬链接拓扑 |
| footer | 588 字节 EOF 的 marker、长度、文件模式、crypto mode 和 reserved 检查 | 不输出受保护密钥记录；不检查候选，不认证正文 |
| plan | 为每个普通文件建立 SHA(原相对路径) 的平铺对象名，保留 intended_path | 仅规划不复制、不解密、不改名；冲突仍需审查 |

`plan` 将 `.L0CK3D` 视为待去除后缀，检查明密文同名、大小写、NFD Unicode 等价及文件作为父路径的冲突。所有普通文件都分配对象路径，因此大小写双方和现有未加密版本不会被工具自动选边。原目录拓扑、链接、权限和空目录重建是后续独立工作。它不生成可直接导入应用的恢复树。

## 退出码

- `0`：该命令的有限检查通过。
- `1`：报告已写入，但清单不完整、比较不一致、footer 布局不匹配或路径存在冲突。
- `2`：输入、参数或 IO 错误；不能当成有效检查完成。输出失败时可能留有不完整 JSON，应保留分析并改用新文件名重试。

不要仅凭退出 0 就声明历史原件一致。清单会一次装入内存，适合小范围离线批次，不适用于本案数千万条全盘元数据。它不识别同 st_dev 的 Btrfs 子卷、bind mount 或实时恶意路径替换，不能替代现场采集器或受攻击系统上的安全边界。读取也可能更新底层 atime；需字节/元数据取证时使用正确只读挂载的证据副本。

JSON 使用 ASCII 转义保存特殊文件名，比较仍按精确路径；保守拒绝 `..`、空组件、反斜杠等路径。manifest 和报告需要受控保存；这不是签名、认证或防篡改数据库。

## 与实际恢复器的关系

| 本案实际组件 | 功能 | 为什么未直接打包 |
|---|---|---|
| process-stream-23393-v2 | 进程映射流式采集、缺页回执 | 本案 PID/布局和通道适配，需重新审阅与参数化 |
| offline-key-23393-v2 | 在已保存映射中提取候选 | 特定样本布局；含敏感材料处理路径 |
| offline-decrypt-23393 | 严格单文件副本解密 | 上游代码许可及会话 profile 需分别核对 |
| photo-audit-20261030 | 清点、照片恢复、配对和 NAS 归档控制 | 固定路径、来源白名单、环境和容量假设较多 |

如需真正取钥、解密或 Btrfs 恢复，先阅读[参考路线](../docs/08-btrfs-and-references.md)，从其固定版本核对适配条件，单文件验证后再扩大。安装上游工具不代表本仓库验证其安全或兼容性。

## 自检

```sh
python3 -m unittest discover -s tests -v
```

测试使用临时合成文件，覆盖同尺寸内容损坏、漏项与额外项、符号链接不跟随、FIFO 标为不完整、危险/重复清单、EOF 变体与未知模式、路径冲突，以及报告不覆盖。测试不连接 NAS，不使用真实密文、密钥或私人数据。

本次执行环境与实际结果见[工具验证记录](../docs/tool-validation.md)，CI 配置不等于已通过远端运行。

## Windows 文件系统注意事项

二进制读取显式使用 Windows `O_BINARY`，避免文本换行转换影响哈希与 footer。Windows 没有 `O_NOFOLLOW` 时，工具在打开前检查 `lstat` 并拒绝符号链接/reparse point，再检查打开后的文件身份；这不等同于 POSIX 的原子 no-follow 保证，仅应用于稳定、可信离线树，不能抵御并发恶意路径替换。

工具发现 junction 或其他非符号链接 reparse point 时标记该清单不完整，不进入目标。云盘占位文件也可能是 reparse point，应先在独立位置取得完整稳定副本，不通过删去检查强行扫描。根目录也不能是链接或 reparse point。

Windows 默认大小写不敏感，NTFS 路径限制与非法字符也可能妨碍 NAS 路径直接落盘。工具规划的十六进制对象名用于避免直接沿用原始文件名，并保留 intended_path 供后续还原；它不把含冒号、保留设备名等原路径变成可直接重建的 Windows 树，也无法找回复制阶段已被覆盖的内容。
