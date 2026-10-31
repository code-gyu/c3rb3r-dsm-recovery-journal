# 11 · Windows / macOS / Linux 跨平台使用指南

[返回首页](../README.md) · [工具说明](../tools/README.md)

恢复对象是 DSM 上的数据，救援工作站不必是 Mac。隔离、保存证据、离线分析、用本机会话材料恢复副本，以及逐项验收的原则适用于 Windows、macOS 和 Linux。不同平台的网络工具、文件系统语义、权限和媒体 API 不能直接互换。

## 平台能力与实际验证

| 工作 | Windows | macOS | Linux |
|---|---|---|---|
| NAS 端 `/proc`、进程状态与提权命令 | 通过可信 SSH 在 NAS 执行 | 相同 | 相同 |
| 本仓库 Python 清单/比较/footer/路径规划 | 已适配原生 Python；待 Windows 实测 | 本地合成测试通过 | CI 已配置；待远端结果 |
| 上游内存采集、提钥与解密器 | 逐项核对版本、依赖与二进制传输 | 本案实际使用的工作站 | 逐项核对版本、依赖与权限 |
| 网络与 SSH | PowerShell / Windows OpenSSH | BSD 系工具 / OpenSSH | iproute2 / OpenSSH |
| Btrfs 设备与 ioctl 访问 | 在 NAS 或具备设备访问的 Linux 环境完成 | 同左 | 需支持实际存储布局的环境 |
| 媒体标识与内容解码 | 可用对应工具检查，记录覆盖范围 | 本案使用 Apple API 验证 | 可用对应工具检查，记录覆盖范围 |
| `PHLivePhoto` / ImageIO / AVAssetReader | 不具备相同 Apple 原生 API | 本案实际使用 | 不具备相同 Apple 原生 API |

“已适配”是代码和接口层面的状态，不代表已在 Windows 实机运行。仓库不附带通用解密器或采集器，不能把审计工具的跨平台适配外推到全部上游恢复代码。

## Windows 快速开始

在干净分析电脑准备 Python 3.9+、仓库和足够的独立存储。准备工具不要以重启或升级受灾 NAS 为前提。以下在仓库根目录的 PowerShell 执行；若系统没有 `py` launcher，使用实际 Python 3 的 `python` 命令。

```powershell
py -3 --version
py -3 tools/rescue_audit.py --help
py -3 -m unittest discover -s tests -v
py -3 scripts/check_repository.py
```

假设稳定的密文副本在 `E:\Rescue\source-copy`，第二份副本在 `F:\Rescue\second-copy`。先创建 `E:\Rescue\receipts` 并使用 NTFS ACL 限制访问，报告文件名必须不存在：

```powershell
py -3 tools/rescue_audit.py --output 'E:\Rescue\receipts\source.json' inventory 'E:\Rescue\source-copy'
py -3 tools/rescue_audit.py --output 'E:\Rescue\receipts\second.json' inventory 'F:\Rescue\second-copy'
py -3 tools/rescue_audit.py --output 'E:\Rescue\receipts\compare.json' compare 'E:\Rescue\receipts\source.json' 'E:\Rescue\receipts\second.json'
py -3 tools/rescue_audit.py --output 'E:\Rescue\receipts\footer.json' footer 'E:\Rescue\source-copy\sample.jpg.L0CK3D' --marker e921db3b
py -3 tools/rescue_audit.py --output 'E:\Rescue\receipts\plan.json' plan 'E:\Rescue\receipts\source.json'
$LASTEXITCODE
```

`e921db3b` 是本案示例，其他案件应根据自己的尾记录核实。退出 1 表示有限检查发现差异、冲突或不匹配，仍须查看报告；退出 2 是错误。报告中的文件名、链接目标可能敏感，不能直接提交到 GitHub。

## 网络检查按平台替换

以下均是只读检查示例。`169.254.100.2` 是占位 NAS 地址，先确认接口、路由和目标身份，不把它当作固定地址。

| 要检查的内容 | Windows PowerShell | macOS | Linux |
|---|---|---|---|
| 接口与地址 | `Get-NetAdapter`、`Get-NetIPConfiguration` | `networksetup -listallhardwareports`、`ifconfig` | `ip address` |
| 路由 | `Get-NetRoute`、`route print` | `route -n get 169.254.100.2` | `ip route get 169.254.100.2` |
| 邻居表 | `Get-NetNeighbor` | `arp -n 169.254.100.2` | `ip neigh` |
| TCP 22 | `Test-NetConnection 169.254.100.2 -Port 22 -InformationLevel Detailed` | 本案使用 `nc -vz -G 3`，参数是 BSD 版本 | `nc -vz -w 3`，先核对本机版本 |
| IP 转发 | `Get-NetIPInterface` 查看 `Forwarding` | `sysctl net.inet.ip.forwarding net.inet6.ip6.forwarding` | `sysctl net.ipv4.ip_forward net.ipv6.conf.all.forwarding` |

