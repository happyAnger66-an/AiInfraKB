# env — 2026-10-16 SoftAdd G-015/G-016

作者：`agent:QA测试/box`  
时区：Asia/Shanghai (UTC+8)

## 测栈锁定

| 项 | 值 |
|---|---|
| Web | `http://10.115.45.181:18088` |
| Service | `:18089` |
| 现网（勿用） | `:8088` |
| 账号 | `qa_e2e`（密码不入库） |
| Agent | `forge-agent-gr00t-test` / `gr00t-test-gpu0` |
| storage | `gpu4090` → `/data` |
| 模板 | `gr00t_n17_softadd_c1` |
| checkpoint | `/data/checkpoints/GR00T-N1.7-3B` |
| datasets | 空（故意） |
| stack | `gr00t-runtime` aarch64 |
| mlc-vla pin（G-015 正式包） | `mlc-vla-2.0.1-feat_gr00t-adastatic-fold-g015-ddea2af79`（sha256 `75c312a7…`） |
| Agent G-016 | commit `22863b1`（`stats_from_gr00t_statistics`）；运行实例 recreate 后生效 |
| C1 | SoftAdd 任务钉 `/work/phase_a_so/libsynapsex_fp8_gemm_c1.so`；`FLASHRT_ARCH=110` |

## Web 镜像缺口（本轮）

测栈 web 一度停在旧镜像 `9b764d5`（无 GR00T 入口）。API 验收不依赖菜单页；UI 冒烟须镜像升到含 GR00T 后再记。
