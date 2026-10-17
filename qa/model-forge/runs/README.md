# 轮次快照

每一轮验收一个目录，命名 `runs/YYYY-MM-DD-slug/`。快照记录当时的环境与结果，不作为下一轮的继承源。

作者：`agent:QA测试/box`

## 怎么开一轮

从空目录开始，放进这些文件：

| 文件 | 内容 |
|---|---|
| `env.md` | 锁定的 web / service 端口、agent、模板 id、ckpt 路径、相关 git 提交 |
| `results.md` | 用例 id、PASS/FAIL、关键数字（cos、mse、是否产出 pack） |
| `ISSUES.md` | 问题表：id、现象、是否阻断、责任方、状态 |

套件断言仍以 `suites/` 为准。本目录只锁「这一轮实际看到的环境」和「这一轮的结果」。

不要写入密钥、token、口令或生产凭据。测栈 IP/路径可作为约定写入。

## 已有轮次

| 目录 | 摘要 |
|---|---|
| `2026-10-16-g015-g016-softadd/` | SoftAdd G-015/G-016 PASS；G-017 方法关；G-018 pack 可见性 open；UI 仍开 |
