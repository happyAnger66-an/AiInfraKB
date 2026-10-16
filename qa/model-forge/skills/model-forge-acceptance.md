# Model Forge 验收手册

作者：`agent:QA测试/box`

本文件是 QA 操作说明，不是 Cursor skill。每一轮按下面顺序做。

## 执行前

1. 打开本家族套件（例如 `suites/family-gr00t.yaml`）和它 `extends` 的平台套件 `suites/forge-platform.yaml`。
2. 把本轮要跑的用例清单发给晓安哥，确认范围后再执行。未确认的用例不跑。
3. 只使用测试账号 `qa_e2e` 登录测试栈。不要用生产 `:8088`。

## 继承

- 新家族从 `forge-platform.yaml` 继承平台用例（FP8 极致量化默认、量化流水线默认 compare 等），在 `family-*.yaml` 里用 `inherits:` 指向，不复制断言正文。
- 家族文件只写该家族的环境、路径和差异用例。
- `runs/` 里的某一轮结果不自动变成下一轮或下一个家族的规则。

## 每一轮

1. 在 `runs/` 下新建 `YYYY-MM-DD-slug/`（见 `runs/README.md`）。
2. 抄进本轮锁定的端口、提交、套件版本和结果。
3. 跑完后写最终报告。报告里用一张问题表，至少包含：用例 id、现象、是否阻断、责任方、状态。
4. 问题留在该轮目录的 `ISSUES.md`，不把密钥、token 或生产地址写进仓库。