Windows 还应在网络适配器设置中检查互联网连接共享（ICS）、移动热点和 Network Bridge。转发值、服务是否运行或一条路由都不能单独证明隔离；还要检查所有接口、IPv6、共享和实际网络路径。本案删除某一静态路由的修复不能直接变成其他电脑上的通用删路由命令。

已安装 OpenSSH 客户端时，Windows 可通过 `ssh NAS_ACCOUNT@169.254.100.2` 连接；先核实主机指纹。是否能使用 `-B` 等接口选项取决于客户端实现，不照抄 Mac 的 `en7`。本地电脑的终端与远端 NAS shell 要清楚区分：`/proc`、`sudo` 和 DSM 路径是在 NAS 执行的，不是在 Windows 本机执行。

## Windows 二进制传输不能经过文本转换

进程内存、归档、密文和密钥文件必须保持每个字节。不要未经验证就用 PowerShell 的文本管道、`Get-Content`、`Out-File` 或不同版本的 `>` 重定向接收原始二进制流。微软文档说明，PowerShell 7.4 起对原生命令 stdout 的重定向保留字节流；旧版本及经过文本 cmdlet 的路径不能据此假定安全。不把屏幕无报错当作字节正确。参见 [PowerShell 重定向文档](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_redirection?view=powershell-7.5)。

优先使用已经审阅的文件传输工具，或用 Python `subprocess` 的字节流接收、单独处理 stderr 与退出码。无论哪种方式，都要检查发送端字节数与 SHA、接收端落盘后完整 SHA，保留失败产物。本仓库不提供进程内存接收器；不要自行把文本示例改成取证采集命令。

NAS 缺少 SFTP 时，支持该选项的 OpenSSH `scp -O` 可选择旧 SCP 协议，但路径引用、版本和来源需要核对。`scp -O` 不是校验或断点续传保证；完成后仍需逐路径清单和 SHA。`.command` 是本案 Mac 启动脚本，Windows 应阅读其实际逻辑并使用对应实现，不能只改扩展名为 `.bat`。

## 路径、链接与权限

Windows 常见大小写不敏感文件系统和 macOS 常见默认卷都会面临 NAS 大小写冲突。Windows 还有保留文件名、非法字符、长路径等约束；复制前应先规划，不要等覆盖后再从数量推测完整性。若需要保存任意 NAS 文件名，评估保留成员名的归档或适当的镜像格式，并将内容保存在独立介质。

`plan` 生成哈希对象名并保留原路径映射，只规划不落盘恢复。`inventory` 无法找回接收盘上已被合并或覆盖的原件。它记录符号链接但不跟随，遇到 Windows junction/其他 reparse point 则标为不完整；不要为了通过检查去掉这些限制。

Windows 的 `0600` 参数不能代替 NTFS ACL；应使用私人目录并核对实际访问控制。exFAT 等介质不提供同等 ACL 语义。WSL、Git Bash 和 Windows 本机的路径、权限与工具并非完全相同，WSL 挂载盘也不自动变成独立备份或大小写安全的 NAS 镜像。

## 照片与实况验收

HEIC/JPEG 与 MOV 的内容标识、`still-image-time`、配对哈希和已知原件比对不要求使用 Mac。Windows/Linux 可以使用适合该格式的元数据读取和完整解码工具，但需要明确记录验证的图像、轨道和辅助数据范围。

Apple `PHLivePhoto` 资源构建、ImageIO 默认 RAW 图像及 AVAssetReader 结果是本案的 Mac 实测证据。Windows 上配对标识一致或媒体可播放，不等于 Apple Photos 成功导入；同样 Mac 构建资源通过也不保证 Windows 播放器完整兼容。所有平台都应把输出 SHA、历史原件 SHA、解码、配对与应用验收分别报告。

## 接口参考

网络检测参数参考微软 [Test-NetConnection](https://learn.microsoft.com/en-us/powershell/module/nettcpip/test-netconnection?view=windowsserver2025-ps)；平台常量与文件打开行为参考 [Python os 文档](https://docs.python.org/3/library/os.html)。它们用于核对接口，不代替真实 Windows 救援验收。
