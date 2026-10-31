# 合成示例

`synthetic-manifest.json` 不包含真实案例数据。它演示明密文同名与大小写冲突；`plan` 应保存冲突报告并退出 1。

```sh
python3 tools/rescue_audit.py --output /SAFE/receipts/synthetic-plan.json plan examples/synthetic-manifest.json
```
