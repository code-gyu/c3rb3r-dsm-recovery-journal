# 工具验证记录

2026-10-31，本地 macOS、Python 3.14.0 执行 `python3 -m unittest discover -s tests -v`：**7 项通过，0 失败**。

覆盖相同尺寸的内容损坏、额外与缺失路径、空目录、链接目标、符号链接不跟随、FIFO 不完整状态、危险及重复清单、EOF marker/长度/未知模式、大小写与 Unicode 及父路径冲突，以及报告独占新建和扫描树外输出。

目录 SHA 检查使用合成临时数据，不读取真实候选、内存、密文或媒体。首次运行的一项断言预期 `ValueError`，而 macOS 的 `O_NOFOLLOW` 实际返回 `OSError`；测试修正为接受两种拒绝路径后全部通过。没有为使测试通过而允许跟随链接。

`scripts/check_repository.py` 核对公共文件的本地 Markdown 链接、禁止产物和常见凭据模式，检查通过。另人工核对照片字节差额、分类计数、homes 累计和原始地址替换。自动模式扫描不能证明没有秘密或代码漏洞。

CI 已配置 Windows/macOS/Ubuntu Python 3.9/3.12；尚未在远端运行，不将配置视为通过。没有验证真实 DSM、Btrfs 实盘、现场采集、真正解密或应用恢复；本工具也不提供这些功能。历史现场恢复器的测试数与本仓库测试分开，不相加。

[工具能力及限制](../tools/README.md) · [恢复结果的验证边界](07-results-and-limits.md)

## 跨平台修订复测

同日 macOS、Python 3.14.0 复测 **9 项通过，0 失败**。新增测试模拟缺少 POSIX 打开常量时仍按原字节读取 CR/LF、0x1A、NUL 等内容，以及拒绝 Windows reparse 属性后不打开目标。符号链接测试在不具备创建权限的 Windows 环境中可跳过，FIFO 测试在无 mkfifo 的平台跳过；报告权限 0600 仅在 POSIX 断言。模拟不等于 Windows 实机验证。

Windows 的二进制 IO、reparse 防护与 ACL 边界已说明；尚无 Windows/Linux 远端执行结果，CI 配置不作为通过证据。
