# kb-0031 evidence summary

Source: model_forge_agent tip GPU claim 验收草稿（2026-10-15），晓安哥点名「问题+方案」备审；知识库润色落 inbox。

| item | note |
|---|---|
| tip | forge-agent ~`87d94b7` |
| job 116 | PASS |
| job 117–119 | FAIL then fixed per five issues |
| PRO5000 | GPU-busy stall → restart; check log timestamps on false-busy |
| Thor lerobot | `/work/vendor/lerobot` (deps aarch64) + overlay |
| schedulable | drain old thor-2240 (thor-003); keep tip thor-2231-gpu0 |
| LIBERO q01 | tip skips missing percentiles; use ckpt norm_stats |
| mlc-vla | Thor 1.1.0 missing nvfp4_awq_calib vs PRO5000 1.1.1; hotfix then pin (no aarch64 1.1.1 full pack yet) |

对外入口只 `/kb/aiinfra/`（晋升后由 Blog 部署）；本文件仅 inbox evidence。
