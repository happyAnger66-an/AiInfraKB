# Model Forge QA

Model Forge 验收分三层。上层是可继承的规则，下层只写本家族或本轮的差异。

作者：`agent:QA测试/box`

知识库首页：[http://www.xiaoanger.com/kb/aiinfra/](http://www.xiaoanger.com/kb/aiinfra/)  
（`qa/` 角色目录目前**只进 GitHub**，站点尚未挂出；禁止 `/wiki/`。）

## 1. 平台套件 `suites/forge-platform.yaml`

所有家族默认继承的平台规则。例如：

- FP8 / NVFP4 模板在创建任务时默认勾选极致量化（calib）；模板带 `requires_calib` / `fp8_gemm` 时不可取消
- 量化流水线默认做 compare（`auto_compare=true`，或 stages 含 compare）。门槛为 overall cos>0.999 且 mse<0.0005。默认 `compare.mode=glue`（ckpt glue / PT 参考），不要求 `p3_dump`
- ISSUE 闭环：修好 → QA **新开一单**（勿刷失败 job）
- API 绿 ≠ UI 绿

## 2. 家族 overlay `suites/family-*.yaml`

按模型家族覆盖，当前为 `family-gr00t.yaml`（后续可加 pi05 等）。`meta.extends: forge-platform`。与平台同 id 的用例写 `inherits:`，不重复展开断言。

GR00T SoftAdd API 菜谱：`skills/gr00t-softadd-api.md`。

## 3. 轮次快照 `runs/`

每一轮单独一个目录，命名 `runs/YYYY-MM-DD-slug/`：锁住当时的端口、提交、结果和问题单。快照不盲目继承到下一轮，也不回写成平台规则。

本轮 SoftAdd G-015/G-016：`runs/2026-10-16-g015-g016-softadd/`。

操作步骤见 `skills/model-forge-acceptance.md`。
